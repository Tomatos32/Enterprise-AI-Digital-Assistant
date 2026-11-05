"""Query Rewriting, Sub-Query Decomposition, and Coreference Resolution Engine.

Implements the 3-tier enterprise retrieval preprocessing architecture:
1. Context Completion & Coreference Resolution (多轮对话上下文补全与代词指代消解)
2. Sub-Query Decomposition & Intent Disambiguation (多意图子查询拆分与关键词提炼)
3. Step-Back Domain & Entity Abstraction (抽象回退与业务领域锚定)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


@dataclass
class RewrittenQuery:
    """Structured container holding decomposed sub-queries and metadata."""

    original_query: str
    standalone_query: str
    sub_queries: List[str] = field(default_factory=list)
    primary_domain: Optional[str] = None
    extracted_entities: List[str] = field(default_factory=list)


# Domain taxonomy for enterprise rules
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "IT": [
        "备用机", "借用", "借机", "归还", "外借", "电脑", "笔记本", "macbook", "thinkpad",
        "显示器", "外设", "资产", "硬件", "配置", "vpn", "ztna", "密码", "mfa", "权限",
        "开源协议", "密钥", "服务器", "集群", "故障", "sla", "p0", "p1", "p2", "p3", "p4",
    ],
    "PROCUREMENT": [
        "采购", "供应商", "询价", "招标", "验收", "领用", "固定资产", "大额采购", "审批矩阵",
    ],
    "HR": [
        "人事", "考勤", "打卡", "请假", "年假", "事假", "病假", "产假", "育儿假",
        "迟到", "早退", "旷工", "加班", "社保", "公积金", "薪酬", "工资", "调薪",
        "绩效", "年终奖", "离职", "交接", "试用期", "转正", "福利",
    ],
    "FINANCE": [
        "报销", "差旅标准", "住宿标准", "机票", "高铁", "交通补贴", "餐补", "借款", "发票",
        "税号", "报销限额", "纳税人识别号",
    ],
    "SECURITY": [
        "数据安全", "泄密", "保密", "合规", "机密", "脱敏", "审计", "安全红线", "密级",
    ],
    "CS": [
        "客户服务", "售后", "投诉", "工单分级", "回访", "满意度",
    ],
}

# Pronouns requiring coreference resolution
PRONOUNS = ["它", "这个", "那台", "那个", "此项", "前述", "上述", "这笔费用", "该设备", "他们"]


class QueryRewriter:
    """Enterprise Query Rewriter and Sub-Query Splitter."""

    def __init__(self):
        pass

    def _resolve_coreference(self, query: str, history: Optional[List[BaseMessage]] = None) -> str:
        """Resolves pronouns in multi-turn dialogues using recent context."""
        if not history or not any(p in query for p in PRONOUNS):
            return query

        # Search backward for the most recent noun/entity mentioned
        recent_entity = None
        for msg in reversed(history):
            content = str(getattr(msg, "content", ""))
            # Extract common enterprise entities
            entity_matches = re.findall(
                r"(MacBook|ThinkPad|显示器|笔记本|备用机|工单|采购单|年假|差旅|报销|发票|密码|权限)",
                content,
                re.IGNORECASE,
            )
            if entity_matches:
                recent_entity = entity_matches[0]
                break

        if recent_entity:
            resolved = query
            for p in PRONOUNS:
                if p in resolved:
                    resolved = resolved.replace(p, recent_entity, 1)
            logger.info("[QueryRewriter] Coreference resolved: '%s' -> '%s'", query, resolved)
            return resolved

        return query

    def _detect_primary_domain(self, query: str) -> Optional[str]:
        """Detects the primary business domain to avoid cross-domain noise."""
        q_lower = query.lower()
        domain_scores: Dict[str, int] = {}

        # High-specificity overrides: "借用备用机/电脑" is IT, even if user mentions "出差"
        if any(k in q_lower for k in ["备用机", "借用", "借机", "电脑", "笔记本", "外设"]):
            return "IT"

        for domain, keywords in DOMAIN_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw.lower() in q_lower)
            if count > 0:
                domain_scores[domain] = count

        if domain_scores:
            best_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
            return best_domain

        return None

    def _split_sub_queries(self, query: str, domain: Optional[str]) -> List[str]:
        """Decomposes a composite multi-faceted question into atomic search queries."""
        sub_queries: List[str] = []

        # 1. Clean query of filler pleasantries
        cleaned = re.sub(r"^(请问|你好|您好|我想了解一下|我想问|帮我查一下|查一下)[，, ]*", "", query).strip()

        # 2. Extract core entities
        entities: List[str] = []
        if any(k in cleaned for k in ["备用机", "借机", "借用机", "临时电脑"]):
            entities.append("备用机")
        elif any(k in cleaned for k in ["MacBook", "ThinkPad", "电脑", "笔记本"]):
            entities.append("办公电脑")
        elif "报销" in cleaned or "差旅" in cleaned:
            entities.append("差旅报销")
        elif "年假" in cleaned or "请假" in cleaned:
            entities.append("年假休假")

        core_entity = entities[0] if entities else ""

        # 3. Detect multi-facet question clauses (duration, deposit, penalty, procedure)
        facets = []

        # Facet: Duration (期限/多久)
        if any(k in cleaned for k in ["期限", "多久", "几天", "时间", "借多久"]):
            facets.append("借用期限 最长时间 申请时限")

        # Facet: Deposit (押金/交钱)
        if any(k in cleaned for k in ["押金", "保证金", "交钱", "抵押"]):
            facets.append("押金 费用 保证金")

        # Facet: Overdue & Penalty (超期/扣钱/违约/处罚)
        if any(k in cleaned for k in ["超期", "超借用期限", "逾期", "不还", "违约", "扣钱", "罚款", "失信", "扣减"]):
            facets.append("超期 续借 冻结权限 绩效扣减 管理费")

        # Facet: Return & Wipe (归还/擦除)
        if any(k in cleaned for k in ["归还", "交回", "擦除", "数据安全"]):
            facets.append("归还流程 数据安全擦除")

        # Assemble atomic queries
        if core_entity and facets:
            for facet in facets:
                atomic_q = f"{core_entity} {facet}"
                sub_queries.append(atomic_q)
        else:
            # Fallback: split by punctuation delimiters
            clauses = [c.strip() for c in re.split(r"[，,。；;？?！!]+", cleaned) if len(c.strip()) >= 3]
            if len(clauses) > 1:
                sub_queries.extend(clauses)
            else:
                sub_queries.append(cleaned)

        # Include a domain-anchor step-back query
        if domain == "IT" and core_entity:
            sub_queries.append(f"IT运维与资产借用指南 {core_entity} 临时设备借用SOP")

        return sub_queries if sub_queries else [cleaned]

    def rewrite(
        self,
        query: str,
        history: Optional[List[BaseMessage]] = None,
    ) -> RewrittenQuery:
        """Executes full query rewriting, coreference resolution, and sub-query splitting."""
        # Step 1: Coreference resolution
        standalone_q = self._resolve_coreference(query, history)

        # Step 2: Primary domain detection
        domain = self._detect_primary_domain(standalone_q)

        # Step 3: Sub-query splitting
        sub_queries = self._split_sub_queries(standalone_q, domain)

        # Extract entities
        extracted_entities = re.findall(
            r"(备用机|MacBook|ThinkPad|显示器|笔记本|出差|年假|差旅|报销|发票|密码|权限|工单)",
            standalone_q,
            re.IGNORECASE,
        )

        logger.info(
            "[QueryRewriter] Query: '%s' -> Domain: %s, Sub-queries: %s",
            query,
            domain,
            sub_queries,
        )

        return RewrittenQuery(
            original_query=query,
            standalone_query=standalone_q,
            sub_queries=sub_queries,
            primary_domain=domain,
            extracted_entities=list(set(extracted_entities)),
        )


# Global singleton
_global_query_rewriter: Optional[QueryRewriter] = None


def get_query_rewriter() -> QueryRewriter:
    """Returns singleton instance of QueryRewriter."""
    global _global_query_rewriter
    if _global_query_rewriter is None:
        _global_query_rewriter = QueryRewriter()
    return _global_query_rewriter
