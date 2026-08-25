"""Script to extract and synthesize standard DPO (Direct Preference Optimization) dataset from Feedback records."""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from backend.db.session import SessionLocal
from backend.models.feedback import FeedbackRecord

logger = logging.getLogger("dpo_extractor")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")

# Simple regex patterns for sensitive information redaction (PII/Secret filtering)
# Match ID cards first before 11-digit phone numbers
ID_CARD_REGEX = re.compile(r'\b\d{17}[\dXx]\b|\d{17}[\dXx]')
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)')


def redact_sensitive_info(text: Optional[str]) -> str:
    """Masks ID numbers, emails, and phone numbers in text."""
    if not text:
        return ""
    masked = ID_CARD_REGEX.sub("[ID_CARD_REDACTED]", text)
    masked = EMAIL_REGEX.sub("[EMAIL_REDACTED]", masked)
    masked = PHONE_REGEX.sub("[PHONE_REDACTED]", masked)
    return masked


def extract_dpo_pairs_from_records(records: List[FeedbackRecord]) -> List[Dict[str, Any]]:
    """
    Transforms feedback records into DPO dataset pairs:
    - prompt: user query extracted from context_snapshot
    - chosen: user_correction (if dislike with correction) or liked output
    - rejected: original flawed output or default negative
    """
    dpo_samples = []

    for r in records:
        snapshot = r.context_snapshot or {}
        prompt = snapshot.get("prompt") or snapshot.get("user_query") or f"Query for thread {r.thread_id}"
        llm_output = snapshot.get("llm_output") or snapshot.get("response") or ""

        # Case A: User gave thumbs-down (-1) and provided a correction (chosen)
        if r.score == -1 and r.user_correction:
            chosen = r.user_correction
            rejected = llm_output or "Inaccurate or flawed assistant response."
            dpo_samples.append({
                "prompt": redact_sensitive_info(prompt),
                "chosen": redact_sensitive_info(chosen),
                "rejected": redact_sensitive_info(rejected),
                "metadata": {
                    "thread_id": r.thread_id,
                    "message_id": r.message_id,
                    "source": "dislike_with_correction"
                }
            })

        # Case B: User gave thumbs-up (1) -> original output is chosen
        elif r.score == 1 and llm_output:
            chosen = llm_output
            rejected = snapshot.get("alternative_output") or "Incomplete or low-quality alternative response."
            dpo_samples.append({
                "prompt": redact_sensitive_info(prompt),
                "chosen": redact_sensitive_info(chosen),
                "rejected": redact_sensitive_info(rejected),
                "metadata": {
                    "thread_id": r.thread_id,
                    "message_id": r.message_id,
                    "source": "thumbs_up_positive"
                }
            })

    return dpo_samples


def export_dpo_dataset(output_path: str = "dpo_dataset.jsonl") -> int:
    """Exports DPO pairs from database into JSONL file."""
    with SessionLocal() as db:
        records = db.execute(select(FeedbackRecord)).scalars().all()

    samples = extract_dpo_pairs_from_records(records)
    with open(output_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    logger.info(f"Successfully exported {len(samples)} DPO pairs to {output_path}")
    return len(samples)


if __name__ == "__main__":
    export_dpo_dataset("dpo_dataset.jsonl")
