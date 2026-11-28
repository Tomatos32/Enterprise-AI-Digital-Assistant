"""Hybrid Semantic Slot Extraction Engine & Shared Numeric/Amount Parser.

Provides:
  1. Shared Chinese/Arabic numeral, quantity, unit-price, and total-price parser
     (reused by router_node.py and slot extraction to keep parsing consistent).
  2. Deterministic + lightweight non-thinking LLM hybrid slot extraction for all
     6 enterprise tools (query_employee, query_inventory, create_ticket,
     create_purchase, send_email, search_knowledge_base) and the approval node.
  3. Policy Strategy 5.1 Option A: automatic HR directory lookup for send_email
     when an internal employee name is mentioned without an explicit email address
     (auto-fills on unique match; politely clarifies on missing or ambiguous match).
  4. Policy Strategy 5.2 Option A: strict prohibition on auto-filling ERP catalog
     reference prices for create_purchase/approval when user omits price/budget.
  5. Multi-turn pending-clarification detection & cross-turn slot merging compatible
     with both in-memory metadata and WebSocket-reconstructed pure message history.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from backend.adapters.factory import get_hr_adapter
from backend.core.config import settings
from backend.core.llm import get_slot_extractor_llm
from backend.core.metrics import record_slot_extraction_event

logger = logging.getLogger(__name__)

APPROVAL_THRESHOLD_RMB = 5000.0

# ---------------------------------------------------------------------------
# 1. Shared Chinese & Arabic Numeral / Purchase Quantity & Amount Parser
# ---------------------------------------------------------------------------

_CN_DIGIT_MAP: Dict[str, int] = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_CN_SMALL_UNIT_MAP: Dict[str, int] = {"十": 10, "百": 100, "千": 1000}


def _cn_section_to_int(section: str) -> Optional[int]:
    """Converts a Chinese numeral section under 10,000 (e.g. 三千五, 两千八百, 十五, 两)."""
    if not section:
        return 0
    result = 0
    current_digit = 0
    last_unit = 10000
    for idx, ch in enumerate(section):
        if ch in _CN_DIGIT_MAP:
            current_digit = _CN_DIGIT_MAP[ch]
        elif ch in _CN_SMALL_UNIT_MAP:
            unit = _CN_SMALL_UNIT_MAP[ch]
            if current_digit == 0 and ch == "十" and idx == 0:
                current_digit = 1
            result += current_digit * unit
            current_digit = 0
            last_unit = unit
        else:
            return None
    if current_digit > 0:
        if last_unit in (1000, 100) and len(section) >= 2 and section[-2] in ("千", "百"):
            result += current_digit * (last_unit // 10)
        else:
            result += current_digit
    return result


def parse_chinese_number(token: str) -> Optional[float]:
    """Converts a Chinese or Arabic numeric string (with optional 万/千/k/w) into a float."""
    cleaned = token.replace(",", "").replace("，", "").strip().lower()
    if not cleaned:
        return None

    arabic_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(万|w|千|k)?", cleaned)
    if arabic_match:
        val = float(arabic_match.group(1))
        unit = arabic_match.group(2)
        if unit in ("万", "w"):
            val *= 10000.0
        elif unit in ("千", "k"):
            val *= 1000.0
        return val

    if not re.fullmatch(r"[零〇一二两三四五六七八九十百千万]+", cleaned):
        return None

    total = 0.0
    if "万" in cleaned:
        left, right = cleaned.split("万", 1)
        left_val = _cn_section_to_int(left) if left else 1
        if left_val is None:
            return None
        total += left_val * 10000.0
        if right:
            if len(right) == 1 and right in _CN_DIGIT_MAP:
                total += _CN_DIGIT_MAP[right] * 1000.0
            else:
                right_val = _cn_section_to_int(right)
                if right_val is None:
                    return None
                total += right_val
        return total

    sec = _cn_section_to_int(cleaned)
    return float(sec) if sec is not None else None


_NUM_TOKEN_PATTERN = r"(?:\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:万|w|千|k))?|[零〇一二两三四五六七八九十百千万]+)"
_UNIT_PRICE_RE = re.compile(
    rf"(?:单价|每台|每个|每件|每套|每把|每张|每部|每只|每箱)\s*(?:为|是|约|大概)?\s*[￥¥]?\s*({_NUM_TOKEN_PATTERN})\s*(?:元|块钱|块|rmb|人民币)?",
    re.IGNORECASE,
)
_TOTAL_PRICE_RE = re.compile(
    rf"(?:总价|总额|总计|合计|总预算|预算|总共|一共)\s*(?:为|是|约|大概)?\s*[￥¥]?\s*({_NUM_TOKEN_PATTERN})\s*(?:元|块钱|块|rmb|人民币)?",
    re.IGNORECASE,
)
_CURRENCY_AMOUNT_RE = re.compile(
    rf"(?:[￥¥]\s*({_NUM_TOKEN_PATTERN})|({_NUM_TOKEN_PATTERN})\s*(?:元|块钱|块|rmb|人民币))",
    re.IGNORECASE,
)
_QUANTITY_RE = re.compile(
    r"(\d+|[一二两三四五六七八九十]+)\s*(?:台|个|件|套|把|张|部|批|只|箱)",
)
_MAGNITUDE_RE = re.compile(
    r"(\d+(?:\.\d+)?|[一二两三四五六七八九十]+)\s*(万|w|千|k)",
    re.IGNORECASE,
)
_BARE_PRICE_RE = re.compile(r"(?:^|[\s,，:：是])([1-9]\d{1,6}(?:\.\d{1,2})?)(?:$|[\s,，。])")


def extract_purchase_quantity_and_prices(
    text: str,
    *,
    allow_bare_price: bool = False,
) -> Dict[str, Any]:
    """Extracts structured quantity, unit_price, total_price, and price_kind from text.

    Returns dict with keys:
      - quantity: Optional[int] (explicitly mentioned quantity, else None)
      - unit_price: Optional[float]
      - total_price: Optional[float]
      - price_kind: Optional[str] ('total' | 'unit' | 'currency' | 'magnitude' | 'bare')
    """
    result: Dict[str, Any] = {
        "quantity": None,
        "unit_price": None,
        "total_price": None,
        "price_kind": None,
    }
    if not text:
        return result

    # Extract explicit quantity if present
    qty_match = _QUANTITY_RE.search(text)
    explicit_qty: Optional[int] = None
    if qty_match:
        parsed_qty = parse_chinese_number(qty_match.group(1))
        if parsed_qty is not None and 1.0 <= parsed_qty <= 10000.0:
            explicit_qty = int(round(parsed_qty))
            result["quantity"] = explicit_qty

    effective_qty = float(explicit_qty) if explicit_qty else 1.0

    # 1. Explicit total price / budget always takes precedence
    total_match = _TOTAL_PRICE_RE.search(text)
    if total_match:
        val = parse_chinese_number(total_match.group(1))
        if val is not None and val > 0:
            total_val = round(val, 2)
            result["total_price"] = total_val
            result["unit_price"] = round(total_val / effective_qty, 2)
            result["price_kind"] = "total"
            return result

    # 2. Explicit unit price ("单价 22999 元", "每台 2000 元")
    unit_match = _UNIT_PRICE_RE.search(text)
    if unit_match:
        unit_val = parse_chinese_number(unit_match.group(1))
        if unit_val is not None and unit_val > 0:
            unit_rounded = round(unit_val, 2)
            result["unit_price"] = unit_rounded
            result["total_price"] = round(effective_qty * unit_rounded, 2)
            result["price_kind"] = "unit"
            return result

    # 3. General currency-tagged amount ("8000元", "￥6800", "3500块", "1.2万元", "三千元")
    curr_match = _CURRENCY_AMOUNT_RE.search(text)
    if curr_match:
        raw_num = curr_match.group(1) or curr_match.group(2)
        val = parse_chinese_number(raw_num)
        if val is not None and val > 0:
            prefix_window = text[max(0, curr_match.start() - 6) : curr_match.start()]
            if any(w in prefix_window for w in ("共", "总共", "合计", "总计", "总价", "预算")):
                total_val = round(val, 2)
                result["total_price"] = total_val
                result["unit_price"] = round(total_val / effective_qty, 2)
                result["price_kind"] = "total"
            elif explicit_qty and explicit_qty > 1:
                unit_rounded = round(val, 2)
                result["unit_price"] = unit_rounded
                result["total_price"] = round(effective_qty * unit_rounded, 2)
                result["price_kind"] = "unit"
            else:
                val_rounded = round(val, 2)
                result["unit_price"] = val_rounded
                result["total_price"] = val_rounded
                result["price_kind"] = "currency"
            return result

    # 4. Standalone "万"/"千"/"k"/"w" in a purchase or clarification context
    if allow_bare_price or any(
        w in text for w in ("采购", "购买", "买", "审批", "报销", "预算", "单价", "价格", "报价")
    ):
        mag_match = _MAGNITUDE_RE.search(text)
        if mag_match:
            val = parse_chinese_number(mag_match.group(1) + mag_match.group(2))
            if val is not None and val > 0:
                val_rounded = round(val, 2)
                prefix_window = text[max(0, mag_match.start() - 6) : mag_match.start()]
                if any(w in prefix_window for w in ("共", "总共", "合计", "总计", "总价", "预算")):
                    result["total_price"] = val_rounded
                    result["unit_price"] = round(val_rounded / effective_qty, 2)
                    result["price_kind"] = "total"
                elif explicit_qty and explicit_qty > 1:
                    result["unit_price"] = val_rounded
                    result["total_price"] = round(effective_qty * val_rounded, 2)
                    result["price_kind"] = "unit"
                else:
                    result["unit_price"] = val_rounded
                    result["total_price"] = val_rounded
                    result["price_kind"] = "magnitude"
                return result

    # 5. Bare positive number ONLY during active purchase clarification turns
    if allow_bare_price:
        cleaned_no_qty = _QUANTITY_RE.sub(" ", text)
        bare_match = _BARE_PRICE_RE.search(cleaned_no_qty)
        if bare_match:
            val = parse_chinese_number(bare_match.group(1))
            if val is not None and val > 0:
                val_rounded = round(val, 2)
                if explicit_qty and explicit_qty > 1:
                    result["unit_price"] = val_rounded
                    result["total_price"] = round(effective_qty * val_rounded, 2)
                else:
                    result["unit_price"] = val_rounded
                    result["total_price"] = val_rounded
                result["price_kind"] = "bare"
                return result

    return result


def parse_purchase_amount(text: str) -> Optional[float]:
    """Dynamically extracts total purchase amount in RMB from natural Chinese/English text.

    Avoids false positives on model numbers (e.g. 'MacBook Pro 16', 'P1', '2026').
    """
    parsed = extract_purchase_quantity_and_prices(text, allow_bare_price=False)
    total = parsed.get("total_price")
    return float(total) if isinstance(total, (int, float)) and total > 0 else None


def merge_purchase_amounts_across_turns(turns: Sequence[str]) -> Dict[str, Any]:
    """Merges quantity, unit_price, and total_price across multi-turn clarification inputs."""
    merged_qty: Optional[int] = None
    merged_unit: Optional[float] = None
    merged_total: Optional[float] = None
    last_price_kind: Optional[str] = None

    for idx, turn_text in enumerate(turns):
        if not turn_text or not turn_text.strip():
            continue
        is_followup = idx > 0
        parsed = extract_purchase_quantity_and_prices(turn_text, allow_bare_price=is_followup)
        turn_qty = parsed.get("quantity")
        turn_unit = parsed.get("unit_price")
        turn_total = parsed.get("total_price")
        turn_kind = parsed.get("price_kind")

        if turn_qty is not None:
            merged_qty = int(turn_qty)

        if turn_kind == "total" and turn_total is not None:
            merged_total = round(float(turn_total), 2)
            eff_qty = merged_qty or 1
            merged_unit = round(merged_total / eff_qty, 2)
            last_price_kind = "total"
        elif turn_kind == "unit" and turn_unit is not None:
            merged_unit = round(float(turn_unit), 2)
            eff_qty = merged_qty or 1
            merged_total = round(merged_unit * eff_qty, 2)
            last_price_kind = "unit"
        elif turn_unit is not None:
            # Ambiguous currency/magnitude/bare price on a follow-up turn
            val = round(float(turn_unit), 2)
            if merged_qty and merged_qty > 1:
                if any(w in turn_text for w in ("共", "总共", "合计", "总计", "总价", "预算")):
                    merged_total = val
                    merged_unit = round(val / merged_qty, 2)
                    last_price_kind = "total"
                else:
                    merged_unit = val
                    merged_total = round(val * merged_qty, 2)
                    last_price_kind = "unit"
            else:
                merged_unit = val
                merged_total = val
                last_price_kind = turn_kind
        elif turn_qty is not None and merged_unit is not None:
            # Quantity updated after price was already known
            eff_qty = merged_qty if merged_qty is not None and merged_qty > 0 else turn_qty
            if last_price_kind == "total" and merged_total is not None:
                merged_unit = round(merged_total / eff_qty, 2)
            else:
                merged_total = round(merged_unit * eff_qty, 2)

    return {
        "quantity": merged_qty,
        "unit_price": merged_unit,
        "total_price": merged_total,
    }


# ---------------------------------------------------------------------------
# 2. Structured Result & Pending Clarification Context Detection
# ---------------------------------------------------------------------------


@dataclass
class SlotExtractionResult:
    """Standardized output of the hybrid semantic slot extraction engine."""

    tool_name: str
    slots: Dict[str, Any] = field(default_factory=dict)
    missing_slots: List[str] = field(default_factory=list)
    clarification_question: str = ""
    extraction_method: str = "deterministic"
    resolved_from_hr: bool = False
    hr_candidates: List[Dict[str, Any]] = field(default_factory=list)
    merged_from_history: bool = False

    @property
    def is_complete(self) -> bool:
        return len(self.missing_slots) == 0


# Deterministic enterprise clarification header markers (zero emojis, zero internal codes)
_CLARIFICATION_MARKERS: Dict[str, Tuple[str, ...]] = {
    "create_purchase": (
        "为确保采购申请准确提交并核对审批额度，请补充以下信息：",
        "为确保采购审批单准确提交，请补充以下信息：",
    ),
    "approval": (
        "为确保采购申请准确提交并核对审批额度，请补充以下信息：",
        "为确保采购审批单准确提交，请补充以下信息：",
    ),
    "send_email": (
        "为确保邮件准确发送，请补充以下信息：",
        "企业通讯录中存在多位名为",
        "未在企业通讯录中查询到名为",
    ),
    "create_ticket": (
        "为确保工单准确派发与处理，请补充以下信息：",
    ),
    "query_employee": (
        "为准确查询员工档案信息，请补充以下信息：",
    ),
    "query_inventory": (
        "为准确查询设备与物料库存，请补充以下信息：",
    ),
    "search_knowledge_base": (
        "为准确检索企业规章制度，请补充以下信息：",
    ),
}

_CANCEL_CLARIFICATION_WORDS = {
    "取消",
    "算了",
    "不用了",
    "先不办了",
    "先不买了",
    "不发了",
    "不提了",
    "先算了",
    "放弃",
    "退出",
    "cancel",
}

_TOPIC_SWITCH_KEYWORDS = (
    "怎么报销",
    "报销标准",
    "住宿标准",
    "差旅标准",
    "年假",
    "请假",
    "借用期限",
    "规章制度",
    "管理规定",
    "你是谁",
    "你好",
    "您好",
    "谢谢",
    "再见",
    "帮我翻译",
    "写一段代码",
)


def _identify_clarified_tool_from_ai_text(ai_text: str) -> Optional[str]:
    """Maps an assistant clarification message back to its canonical business tool name."""
    if not ai_text:
        return None
    for tool_name, markers in _CLARIFICATION_MARKERS.items():
        if any(marker in ai_text for marker in markers):
            return tool_name
    return None


def _is_clarification_cancelled_or_switched(current_query: str, pending_tool: str) -> bool:
    """Detects whether the user cancelled clarification or clearly switched to another topic."""
    q_clean = re.sub(r"[\s,，。！？!?.~～]+", "", current_query).lower()
    if not q_clean:
        return True
    if q_clean in _CANCEL_CLARIFICATION_WORDS:
        return True
    if current_query.strip().startswith("/"):
        return True
    if any(kw in q_clean for kw in _TOPIC_SWITCH_KEYWORDS):
        # Allow if the user is still explicitly mentioning the pending tool's domain
        if pending_tool in ("create_purchase", "approval") and parse_purchase_amount(current_query) is not None:
            return False
        if pending_tool == "send_email" and ("@" in current_query or "{{EMAIL_" in current_query):
            return False
        return True

    # Cross-tool explicit switch guard (e.g., was clarifying purchase, now asks to send email or create ticket)
    if pending_tool in ("create_purchase", "approval"):
        if any(k in q_clean for k in ("发邮件", "发封邮件", "创建工单", "提个工单", "查库存", "查员工")):
            return True
    elif pending_tool == "send_email":
        if any(k in q_clean for k in ("申请采购", "发起审批", "创建工单", "提个工单", "查库存")):
            return True
    elif pending_tool == "create_ticket":
        if any(k in q_clean for k in ("申请采购", "发起审批", "发邮件", "发封邮件")):
            return True
    elif pending_tool in ("query_employee", "query_inventory"):
        if any(k in q_clean for k in ("申请采购", "发起审批", "发邮件", "创建工单")):
            return True

    return False


def detect_pending_clarification_context(
    messages: Sequence[BaseMessage],
    metadata: Optional[Dict[str, Any]] = None,
    current_query: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Detects an active missing-slot clarification loop from metadata or pure messages history.

    Supports both:
      - In-memory LangGraph state reuse (`metadata["pending_slot_tool"]`)
      - Stateless WebSocket multi-turn replay (`messages` loaded from DB)
    Returns dict `{pending_tool, pending_slots, prior_user_turns}` or None.
    """
    meta = metadata or {}
    prior_msgs = list(messages[:-1]) if messages else []
    active_query = (
        current_query
        if current_query is not None
        else (str(getattr(messages[-1], "content", "")).strip() if messages else "")
    )

    pending_tool: Optional[str] = None
    pending_slots: Dict[str, Any] = {}

    # 1. Inspect immediately preceding assistant message first (authoritative for WS reload)
    last_ai_idx = -1
    for idx in range(len(prior_msgs) - 1, -1, -1):
        msg = prior_msgs[idx]
        if isinstance(msg, AIMessage):
            last_ai_idx = idx
            pending_tool = _identify_clarified_tool_from_ai_text(str(getattr(msg, "content", "")))
            break
        if isinstance(msg, HumanMessage):
            # Another human turn without an intervening AI clarification breaks the chain
            break

    # 2. Merge with explicit in-memory metadata if consistent
    meta_tool = str(meta.get("pending_slot_tool") or "").strip()
    if meta_tool and (pending_tool is None or meta_tool == pending_tool or {meta_tool, pending_tool} == {"create_purchase", "approval"}):
        pending_tool = meta_tool
        if isinstance(meta.get("pending_slots"), dict):
            pending_slots = dict(meta["pending_slots"])

    if not pending_tool:
        return None

    if _is_clarification_cancelled_or_switched(active_query, pending_tool):
        return None

    # 3. Walk backward through contiguous clarification rounds to gather all user turns in this chain
    prior_user_turns: List[str] = []
    if last_ai_idx >= 0:
        idx = last_ai_idx
        while idx >= 0:
            msg = prior_msgs[idx]
            if isinstance(msg, AIMessage):
                ai_tool = _identify_clarified_tool_from_ai_text(str(getattr(msg, "content", "")))
                if ai_tool and (ai_tool == pending_tool or {ai_tool, pending_tool} == {"create_purchase", "approval"}):
                    idx -= 1
                    continue
                break
            if isinstance(msg, HumanMessage):
                txt = str(getattr(msg, "content", "")).strip()
                if txt and (not prior_user_turns or prior_user_turns[-1] != txt):
                    prior_user_turns.append(txt)
                idx -= 1
                # Continue walking only if the turn before this user message was ALSO a clarification for the same tool
                if idx >= 0 and isinstance(prior_msgs[idx], AIMessage):
                    prev_ai_tool = _identify_clarified_tool_from_ai_text(str(getattr(prior_msgs[idx], "content", "")))
                    if prev_ai_tool and (
                        prev_ai_tool == pending_tool or {prev_ai_tool, pending_tool} == {"create_purchase", "approval"}
                    ):
                        continue
                break
            idx -= 1

    prior_user_turns.reverse()
    return {
        "pending_tool": pending_tool,
        "pending_slots": pending_slots,
        "prior_user_turns": prior_user_turns,
    }


# ---------------------------------------------------------------------------
# 3. Domain Dictionaries & Deterministic Per-Tool Extractors
# ---------------------------------------------------------------------------

KNOWN_DEPARTMENTS: Tuple[str, ...] = tuple(
    sorted(
        {
            "IT运维部",
            "行政后勤部",
            "人力资源部",
            "客户服务部",
            "信息安全部",
            "市场营销部",
            "产品研发部",
            "技术研发部",
            "供应链部",
            "法务合规部",
            "研发部",
            "财务部",
            "行政部",
            "运维部",
            "HR部",
            "人事部",
            "市场部",
            "销售部",
            "产品部",
            "客服部",
            "安全部",
            "采购部",
            "运营部",
            "技术部",
        },
        key=lambda s: (-len(s), s),
    )
)

KNOWN_INVENTORY_ITEMS: Tuple[str, ...] = tuple(
    sorted(
        {
            "MacBook Pro 16",
            "MacBook Pro 14",
            "MacBook Pro",
            "MacBook Air",
            "MacBook",
            "ThinkPad X1 Carbon",
            "ThinkPad",
            "Dell UltraSharp 显示器",
            "Dell UltraSharp",
            "Dell R760",
            "Logitech MX Master 3S",
            "Logitech",
            "Herman Miller 办公椅",
            "Herman Miller",
            "iPhone",
            "iPad",
            "人体工学椅",
            "办公电脑",
            "笔记本电脑",
            "台式电脑",
            "无线鼠标",
            "机械键盘",
            "蓝牙耳机",
            "会议设备",
            "服务器集群",
            "办公椅",
            "显示器",
            "笔记本",
            "投影仪",
            "打印机",
            "服务器",
            "交换机",
            "路由器",
            "备用机",
            "耳机",
            "鼠标",
            "键盘",
            "电脑",
            "办公桌",
            "工牌",
            "显卡",
            "GPU服务器",
            "存储阵列",
        },
        key=lambda s: (-len(s), s),
    )
)

_GENERIC_NAME_STOPLIST = {
    "员工",
    "同事",
    "人员",
    "大家",
    "所有人",
    "全部",
    "部门",
    "公司",
    "企业",
    "一下",
    "信息",
    "档案",
    "资料",
    "联系方式",
    "邮箱",
    "邮件",
    "电话",
    "职级",
    "职位",
    "工号",
    "个人",
    "这个",
    "那个",
    "他们",
    "我们",
    "你们",
    "请问",
    "帮我",
    "麻烦",
    "查询",
    "查找",
    "看看",
    "一下吧",
    "谁",
    "哪位",
    "主管",
    "经理",
    "总监",
    "老板",
    "领导",
    "通知",
    "汇报",
    "确认",
    "处理",
    "一下他",
    "系统",
    "客服",
    "支持",
    "运维",
    "管理员",
}

_GENERIC_ITEM_STOPLIST = {
    "库存",
    "余量",
    "现货",
    "备货",
    "设备",
    "办公设备",
    "办公硬件设备",
    "硬件设备",
    "资产",
    "物资",
    "物料",
    "物品",
    "东西",
    "一下",
    "仓库",
    "公司",
    "全部",
    "所有",
    "采购",
    "购买",
    "申请",
    "审批",
    "大额",
    "大额采购",
    "大额设备",
    "商品",
    "产品",
    "货品",
    "一些",
    "一批",
    "几个",
    "几台",
}

_EMAIL_RE = re.compile(r"(?:\{\{EMAIL_[a-zA-Z0-9_]+\}\}|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
_EMP_ID_RE = re.compile(r"\bEMP-\d+\b", re.IGNORECASE)
_PERSON_PLACEHOLDER_RE = re.compile(r"\{\{PERSON_[a-zA-Z0-9_]+\}\}")


def _extract_department(text: str) -> Optional[str]:
    if not text:
        return None
    for dept in KNOWN_DEPARTMENTS:
        if dept.lower() in text.lower():
            return dept
    m = re.search(r"([一-龥A-Za-z]{2,8}部)", text)
    if m:
        cand = m.group(1)
        if cand not in ("全部", "内部", "外部", "总部", "底部", "顶部", "局部"):
            return cand
    return None


def _is_valid_person_candidate(name: str) -> bool:
    cleaned = name.strip()
    if not cleaned:
        return False
    if _EMP_ID_RE.fullmatch(cleaned) or _PERSON_PLACEHOLDER_RE.fullmatch(cleaned):
        return True
    if cleaned in _GENERIC_NAME_STOPLIST:
        return False
    if any(cleaned.startswith(p) for p in ("一下", "帮我", "请问", "这个", "那个", "什么", "怎么", "如何", "查询", "看看", "所有", "全部", "各位", "明天", "今天", "下午", "上午")):
        return False
    if any(cleaned.endswith(s) for s in ("部门", "公司", "系统", "邮箱", "邮件", "工单", "库存", "制度", "流程", "标准", "会议", "通知", "设备", "电脑", "采购")):
        return False
    if "部" in cleaned and not cleaned.startswith("部"):
        return False
    if "的" in cleaned:
        return False
    if re.fullmatch(r"[一-龥]{2,4}", cleaned):
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,24}", cleaned) and cleaned.lower() not in {"email", "mail", "send", "query", "employee", "hr", "it", "oa", "erp"}:
        return True
    return False


def _extract_employee_slots_deterministic(
    turns: Sequence[str],
    *,
    is_followup: bool = False,
) -> Dict[str, Any]:
    """Extracts name/employee_id and optional department for query_employee."""
    slots: Dict[str, Any] = {}
    combined = "\n".join(t for t in turns if t)

    dept = _extract_department(combined)
    if dept:
        slots["department"] = dept

    # Inspect newest turn first so follow-ups override older incomplete phrasing
    for idx, raw_text in enumerate(reversed(turns)):
        text = raw_text.strip()
        if not text:
            continue

        emp_id_m = _EMP_ID_RE.search(text)
        if emp_id_m:
            slots["name"] = emp_id_m.group(0).upper()
            break

        ph_m = _PERSON_PLACEHOLDER_RE.search(text)
        if ph_m:
            slots["name"] = ph_m.group(0)
            break

        search_text = re.sub(rf"{re.escape(dept)}(?:的)?", " ", text) if dept else text
        patterns = (
            r"(?:查(?:询|一下|下)?|找(?:一下|下)?|看看)\s*(?:员工|同事)?\s*([一-龥]{2,4}?|[A-Za-z][A-Za-z .'-]{1,20})\s*(?:的)?(?:部门|职级|邮箱|联系方式|电话|职位|工号|信息|档案|资料)",
            r"(?:员工|同事|姓名(?:是|为|:|：)?|名字(?:是|为|:|：)?|叫)\s*([一-龥]{2,4}?|[A-Za-z][A-Za-z .'-]{1,20})(?=[的，,。！？!?\s]|$)",
            r"([一-龥]{2,4}?)\s*(?:的)?(?:部门|职级|邮箱|联系方式|电话|工号|职位|在哪个部门|是哪个部门)",
            r"(?:查(?:询|一下|下)?|找(?:一下|下)?|看看)\s*(?:员工|同事)?\s*([一-龥]{2,4}|[A-Za-z][A-Za-z .'-]{1,20})(?=[，,。！？!?\s]|$)",
        )
        found_name: Optional[str] = None
        for pat in patterns:
            for m in re.finditer(pat, search_text):
                cand = m.group(1).strip()
                # Strip trailing particle "的" if captured
                cand = re.sub(r"的$", "", cand)
                if _is_valid_person_candidate(cand):
                    found_name = cand
                    break
            if found_name:
                break

        if not found_name and (is_followup or idx == 0 and len(turns) > 1):
            # Clean short follow-up answer like "李明" or "查一下王强" or "研发部的李明"
            stripped = re.sub(
                r"^(?:请问|请|帮我|麻烦|我想|我要|查(?:询|一下|下)?|找(?:一下|下)?|员工|同事|姓名|名字|叫|是|为|[:：\s])+",
                "",
                text,
            )
            if dept:
                stripped = stripped.replace(dept, "").lstrip("的 ")
            stripped = re.sub(r"[。！？!?，,\s]+$", "", stripped)
            if _is_valid_person_candidate(stripped):
                found_name = stripped

        if found_name:
            slots["name"] = found_name
            break

    return slots


def _is_valid_item_candidate(item: str) -> bool:
    cleaned = item.strip(" \t\r\n,，。！？!?:：\"'「」《》()（）")
    if not cleaned or len(cleaned) < 2:
        return False
    if cleaned in _GENERIC_ITEM_STOPLIST:
        return False
    if cleaned.lower() in {"item", "inventory", "stock", "device", "equipment", "purchase"}:
        return False
    if re.fullmatch(r"[\d.,，\s]+(?:元|块|万|千|台|个|件|套|把|张)?", cleaned):
        return False
    return True


def _match_known_inventory_item(text: str) -> Optional[str]:
    if not text:
        return None
    low = text.lower()
    for item in KNOWN_INVENTORY_ITEMS:
        if item.lower() in low:
            return item
    return None


def _extract_inventory_slots_deterministic(
    turns: Sequence[str],
    *,
    is_followup: bool = False,
) -> Dict[str, Any]:
    """Extracts item_name and optional category for query_inventory."""
    slots: Dict[str, Any] = {}
    combined = "\n".join(t for t in turns if t)

    dept = _extract_department(combined)
    if dept:
        slots["category"] = dept

    for idx, raw_text in enumerate(reversed(turns)):
        text = raw_text.strip()
        if not text:
            continue

        # In compound sentences ("先查一下...备用机借用标准，再帮我查一下MacBook库存"),
        # prioritize the clause containing inventory/stock cues first.
        clauses = [c.strip() for c in re.split(r"[，,。；;！？!?\n]+", text) if c.strip()]
        stock_clauses = [
            c
            for c in clauses
            if any(k in c.lower() for k in ("库存", "inventory", "余量", "现货", "备货", "还有", "还剩", "几台", "多少"))
        ]
        search_targets = stock_clauses + [text]

        matched_item: Optional[str] = None
        for seg in search_targets:
            matched_item = _match_known_inventory_item(seg)
            if matched_item:
                break

        if not matched_item:
            for seg in search_targets:
                m = re.search(
                    r"(?:查(?:询|一下|下)?|看看|有没有|还剩(?:多少)?|还有(?:多少|几[台个把张套])?)\s*([A-Za-z0-9一-龥 ._-]{2,24}?)\s*(?:的)?(?:库存|余量|现货|备货|还有吗|还剩)",
                    seg,
                    re.IGNORECASE,
                )
                if m:
                    cand = re.sub(r"^(?:一下|下|公司|仓库|目前|现在|当前|的)+", "", m.group(1).strip())
                    if dept and cand.startswith(dept):
                        cand = cand[len(dept) :].lstrip("的 ")
                    if _is_valid_item_candidate(cand):
                        matched_item = cand
                        break

        if not matched_item and (is_followup or (idx == 0 and len(turns) > 1)):
            stripped = re.sub(
                r"^(?:请问|请|帮我|麻烦|查(?:询|一下|下)?|看看|我想查|设备|物料|物品|是|为|[:：\s])+",
                "",
                text,
            )
            stripped = re.sub(r"(?:的)?(?:库存|余量|现货|备货)[。！？!?\s]*$", "", stripped).strip()
            if _is_valid_item_candidate(stripped):
                matched_item = stripped

        if matched_item:
            slots["item_name"] = matched_item
            break

    return slots


def _infer_ticket_priority(text: str) -> str:
    m = re.search(r"\b(P[0-4])\b", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    low = text.lower()
    if any(k in low for k in ("全网瘫痪", "生产宕机", "全面中断", "核心崩溃", "灾难", "p0")):
        return "P0"
    if any(k in low for k in ("紧急", "加急", "宕机", "瘫痪", "崩溃", "断网", "连不上", "无法登录", "核心网络", "502", "500")):
        return "P1"
    if any(k in low for k in ("故障", "异常", "打不开", "报错", "卡顿", "蓝屏", "坏了", "无法访问", "失败", "排查")):
        return "P2"
    if any(k in low for k in ("咨询", "建议")):
        return "P4"
    return "P3"


def _infer_ticket_department(text: str) -> str:
    low = text.lower()
    hr_hits = sum(1 for k in ("考勤", "薪资", "工资", "社保", "公积金", "入职", "离职", "休假", "请假", "人事", "hr", "在职证明") if k in low)
    it_hits = sum(1 for k in ("网络", "vpn", "电脑", "系统", "服务器", "账号", "密码", "硬件", "软件", "邮箱", "it", "网关", "交换机", "打印机", "报错", "故障") if k in low)
    if hr_hits > 0 and it_hits == 0:
        return "HR"
    return "IT"


def _strip_ticket_boilerplate(text: str) -> str:
    """Strips generic command boilerplate from ticket requests to inspect substantive content."""
    cleaned = text.strip()
    cleaned = re.sub(r"^/ticket\b\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^(?:请帮我|麻烦帮我|帮我|请|麻烦|我要|我想|需要|给我|赶紧|立刻|马上)+",
        "",
        cleaned,
    ).strip()
    cleaned = re.sub(
        r"^(?:创建|新建|提交|发起|提个|提一个|开个|开一个|拉个|拉一个|建个|建一个|报一个|提)\s*(?:IT|HR|运维|报修|故障|服务|支持)?\s*(?:工单|报修单|报修|ticket)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"^[，,：:。!！\s]+", "", cleaned).strip()
    cleaned = re.sub(r"^(?:一下|下|吧|呢|啊|哦)+$", "", cleaned).strip()
    return cleaned


def _extract_ticket_slots_deterministic(turns: Sequence[str]) -> Dict[str, Any]:
    """Extracts title, description, priority, and department for create_ticket."""
    substantive_parts: List[str] = []
    for t in turns:
        core = _strip_ticket_boilerplate(t)
        # Filter out pure non-substantive filler
        if len(core) >= 2 and core not in {"工单", "报修", "问题", "求助", "处理一下", "帮忙处理", "故障"}:
            substantive_parts.append(core)

    if not substantive_parts:
        return {}

    full_desc = "；".join(dict.fromkeys(substantive_parts))
    # Build a crisp title from the first meaningful clause
    first_clause = re.split(r"[。！？!?\n；;，,]+", substantive_parts[0])[0].strip()
    title_cand = re.sub(r"^(?:申请|反馈|反映|报告|说明|情况是|问题是|标题是|主题是|标题[:：]|主题[:：])", "", first_clause).strip()
    if len(title_cand) < 2:
        title_cand = first_clause
    title = title_cand[:32]

    combined_raw = "\n".join(turns)
    return {
        "title": title,
        "description": full_desc,
        "priority": _infer_ticket_priority(combined_raw),
        "department": _infer_ticket_department(combined_raw),
    }


def _extract_email_recipient_name(text: str) -> Optional[str]:
    """Extracts an intended internal employee name from email-sending text."""
    ph_m = _PERSON_PLACEHOLDER_RE.search(text)
    if ph_m:
        return ph_m.group(0)

    emp_id_m = _EMP_ID_RE.search(text)
    if emp_id_m:
        return emp_id_m.group(0).upper()

    patterns = (
        r"(?:给|向|发给|发送给|转发给|通知|抄送给|收件人(?:是|为|:|：)?)\s*(?:一下|下)?\s*(?:[一-龥A-Za-z]{2,6}部(?:的)?)?\s*([一-龥]{2,4}|[A-Za-z][A-Za-z .'-]{1,20})(?=[发写寄说告诉通知，,。:：\s]|$)",
        r"(?:发(?:一)?(?:封|个)?邮件给|写(?:一)?(?:封|个)?邮件给)\s*(?:[一-龥A-Za-z]{2,6}部(?:的)?)?\s*([一-龥]{2,4}|[A-Za-z][A-Za-z .'-]{1,20})",
    )
    for pat in patterns:
        for m in re.finditer(pat, text):
            cand = m.group(1).strip()
            cand = re.sub(r"(?:发|写|寄|说|发封|发个|发邮件|邮件|的)$", "", cand).strip()
            if _is_valid_person_candidate(cand):
                return cand
    return None


def _extract_email_slots_deterministic(
    turns: Sequence[str],
    *,
    is_followup: bool = False,
) -> Dict[str, Any]:
    """Extracts to_email (or recipient_name for HR lookup), subject, and body."""
    slots: Dict[str, Any] = {}
    combined = "\n".join(t for t in turns if t)

    # 1. Explicit email address (newest turn first)
    for text in reversed(turns):
        email_m = _EMAIL_RE.search(text)
        if email_m:
            slots["to_email"] = email_m.group(0)
            break

    # 2. Optional department hint for disambiguating duplicate names
    dept = _extract_department(combined)
    if dept:
        slots["_recipient_department"] = dept

    # 3. Recipient name if no explicit email address yet
    if "to_email" not in slots:
        for idx, text in enumerate(reversed(turns)):
            cand_name = _extract_email_recipient_name(text)
            if cand_name:
                slots["_recipient_name"] = cand_name
                break
            if is_followup and idx == 0:
                stripped = re.sub(r"^(?:收件人|发给|给|是|为|[:：\s])+", "", text.strip())
                if dept:
                    stripped = stripped.replace(dept, "").lstrip("的那位 ")
                stripped = re.sub(r"(?:那位|这位|同事|员工|[。！？!?,，\s]+)$", "", stripped).strip()
                if _is_valid_person_candidate(stripped):
                    slots["_recipient_name"] = stripped
                    break

    # 4. Explicit subject & body extraction
    subject: Optional[str] = None
    body: Optional[str] = None

    subj_m = re.search(
        r"(?:主题|标题|题目)\s*(?:为|是|:|：)\s*[「\"'《]?([^，,。；;\n」\"'》]{2,60})[」\"'》]?",
        combined,
    )
    if subj_m:
        subject = subj_m.group(1).strip()

    body_m = re.search(
        r"(?:内容|正文|消息|邮件内容)\s*(?:为|是|:|：)\s*(.+)",
        combined,
        re.DOTALL,
    )
    if body_m:
        body = body_m.group(1).strip()

    # 5. Natural clause extraction when user didn't use explicit "主题:/正文:" labels
    if not body:
        natural_parts: List[str] = []
        for text in turns:
            t_clean = text.strip()
            # Remove explicit email and command prefix
            t_clean = _EMAIL_RE.sub("", t_clean)
            t_clean = re.sub(
                r"(?:请帮我|麻烦帮我|帮我|请|麻烦|我要|我想)?\s*(?:给|向|发给|发送给)?\s*(?:[一-龥A-Za-z]{2,6}部(?:的)?)?\s*(?:\{\{PERSON_[^}]+\}\}|EMP-\d+|[一-龥]{2,4})?\s*(?:发(?:送)?|写|寄)(?:一)?(?:封|个)?(?:电子)?(?:邮件|email|mail)\s*(?:给)?\s*(?:\{\{PERSON_[^}]+\}\}|EMP-\d+|[一-龥]{2,4})?",
                "",
                t_clean,
                flags=re.IGNORECASE,
            )
            t_clean = re.sub(r"(?:主题|标题|题目)\s*(?:为|是|:|：)\s*[「\"'《]?[^，,。；;\n」\"'》]{2,60}[」\"'》]?", "", t_clean)
            t_clean = re.sub(r"^(?:收件人(?:是|为|:|：)?|发给|给|转发给)\s*(?:\{\{PERSON_[^}]+\}\}|EMP-\d+|[一-龥]{2,4})?", "", t_clean)
            t_clean = re.sub(r"^[，,：:。;；!！\s]+", "", t_clean).strip()
            # Remove leading connectors like "通知他" / "告诉她" / "说一下"
            t_clean_body = re.sub(r"^(?:通知(?:一下)?|告诉(?:一下)?|提醒(?:一下)?|说(?:一下)?|内容(?:为|是|:|：)?)\s*(?:他|她|对方)?[，,：:\s]*", "", t_clean).strip()
            if len(t_clean_body) >= 3 and t_clean_body not in {
                slots.get("_recipient_name", ""),
                slots.get("_recipient_department", ""),
                "邮件",
                "一封邮件",
                "发邮件",
                "通知",
                "那位",
            }:
                # Avoid mistaking a department disambiguation reply like "研发部的那位" as email body
                if not re.fullmatch(r"(?:[一-龥A-Za-z]{2,8}部)?(?:的)?(?:那位|这位|那个|同事|员工)?", t_clean_body):
                    natural_parts.append(t_clean_body)
        if natural_parts:
            body = "；".join(dict.fromkeys(natural_parts))

    if body and not subject:
        first_line = re.split(r"[。！？!?\n；;，,]+", body)[0].strip()
        subject = first_line[:24] if len(first_line) >= 2 else body[:24]

    if subject:
        slots["subject"] = subject
    if body:
        slots["body"] = body

    return slots


def _resolve_email_recipient_via_hr(
    recipient_name: str,
    department: Optional[str] = None,
) -> Tuple[Optional[str], List[Dict[str, Any]], bool]:
    """Strategy 5.1 Option A: looks up internal employee email via Unified HR Adapter.

    Returns (resolved_email, candidates, looked_up_ok).
      - Unique match with email -> (email, [match], True)
      - Multiple matches -> (None, candidates, True)
      - No match -> (None, [], True)
    """
    try:
        hr = get_hr_adapter()
        resp = hr.get_employee(id_or_name=recipient_name, department=department)
    except Exception as exc:
        logger.warning("[SlotExtractor] HR adapter lookup failed for '%s': %s", recipient_name, exc)
        return None, [], False

    if not isinstance(resp, dict) or resp.get("status") != "SUCCESS":
        return None, [], True

    records = resp.get("data") or []
    if not isinstance(records, list) or not records:
        return None, [], True

    # Prefer exact name match if partial LIKE returned extra entries
    exact_matches = [r for r in records if isinstance(r, dict) and str(r.get("name", "")).strip() == recipient_name.strip()]
    effective_records = exact_matches if exact_matches else [r for r in records if isinstance(r, dict)]

    if len(effective_records) == 1:
        email = str(effective_records[0].get("email") or "").strip()
        if email and ("@" in email or "{{EMAIL_" in email):
            return email, effective_records, True
        return None, effective_records, True

    return None, effective_records, True


def _extract_purchase_item_name(turns: Sequence[str]) -> Optional[str]:
    """Extracts concrete purchase item/service name across turns without fabricating defaults."""
    for raw_text in reversed(turns):
        text = raw_text.strip()
        if not text:
            continue

        # 1. Known equipment / enterprise asset catalog names (strictly item name only; NEVER price!)
        known = _match_known_inventory_item(text)
        if known:
            return known

        # 2. Explicit structured patterns
        patterns = (
            r"(?:采购|购买|申购|买|下单)\s*(?:物品|设备|产品|品名)?\s*[:：]\s*([A-Za-z0-9一-龥 ._-]{2,32}?)(?=\s*(?:\d+|[一二两三四五六七八九十]+)\s*(?:台|个|件|套|把|张|部|批|只|箱)|[，,。；;\n]|$)",
            r"(?:采购|购买|申购|帮我买|我要买|配备|配置|配|买)\s*(?:(?:\d+|[一二两三四五六七八九十]+)\s*(?:台|个|件|套|把|张|部|批|只|箱))?\s*(?:单价|每台|总价|约|大概)?\s*(?:[￥¥]?\s*[\d,.一二两三四五六七八九十百千万]+\s*(?:元|块钱|块|万元|千元|rmb)?\s*(?:的)?)?\s*([A-Za-z0-9一-龥 _-]{2,28}?)(?=[，,。；;！？!?\n]|$)",
            r"(?:品名|物品|设备名称|采购项)\s*(?:为|是|:|：)\s*([A-Za-z0-9一-龥 ._-]{2,32})",
        )
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                # Strip trailing price/quantity fragments
                cand = re.sub(r"(?:单价|每台|总价|预算|总共|共|约|大约|￥|¥|\d+\s*(?:台|个|件|套|把|张|元|块)).*$", "", cand).strip()
                cand = re.sub(r"^(?:一下|下|一台|两台|几台|一个|一批|大额|办公用|用于)+", "", cand).strip()
                cand = re.sub(r"[，,。；;！？!?\s]+$", "", cand).strip()
                if _is_valid_item_candidate(cand):
                    return cand

    return None


def _extract_purchase_reason(turns: Sequence[str]) -> Optional[str]:
    combined = "\n".join(turns)
    m = re.search(r"(?:理由|原因|事由|用途|用于)\s*(?:为|是|:|：)?\s*([^，,。；;\n]{2,60})", combined)
    if m:
        reason = m.group(1).strip()
        if len(reason) >= 2:
            return reason
    return None


def _extract_purchase_slots_deterministic(
    turns: Sequence[str],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Extracts purchase slots for create_purchase / approval (Strategy 5.2 Option A enforced)."""
    slots: Dict[str, Any] = {}

    # Honor explicit pre-supplied purchase_args (backward compatible with API & unit tests)
    explicit_args = metadata.get("purchase_args")
    if isinstance(explicit_args, dict) and explicit_args:
        if explicit_args.get("item_name"):
            slots["item_name"] = str(explicit_args["item_name"]).strip()
        if explicit_args.get("quantity") is not None:
            try:
                q = int(explicit_args["quantity"])
                if q > 0:
                    slots["quantity"] = q
            except (TypeError, ValueError):
                pass
        if explicit_args.get("unit_price") is not None:
            try:
                p = float(explicit_args["unit_price"])
                if p > 0:
                    slots["unit_price"] = round(p, 2)
            except (TypeError, ValueError):
                pass
        if explicit_args.get("department"):
            slots["department"] = str(explicit_args["department"]).strip()
        if explicit_args.get("reason"):
            slots["reason"] = str(explicit_args["reason"]).strip()

    # Fill missing fields from natural language conversation turns
    if not slots.get("item_name"):
        item_name = _extract_purchase_item_name(turns)
        if item_name:
            slots["item_name"] = item_name

    parsed_amounts = merge_purchase_amounts_across_turns(turns)
    if "quantity" not in slots and parsed_amounts.get("quantity") is not None:
        slots["quantity"] = int(parsed_amounts["quantity"])
    if "unit_price" not in slots and parsed_amounts.get("unit_price") is not None:
        slots["unit_price"] = float(parsed_amounts["unit_price"])
    if parsed_amounts.get("total_price") is not None and "unit_price" in slots:
        qty = int(slots.get("quantity") or 1)
        slots["total_price"] = round(qty * float(slots["unit_price"]), 2)

    if not slots.get("department"):
        dept = _extract_department("\n".join(turns))
        if dept:
            slots["department"] = dept
        elif metadata.get("department"):
            slots["department"] = str(metadata["department"]).strip()

    if not slots.get("reason"):
        reason = _extract_purchase_reason(turns)
        if reason:
            slots["reason"] = reason

    return slots


def _extract_kb_slots_deterministic(turns: Sequence[str]) -> Dict[str, Any]:
    """Extracts query and optional category for search_knowledge_base."""
    parts: List[str] = []
    for t in turns:
        cleaned = re.sub(r"^/(?:kb|search|rag)\b\s*", "", t.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(
            r"^(?:请帮我|帮我|请|麻烦)?(?:检索|搜索|查(?:询|一下|下)?)\s*(?:知识库|规章制度|企业制度|文档|手册|SOP)\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" ，,。：:？?")
        if len(cleaned) >= 2:
            parts.append(cleaned)

    slots: Dict[str, Any] = {}
    if parts:
        slots["query"] = " ".join(dict.fromkeys(parts))

    combined_low = "\n".join(turns).lower()
    if any(k in combined_low for k in ("报销", "差旅", "发票", "财务", "预算")):
        slots["category"] = "FINANCE"
    elif any(k in combined_low for k in ("考勤", "请假", "年假", "薪酬", "入职", "离职", "hr")):
        slots["category"] = "HR"
    elif any(k in combined_low for k in ("采购", "供应商", "招标", "询价")):
        slots["category"] = "PROCUREMENT"
    elif any(k in combined_low for k in ("安全", "保密", "脱敏", "红线")):
        slots["category"] = "SECURITY"
    elif any(k in combined_low for k in ("备用机", "vpn", "电脑", "运维", "故障", "sla")):
        slots["category"] = "IT"
    elif any(k in combined_low for k in ("售后", "投诉", "客服", "退换货")):
        slots["category"] = "CS"

    return slots


# ---------------------------------------------------------------------------
# 4. Tier 2 Lightweight Non-Thinking LLM Slot Extractor Fallback
# ---------------------------------------------------------------------------

_LLM_TOOL_SCHEMAS: Dict[str, str] = {
    "create_purchase": '{"item_name": string|null, "quantity": int|null, "unit_price": number|null, "total_price": number|null, "department": string|null, "reason": string|null}',
    "approval": '{"item_name": string|null, "quantity": int|null, "unit_price": number|null, "total_price": number|null, "department": string|null, "reason": string|null}',
    "create_ticket": '{"title": string|null, "description": string|null, "priority": "P0"|"P1"|"P2"|"P3"|"P4"|null, "department": "IT"|"HR"|null}',
    "send_email": '{"to_email": string|null, "recipient_name": string|null, "recipient_department": string|null, "subject": string|null, "body": string|null}',
    "query_employee": '{"name": string|null, "department": string|null}',
    "query_inventory": '{"item_name": string|null, "category": string|null}',
    "search_knowledge_base": '{"query": string|null, "category": "IT"|"HR"|"FINANCE"|"PROCUREMENT"|"SECURITY"|"CS"|null}',
}


def _build_llm_slot_messages(tool_name: str, turns: Sequence[str]) -> List[BaseMessage]:
    schema_hint = _LLM_TOOL_SCHEMAS.get(tool_name, "{}")
    system_prompt = (
        "你是企业智能助手的结构化语义槽位提取器。请严格从用户提供的对话内容中提取业务参数，并仅输出单个 JSON 对象。\n"
        f"目标业务工具：{tool_name}\n"
        f"严格输出 JSON Schema：{schema_hint}\n"
        "核心合规红线：\n"
        "1. 只能提取用户原文明确提到的信息，未提及的字段必须填 null；\n"
        "2. 严禁依据常识或库存目录价格推测/编造任何单价或总预算（例如提到 MacBook Pro 但用户未说价格时，unit_price 和 total_price 必须为 null）；\n"
        "3. 严禁编造邮箱地址、员工姓名或工单故障内容；\n"
        "4. 不要输出任何解释文字、思维过程或多余字段，只输出合法 JSON。"
    )
    conv_lines = [f"用户第 {idx + 1} 轮：{txt}" for idx, txt in enumerate(turns)]
    user_prompt = "\n".join(conv_lines)
    return [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]


def _parse_llm_slot_json(raw_text: str) -> Optional[Dict[str, Any]]:
    if not raw_text:
        return None
    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


async def _invoke_slot_extractor_llm(
    prompt_messages: List[BaseMessage],
    timeout_sec: float,
) -> Optional[str]:
    """Invokes the lightweight non-thinking slot extractor LLM with timeout & stream isolation."""
    llm = get_slot_extractor_llm(timeout_sec=timeout_sec, max_tokens=360)
    if llm is None:
        return None

    async_client = getattr(llm, "http_async_client", None)
    try:
        response = await asyncio.wait_for(
            llm.ainvoke(prompt_messages, config={"callbacks": [], "tags": ["internal_slot_extractor"]}),
            timeout=timeout_sec,
        )
        content = response.content if hasattr(response, "content") else response
        return content if isinstance(content, str) else str(content)
    except asyncio.TimeoutError:
        logger.warning("[SlotExtractor] Lightweight LLM timed out after %.2fs; using deterministic slots.", timeout_sec)
        return None
    except Exception as exc:
        logger.debug("[SlotExtractor] Lightweight LLM unavailable (%s); using deterministic slots.", exc)
        return None
    finally:
        if async_client is not None and hasattr(async_client, "aclose"):
            try:
                await async_client.aclose()
            except Exception:
                pass


def _text_contains_explicit_price_cue(combined_text: str) -> bool:
    """Anti-hallucination guard (Strategy 5.2 Option A): verifies user actually supplied a price/budget."""
    if not combined_text:
        return False
    if _TOTAL_PRICE_RE.search(combined_text) or _UNIT_PRICE_RE.search(combined_text) or _CURRENCY_AMOUNT_RE.search(combined_text):
        return True
    if _MAGNITUDE_RE.search(combined_text):
        return True
    return False


def _merge_llm_slots_safely(
    tool_name: str,
    det_slots: Dict[str, Any],
    llm_parsed: Dict[str, Any],
    turns: Sequence[str],
) -> Dict[str, Any]:
    """Safely merges LLM-extracted slots into deterministic slots with anti-hallucination guards."""
    merged = dict(det_slots)
    combined_text = "\n".join(turns)

    if tool_name in ("create_purchase", "approval"):
        if not merged.get("item_name"):
            cand_item = str(llm_parsed.get("item_name") or "").strip()
            if _is_valid_item_candidate(cand_item):
                merged["item_name"] = cand_item

        if "quantity" not in merged and llm_parsed.get("quantity") is not None:
            try:
                q = int(llm_parsed["quantity"])
                if 1 <= q <= 10000 and (_QUANTITY_RE.search(combined_text) or str(q) in combined_text):
                    merged["quantity"] = q
            except (TypeError, ValueError):
                pass

        # Strategy 5.2 Option A Anti-Hallucination Guard:
        # NEVER accept an LLM-supplied unit_price/total_price unless the user's text actually has a price cue!
        if "unit_price" not in merged and _text_contains_explicit_price_cue(combined_text):
            raw_unit = llm_parsed.get("unit_price")
            raw_total = llm_parsed.get("total_price")
            eff_qty = int(merged.get("quantity") or 1)
            try:
                if raw_unit is not None and float(raw_unit) > 0:
                    merged["unit_price"] = round(float(raw_unit), 2)
                elif raw_total is not None and float(raw_total) > 0:
                    merged["unit_price"] = round(float(raw_total) / eff_qty, 2)
            except (TypeError, ValueError):
                pass

        if not merged.get("department"):
            cand_dept = str(llm_parsed.get("department") or "").strip()
            if cand_dept and cand_dept in combined_text:
                merged["department"] = cand_dept

        if not merged.get("reason"):
            cand_reason = str(llm_parsed.get("reason") or "").strip()
            if len(cand_reason) >= 2 and cand_reason not in ("硬件升级需求", "办公设备采购"):
                merged["reason"] = cand_reason

    elif tool_name == "create_ticket":
        if not merged.get("title"):
            cand_title = str(llm_parsed.get("title") or "").strip()
            if len(cand_title) >= 2 and cand_title not in ("客服支持工单", "工单", "问题", "报修"):
                # Ensure user actually provided substantive content beyond bare command
                if any(len(_strip_ticket_boilerplate(t)) >= 2 for t in turns):
                    merged["title"] = cand_title[:32]
        if not merged.get("description"):
            cand_desc = str(llm_parsed.get("description") or "").strip()
            if len(cand_desc) >= 2 and any(len(_strip_ticket_boilerplate(t)) >= 2 for t in turns):
                merged["description"] = cand_desc
        if "priority" not in merged:
            cand_p = str(llm_parsed.get("priority") or "").strip().upper()
            if cand_p in ("P0", "P1", "P2", "P3", "P4"):
                merged["priority"] = cand_p
        if "department" not in merged:
            cand_d = str(llm_parsed.get("department") or "").strip().upper()
            if cand_d in ("IT", "HR"):
                merged["department"] = cand_d

    elif tool_name == "send_email":
        if not merged.get("to_email"):
            cand_email = str(llm_parsed.get("to_email") or "").strip()
            if cand_email and _EMAIL_RE.fullmatch(cand_email) and cand_email in combined_text:
                merged["to_email"] = cand_email
        if not merged.get("to_email") and not merged.get("_recipient_name"):
            cand_name = str(llm_parsed.get("recipient_name") or "").strip()
            if _is_valid_person_candidate(cand_name) and cand_name in combined_text:
                merged["_recipient_name"] = cand_name
        if not merged.get("_recipient_department"):
            cand_dept = str(llm_parsed.get("recipient_department") or "").strip()
            if cand_dept and cand_dept in combined_text:
                merged["_recipient_department"] = cand_dept
        if not merged.get("body"):
            cand_body = str(llm_parsed.get("body") or "").strip()
            if len(cand_body) >= 3 and cand_body not in ("系统自动化通知", "通知", "邮件内容"):
                # Verify user actually gave more than just "发邮件给XX"
                stripped_all = re.sub(
                    r"(?:请帮我|帮我|请|麻烦|发(?:送)?|写|一封|邮件|给|向|收件人|员工|同事|\s|[，,。！？!?])+",
                    "",
                    combined_text,
                )
                if merged.get("_recipient_name"):
                    stripped_all = stripped_all.replace(str(merged["_recipient_name"]), "")
                if merged.get("to_email"):
                    stripped_all = stripped_all.replace(str(merged["to_email"]), "")
                if len(stripped_all) >= 3:
                    merged["body"] = cand_body
        if not merged.get("subject"):
            cand_subj = str(llm_parsed.get("subject") or "").strip()
            if len(cand_subj) >= 2 and merged.get("body") and cand_subj not in ("系统自动化通知",):
                merged["subject"] = cand_subj[:48]
            elif merged.get("body"):
                merged["subject"] = str(merged["body"])[:24]

    elif tool_name == "query_employee":
        if not merged.get("name"):
            cand_name = str(llm_parsed.get("name") or "").strip()
            if _is_valid_person_candidate(cand_name) and cand_name in combined_text:
                merged["name"] = cand_name
        if not merged.get("department"):
            cand_dept = str(llm_parsed.get("department") or "").strip()
            if cand_dept and cand_dept in combined_text:
                merged["department"] = cand_dept

    elif tool_name == "query_inventory":
        if not merged.get("item_name"):
            cand_item = str(llm_parsed.get("item_name") or "").strip()
            if _is_valid_item_candidate(cand_item) and cand_item.lower() in combined_text.lower():
                merged["item_name"] = cand_item
        if not merged.get("category"):
            cand_cat = str(llm_parsed.get("category") or "").strip()
            if cand_cat and cand_cat in combined_text:
                merged["category"] = cand_cat

    elif tool_name == "search_knowledge_base":
        if not merged.get("query"):
            cand_q = str(llm_parsed.get("query") or "").strip()
            if len(cand_q) >= 2:
                merged["query"] = cand_q
        if not merged.get("category"):
            cand_cat = str(llm_parsed.get("category") or "").strip().upper()
            if cand_cat in ("IT", "HR", "FINANCE", "PROCUREMENT", "SECURITY", "CS"):
                merged["category"] = cand_cat

    return merged


# ---------------------------------------------------------------------------
# 5. Validation & Neutral Polite Clarification Message Builders (Zero Emoji)
# ---------------------------------------------------------------------------


def _validate_and_build_clarification(
    tool_name: str,
    raw_slots: Dict[str, Any],
    metadata: Dict[str, Any],
    *,
    extraction_method: str,
    merged_from_history: bool,
) -> SlotExtractionResult:
    """Validates required slots, runs Option A HR lookup for send_email, and builds clarification."""
    slots = dict(raw_slots)
    clean_slots: Dict[str, Any] = {}
    missing: List[str] = []
    resolved_from_hr = False
    hr_candidates: List[Dict[str, Any]] = []
    clarification = ""

    if tool_name in ("create_purchase", "approval"):
        item_name = str(slots.get("item_name") or "").strip()
        if not _is_valid_item_candidate(item_name):
            slots.pop("item_name", None)
            missing.append("item_name")

        unit_price = slots.get("unit_price")
        if not isinstance(unit_price, (int, float)) or float(unit_price) <= 0:
            slots.pop("unit_price", None)
            missing.append("unit_price")

        if not missing:
            qty = int(slots.get("quantity") or 1)
            unit_p = round(float(slots["unit_price"]), 2)
            dept = str(slots.get("department") or metadata.get("department") or "未指定部门").strip()
            reason = str(slots.get("reason") or "办公设备采购").strip()
            clean_slots = {
                "item_name": item_name,
                "quantity": qty,
                "unit_price": unit_p,
                "total_price": round(qty * unit_p, 2),
                "department": dept,
                "reason": reason,
            }
            return SlotExtractionResult(
                tool_name=tool_name,
                slots=clean_slots,
                missing_slots=[],
                clarification_question="",
                extraction_method=extraction_method,
                merged_from_history=merged_from_history,
            )

        # Build concise, neutral enterprise clarification (Strategy 5.2 Option A)
        known_bits: List[str] = []
        if slots.get("item_name"):
            known_bits.append(f"采购物品：{slots['item_name']}")
        if slots.get("quantity"):
            known_bits.append(f"数量：{slots['quantity']}")
        if slots.get("unit_price"):
            known_bits.append(f"预估单价：￥{float(slots['unit_price']):,.2f}")

        req_lines: List[str] = []
        if "item_name" in missing:
            req_lines.append("- **采购物品名称**：请说明具体需要采购的设备、物料或服务名称")
        if "unit_price" in missing:
            req_lines.append(
                "- **预估单价或总预算**：请明确填写预估单价（如「单价 8000 元」）或总预算（如「总价 16000 元」）；为严格遵循采购财务合规与 5,000 元审批门槛核验，系统不自动套用目录参考价"
            )
        if not slots.get("quantity"):
            req_lines.append("- **采购数量**（可选，未说明时默认按 1 计）")

        header = "为确保采购申请准确提交并核对审批额度，请补充以下信息："
        known_line = f"\n\n当前已识别信息：{'，'.join(known_bits)}。" if known_bits else ""
        clarification = f"{header}{known_line}\n\n" + "\n".join(req_lines) + "\n\n您可直接回复补充信息，我将立即为您继续办理。"

    elif tool_name == "send_email":
        hr_not_found_name: Optional[str] = None
        recipient_name = str(slots.get("_recipient_name") or "").strip()
        recipient_dept = str(slots.get("_recipient_department") or "").strip() or None

        # Strategy 5.1 Option A: auto-resolve employee email via HR Adapter
        if not slots.get("to_email") and recipient_name:
            resolved_email, candidates, _ = _resolve_email_recipient_via_hr(recipient_name, department=recipient_dept)
            if resolved_email:
                slots["to_email"] = resolved_email
                resolved_from_hr = True
                hr_candidates = candidates
            elif len(candidates) > 1:
                hr_candidates = candidates
                missing.append("to_email")
            else:
                hr_not_found_name = recipient_name
                missing.append("to_email")
        elif not slots.get("to_email"):
            missing.append("to_email")

        if not slots.get("body"):
            missing.append("body")
        if not slots.get("subject"):
            if slots.get("body"):
                slots["subject"] = str(slots["body"])[:24]
            else:
                missing.append("subject")

        if not missing:
            clean_slots = {
                "to_email": str(slots["to_email"]).strip(),
                "subject": str(slots["subject"]).strip(),
                "body": str(slots["body"]).strip(),
            }
            return SlotExtractionResult(
                tool_name=tool_name,
                slots=clean_slots,
                missing_slots=[],
                clarification_question="",
                extraction_method=extraction_method,
                resolved_from_hr=resolved_from_hr,
                hr_candidates=hr_candidates,
                merged_from_history=merged_from_history,
            )

        # Build concise clarification tailored to HR ambiguity / not-found / missing body
        lines: List[str] = []
        if hr_candidates and len(hr_candidates) > 1 and "to_email" in missing:
            header = f"企业通讯录中存在多位名为「{recipient_name}」的同事，为避免误发，请确认具体收件人或直接提供邮箱地址："
            for idx, emp in enumerate(hr_candidates[:5], 1):
                lines.append(
                    f"- 候选 {idx}：{emp.get('name', recipient_name)}（{emp.get('department', '未知部门')} / {emp.get('title', '员工')}，邮箱：{emp.get('email', '未登记')}）"
                )
        elif hr_not_found_name and "to_email" in missing:
            header = f"未在企业通讯录中查询到名为「{hr_not_found_name}」的员工，为确保邮件准确发送，请补充以下信息："
            lines.append("- **收件人邮箱**：请提供对方的完整企业邮箱地址或核对姓名")
        else:
            header = "为确保邮件准确发送，请补充以下信息："
            if "to_email" in missing:
                lines.append("- **收件人**：请提供收件人邮箱地址或企业内部员工姓名")

        if "body" in missing or "subject" in missing:
            lines.append("- **邮件主题与正文**：请说明本次邮件的主题及需要传达的具体内容")

        known_bits = []
        if slots.get("to_email"):
            who = f"{recipient_name} ({slots['to_email']})" if recipient_name and resolved_from_hr else str(slots["to_email"])
            known_bits.append(f"收件人：{who}")
        if slots.get("subject"):
            known_bits.append(f"主题：{slots['subject']}")
        known_line = f"\n\n当前已识别信息：{'，'.join(known_bits)}。" if known_bits else ""
        clarification = f"{header}{known_line}\n\n" + "\n".join(lines) + "\n\n补充后我将立即为您发送。"

    elif tool_name == "create_ticket":
        title = str(slots.get("title") or "").strip()
        desc = str(slots.get("description") or "").strip()
        if not title:
            missing.append("title")
        if not desc:
            missing.append("description")

        if not missing:
            clean_slots = {
                "title": title,
                "description": desc,
                "priority": str(slots.get("priority") or "P3").upper(),
                "department": str(slots.get("department") or "IT").upper(),
            }
            return SlotExtractionResult(
                tool_name=tool_name,
                slots=clean_slots,
                missing_slots=[],
                clarification_question="",
                extraction_method=extraction_method,
                merged_from_history=merged_from_history,
            )

        clarification = (
            "为确保工单准确派发与处理，请补充以下信息：\n\n"
            "- **问题主题与详细描述**：请简要说明具体故障现象、涉及系统或需求内容\n"
            "- **紧急程度**（可选，如 P1 紧急 / P2 重要 / P3 一般，未说明时将按内容自动判定）\n\n"
            "回复后我将立即为您创建工单并返回 SLA 承诺。"
        )

    elif tool_name == "query_employee":
        name = str(slots.get("name") or "").strip()
        if not _is_valid_person_candidate(name):
            slots.pop("name", None)
            missing.append("name")

        if not missing:
            clean_slots = {"name": name}
            if slots.get("department"):
                clean_slots["department"] = str(slots["department"]).strip()
            return SlotExtractionResult(
                tool_name=tool_name,
                slots=clean_slots,
                missing_slots=[],
                clarification_question="",
                extraction_method=extraction_method,
                merged_from_history=merged_from_history,
            )

        clarification = (
            "为准确查询员工档案信息，请补充以下信息：\n\n"
            "- **员工姓名或工号**：请提供待查询同事的姓名或工号（例如 EMP-1001）\n"
            "- **所属部门**（可选，用于同名员工快速筛选）"
        )

    elif tool_name == "query_inventory":
        item_name = str(slots.get("item_name") or "").strip()
        if not _is_valid_item_candidate(item_name):
            slots.pop("item_name", None)
            missing.append("item_name")

        if not missing:
            clean_slots = {"item_name": item_name}
            if slots.get("category"):
                clean_slots["category"] = str(slots["category"]).strip()
            return SlotExtractionResult(
                tool_name=tool_name,
                slots=clean_slots,
                missing_slots=[],
                clarification_question="",
                extraction_method=extraction_method,
                merged_from_history=merged_from_history,
            )

        clarification = (
            "为准确查询设备与物料库存，请补充以下信息：\n\n"
            "- **设备或物料名称**：请说明需要查询的具体型号或品类（例如 MacBook Pro、显示器、办公椅或无线鼠标）"
        )

    elif tool_name == "search_knowledge_base":
        kb_query = str(slots.get("query") or "").strip()
        if len(kb_query) < 2:
            missing.append("query")

        if not missing:
            clean_slots = {"query": kb_query}
            if slots.get("category"):
                clean_slots["category"] = str(slots["category"]).strip().upper()
            return SlotExtractionResult(
                tool_name=tool_name,
                slots=clean_slots,
                missing_slots=[],
                clarification_question="",
                extraction_method=extraction_method,
                merged_from_history=merged_from_history,
            )

        clarification = (
            "为准确检索企业规章制度，请补充以下信息：\n\n"
            "- **检索主题或关键词**：请说明您希望查询的具体制度名称或业务问题（例如差旅报销标准、备用机借用期限、年假规定等）"
        )

    # Strip private helper keys from persisted pending slots while keeping recipient hints if helpful
    public_slots = {k: v for k, v in slots.items() if not k.startswith("_") and v is not None}
    if slots.get("_recipient_name") and tool_name == "send_email":
        public_slots["_recipient_name"] = slots["_recipient_name"]
    if slots.get("_recipient_department") and tool_name == "send_email":
        public_slots["_recipient_department"] = slots["_recipient_department"]

    return SlotExtractionResult(
        tool_name=tool_name,
        slots=public_slots,
        missing_slots=missing,
        clarification_question=clarification,
        extraction_method=extraction_method,
        resolved_from_hr=resolved_from_hr,
        hr_candidates=hr_candidates,
        merged_from_history=merged_from_history,
    )


# ---------------------------------------------------------------------------
# 6. Public Hybrid Extraction Entrypoint
# ---------------------------------------------------------------------------


async def extract_slots_for_tool(
    tool_name: str,
    query: str,
    messages: Sequence[BaseMessage],
    metadata: Optional[Dict[str, Any]] = None,
) -> SlotExtractionResult:
    """Extracts and validates semantic slots for a business tool or approval node.

    Pipeline:
      1. Gather multi-turn clarification context (prior user turns + pending slots if active).
      2. Run fast 0ms deterministic multi-turn slot extraction.
      3. Validate & resolve HR directory lookup (Strategy 5.1 Option A) while enforcing
         strict no-catalog-price policy (Strategy 5.2 Option A).
      4. If any required slot is still missing and SLOT_EXTRACTOR_LLM_ENABLED is True,
         invoke lightweight non-thinking LLM JSON extractor with strict timeout,
         callback isolation, and anti-hallucination post-validation, then re-validate.
    """
    meta = dict(metadata or {})
    clarification_ctx = detect_pending_clarification_context(messages, meta, current_query=query)
    prior_turns: List[str] = []
    pending_slots: Dict[str, Any] = {}
    merged_from_history = False

    if clarification_ctx:
        ctx_tool = clarification_ctx["pending_tool"]
        if ctx_tool == tool_name or {ctx_tool, tool_name} == {"create_purchase", "approval"}:
            prior_turns = list(clarification_ctx.get("prior_user_turns") or [])
            pending_slots = dict(clarification_ctx.get("pending_slots") or {})
            merged_from_history = bool(prior_turns or pending_slots)

    turns: List[str] = [t for t in prior_turns if t and t.strip()]
    if query and query.strip() and (not turns or turns[-1] != query.strip()):
        turns.append(query.strip())
    if not turns:
        turns = [query]

    # Step 1: Deterministic extraction
    if tool_name in ("create_purchase", "approval"):
        det_slots = _extract_purchase_slots_deterministic(turns, meta)
    elif tool_name == "create_ticket":
        det_slots = _extract_ticket_slots_deterministic(turns)
    elif tool_name == "send_email":
        det_slots = _extract_email_slots_deterministic(turns, is_followup=merged_from_history)
    elif tool_name == "query_employee":
        det_slots = _extract_employee_slots_deterministic(turns, is_followup=merged_from_history)
    elif tool_name == "query_inventory":
        det_slots = _extract_inventory_slots_deterministic(turns, is_followup=merged_from_history)
    elif tool_name == "search_knowledge_base":
        det_slots = _extract_kb_slots_deterministic(turns)
    else:
        det_slots = {}

    # Backfill from pending_slots if deterministic pass didn't re-capture a prior slot
    for k, v in pending_slots.items():
        if k not in det_slots and v is not None:
            det_slots[k] = v

    det_result = _validate_and_build_clarification(
        tool_name=tool_name,
        raw_slots=det_slots,
        metadata=meta,
        extraction_method="deterministic",
        merged_from_history=merged_from_history,
    )

    final_result = det_result
    # Step 2: Lightweight non-thinking LLM fallback when required slots are missing
    if not det_result.is_complete and getattr(settings, "SLOT_EXTRACTOR_LLM_ENABLED", True):
        timeout_sec = max(0.05, float(getattr(settings, "SLOT_EXTRACTOR_LLM_TIMEOUT", 2.5)))
        prompt_messages = _build_llm_slot_messages(tool_name, turns)
        raw_llm = await _invoke_slot_extractor_llm(prompt_messages, timeout_sec=timeout_sec)
        if raw_llm:
            parsed_llm = _parse_llm_slot_json(raw_llm)
            if parsed_llm:
                merged_slots = _merge_llm_slots_safely(tool_name, det_slots, parsed_llm, turns)
                final_result = _validate_and_build_clarification(
                    tool_name=tool_name,
                    raw_slots=merged_slots,
                    metadata=meta,
                    extraction_method="hybrid_llm",
                    merged_from_history=merged_from_history,
                )

    try:
        record_slot_extraction_event(
            is_complete=final_result.is_complete,
            extraction_method=final_result.extraction_method,
            merged_from_history=final_result.merged_from_history,
        )
    except Exception as exc:
        logger.debug("[SlotExtractor] Cognitive telemetry hook skipped: %s", exc)
    return final_result
