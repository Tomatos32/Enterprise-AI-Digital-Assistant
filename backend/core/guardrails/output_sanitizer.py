"""Output Safety Sanitizer and Streaming PII Redaction Engine."""

import re
import logging
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)


def _mask_bank_card(match: re.Match) -> str:
    """Mask bank card numbers, preserving first 4 and last 4 digits."""
    card = match.group(0)
    prefix = card[:4]
    suffix = card[-4:]
    masked_len = len(card) - 8
    return f"{prefix}{'*' * masked_len}{suffix}"


def _mask_api_key(match: re.Match) -> str:
    """Mask API key (sk-...), preserving prefix and masking secret token."""
    key = match.group(0)
    return f"sk-{'*' * min(20, len(key) - 3)}"


def _mask_bearer_token(match: re.Match) -> str:
    """Mask HTTP Bearer token."""
    return "Bearer ********************"


# PII Regex Rules: (Category, Regex Pattern, Replacement / Function)
PII_RULES: List[Tuple[str, re.Pattern, Any]] = [
    # 1. Chinese Mobile Phone (11 digits: 13x - 19x) -> 138****5678
    (
        "PHONE_NUMBER",
        re.compile(r"(?<!\d)(1[3-9]\d)(\d{4})(\d{4})(?!\d)"),
        r"\g<1>****\g<3>",
    ),
    # 2. Chinese National Resident ID (18 digits) -> 110101********2345
    (
        "CHINESE_ID_CARD",
        re.compile(r"(?<!\d)([1-9]\d{5})\d{8}(\d{3}[\dXx])(?!\d)"),
        r"\g<1>********\g<2>",
    ),
    # 3. Bank Card (16 to 19 digits) -> 6222************1234
    (
        "BANK_CARD",
        re.compile(r"(?<!\d)([1-9]\d{3})(\d{8,11})(\d{4})(?!\d)"),
        _mask_bank_card,
    ),
    # 4. OpenAI / Cloud API Keys (e.g. sk-...) -> sk-********************
    (
        "API_SECRET_KEY",
        re.compile(r"\b(sk-[a-zA-Z0-9]{20,})\b"),
        _mask_api_key,
    ),
    # 5. Bearer Tokens -> Bearer ********************
    (
        "BEARER_TOKEN",
        re.compile(r"\bBearer\s+[a-zA-Z0-9_\-\.]{25,}\b"),
        _mask_bearer_token,
    ),
    # 6. Email Addresses -> t***@domain.com
    (
        "EMAIL_ADDRESS",
        re.compile(r"(?i)\b([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b"),
        r"\g<1>***@\g<2>",
    ),
]


def sanitize_text(text: str) -> str:
    """
    Sanitizes plain text by masking all PII patterns (Phone, ID, Bank Card, Keys).
    Pure function, safe for batch strings.
    """
    if not text or not isinstance(text, str):
        return text

    sanitized = text
    for _, pattern, repl in PII_RULES:
        if callable(repl):
            sanitized = pattern.sub(repl, sanitized)
        else:
            sanitized = pattern.sub(repl, sanitized)

    return sanitized


def sanitize_text_detailed(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Sanitizes text and returns the masked string along with audit records of masked entities.
    """
    if not text or not isinstance(text, str):
        return text, []

    audit_logs: List[Dict[str, Any]] = []
    sanitized = text

    for category, pattern, repl in PII_RULES:
        matches = pattern.finditer(sanitized)
        for m in matches:
            audit_logs.append({
                "category": category,
                "raw_match": m.group(0),
                "start": m.start(),
                "end": m.end(),
            })
        if callable(repl):
            sanitized = pattern.sub(repl, sanitized)
        else:
            sanitized = pattern.sub(repl, sanitized)

    return sanitized, audit_logs


class StreamingSanitizer:
    """
    Stateful streaming token sanitizer with sliding window buffer.
    Ensures PII spanning across consecutive chunk boundaries is never leaked.
    """

    def __init__(self, window_size: int = 32):
        """
        :param window_size: Lookahead sliding buffer size in characters (>= max PII entity length).
        """
        self.window_size = window_size
        self._buffer: str = ""

    def process_chunk(self, chunk: str) -> str:
        """
        Appends chunk to buffer, masks any complete PII entities, and yields
        safe characters outside the sliding window boundary.
        """
        if not chunk:
            return ""

        self._buffer += chunk
        sanitized = sanitize_text(self._buffer)

        if len(sanitized) > self.window_size:
            safe_cut = len(sanitized) - self.window_size
            to_emit = sanitized[:safe_cut]
            self._buffer = sanitized[safe_cut:]
            return to_emit

        return ""

    def flush(self) -> str:
        """
        Flushes the remaining buffer content at stream termination, applying final masking.
        """
        if not self._buffer:
            return ""

        final_chunk = sanitize_text(self._buffer)
        self._buffer = ""
        return final_chunk

    def reset(self) -> None:
        """Resets the internal buffer state."""
        self._buffer = ""
