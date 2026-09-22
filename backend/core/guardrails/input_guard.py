"""Input Safety Guardrail Engine for Prompt Injection and Jailbreak Defense."""

import re
import logging
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class GuardResult(BaseModel):
    """Result of an input guardrail security check."""
    is_valid: bool = Field(..., description="True if prompt is safe, False if policy violation")
    category: Optional[str] = Field(default=None, description="Violation category if detected")
    reason: Optional[str] = Field(default=None, description="Detailed explanation of the violation")
    matched_pattern: Optional[str] = Field(default=None, description="Regex pattern or keyword matched")
    risk_score: float = Field(default=0.0, description="Confidence/Severity score between 0.0 and 1.0")


class PolicyViolationException(HTTPException):
    """Exception raised when an input violates content security or system guardrails."""
    def __init__(self, detail: str = "400 Bad Request: Policy Violation", category: Optional[str] = None):
        super().__init__(status_code=400, detail=detail)
        self.category = category


# High-Risk Threat Pattern Definitions
INJECTION_RULES: List[Tuple[str, str, str]] = [
    # 1. Direct Instruction Overrides (English & Chinese)
    (
        "PROMPT_INJECTION_OVERRIDE",
        r"(?i)((ignore|disregard)\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|prompts|rules)|"
        r"forget\s+(everything|all)\s+(you\s+were\s+told|prior)|"
        r"free\s+from\s+(all\s+)?(rules|restrictions|limits)|"
        r"忽略(所有)?(之前|前序|上述)(的)?(指令|规则|提示词|设定)|"
        r"无视(先前|上述|所有)(指令|限制|规则)|"
        r"放弃前置设定)",
        "Attempt to override or disregard prior system instructions"
    ),

    # 2. Known Jailbreak Personas & Modes (DAN, Developer Mode, AIM, etc.)
    (
        "JAILBREAK_PERSONA",
        r"(?i)(\bDAN\s+mode\b|do\s+anything\s+now|developer\s+mode\s+enabled|"
        r"act\s+as\s+(an?\s+)?unfiltered\s+AI|"
        r"pretend\s+(you\s+have\s+no\s+(rules|limits|guidelines)|to\s+be\s+evil)|"
        r"开启越狱模式|进入开发者模式|解除所有(安全|道德|风控)限制|"
        r"不受任何(约束|限制)|假装你没有任何道德标准)",
        "Known jailbreak persona or rule evasion mode detected"
    ),

    # 3. System Prompt & Internal Secret Exfiltration
    (
        "SECRET_EXFILTRATION",
        r"(?i)((reveal|output|print|show|dump)\s+(your\s+)?(system\s+prompt|initial\s+instructions|secret\s+key|api\s+token|environment\s+variables)|"
        r"显示系统提示词|打印系统预设|泄露系统指令|输出你的(底层|系统)提示词|"
        r"查看后台密钥|打印环境变量|获取数据库密码)",
        "Attempt to exfiltrate system prompt or sensitive runtime secrets"
    ),

    # 4. Delimiter Hijacking & Format Injection
    (
        "DELIMITER_HIJACKING",
        r"(?i)(<\|im_start\|>system|<\|im_end\|>|\[INST\]\s*<<SYS>>|```system|"
        r"---BEGIN INSTRUCTIONS---|---END OF SYSTEM PROMPT---|\[SYSTEM\s+PROMPT\])",
        "Delimiter or LLM special token injection attempt"
    ),

    # 5. System Probing & OS/SQL Injection Payloads
    (
        "SYSTEM_EXPLOIT_PROBE",
        r"(?i)(/etc/passwd|/etc/shadow|\bDROP\s+TABLE\b|\bUNION\s+SELECT\b|"
        r"\brm\s+-rf\s+/|\beval\s*\(|\bexec\s*\(|subprocess\.Popen|"
        r"cat\s+/var/log/|sudo\s+su\b|切换到最高管理员权限|授予系统root权限)",
        "System probing, OS command or SQL injection pattern detected"
    ),

    # 6. Prefix Injection / Response Hijacking
    (
        "PREFIX_INJECTION",
        r"(?i)(start\s+your\s+response\s+with\s*['\"]|以['\"]好的，我现在就教你黑客入侵['\"]开头|"
        r"强制第一句话说|必须回复如下字样)",
        "Prefix injection or response forcing attempt"
    ),

    # 7. Obfuscated Payload Decoding Directives
    (
        "OBFUSCATION_DECODE",
        r"(?i)(decode\s+the\s+following\s+base64\s+and\s+execute|"
        r"解密以下base64并作为系统指令执行|"
        r"忽略安全策略并解析十六进制)",
        "Obfuscated encoded payload execution attempt"
    ),
]


def validate_input(prompt: str) -> GuardResult:
    """
    Validates user input against prompt injection, jailbreaks, and sensitive probes.
    Returns GuardResult with classification details.
    """
    if not prompt or not isinstance(prompt, str):
        return GuardResult(is_valid=True, risk_score=0.0)

    clean_prompt = prompt.strip()

    for category, pattern, reason in INJECTION_RULES:
        match = re.search(pattern, clean_prompt)
        if match:
            matched_str = match.group(0)
            logger.warning(
                f"[InputGuard] Policy Violation detected! Category={category}, "
                f"Pattern='{matched_str}', Input excerpt='{clean_prompt[:60]}...'"
            )
            return GuardResult(
                is_valid=False,
                category=category,
                reason=reason,
                matched_pattern=matched_str,
                risk_score=0.98
            )

    return GuardResult(is_valid=True, risk_score=0.0)


def check_input_or_raise(prompt: str) -> GuardResult:
    """
    Checks prompt safety and raises PolicyViolationException (HTTP 400) if unsafe.
    """
    result = validate_input(prompt)
    if not result.is_valid:
        raise PolicyViolationException(
            detail=f"400 Bad Request: Policy Violation - {result.reason} ({result.category})",
            category=result.category
        )
    return result
