"""
RAG Agent — custom guard functions.

GuardOps calls these when the LLM output hits "RAG_Answer_Node".
The payload includes both the generated answer AND the retrieved chunks,
so guards here can check grounding — not just keywords.

Signature contract:
    check_*(value, rule_config) -> bool       True = breach
    recover_*(value, rule_config) -> str      replacement value
"""

import re
from typing import Any

# Shared state — the decorator passes the full payload dict each turn,
# so guards can read sibling fields (retrieved_chunks, retrieval_score, etc.)
# via rule_config["_payload"].  GuardOps sets this automatically.
_current_payload: dict = {}


def set_payload_context(payload: dict) -> None:
    """Called by the agent before each turn so guards can read the full payload."""
    global _current_payload
    _current_payload = payload


# ─── Guard 1: Hallucination check ────────────────────────────────────────────

def check_hallucination(value: Any, rule_config: dict) -> bool:
    """
    Return True if the answer contains a claim not supported by any
    retrieved chunk.

    Strategy: extract sentences from the answer, then check whether each
    sentence's key noun phrases appear somewhere in the retrieved context.
    Falls back to a simple word-overlap heuristic when spaCy is not installed.

    In production you would use an LLM-as-judge here (GPT-4o-mini asking
    "Is every claim in this answer supported by the context below?").
    We use a word-overlap heuristic so the demo runs without API keys.
    """
    retrieved_chunks: list[str] = _current_payload.get("retrieved_chunks", [])
    if not retrieved_chunks:
        # No context retrieved at all — anything the LLM says is a hallucination
        print("  [check_hallucination] No retrieved chunks — treating as hallucination.")
        return True

    full_context = " ".join(retrieved_chunks).lower()
    answer = str(value).lower()

    # Split answer into sentences and check each for grounding
    sentences = [s.strip() for s in re.split(r"[.!?]", answer) if len(s.strip()) > 20]
    ungrounded = []

    for sentence in sentences:
        # Extract content words (ignore stopwords heuristically)
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "to", "of", "and", "in", "that", "for", "on", "with", "this",
                     "it", "as", "at", "by", "from", "or", "but", "not", "have",
                     "has", "had", "will", "would", "can", "could", "our", "your",
                     "we", "you", "they", "their", "its", "i", "my", "me", "us"}
        content_words = [w for w in re.findall(r"\b[a-z]+\b", sentence)
                         if w not in stopwords and len(w) > 3]
        if not content_words:
            continue

        # A sentence is "grounded" if ≥50% of its content words appear in the context
        hits = sum(1 for w in content_words if w in full_context)
        ratio = hits / len(content_words)
        if ratio < 0.5:
            ungrounded.append((sentence[:60], ratio))

    if ungrounded:
        for excerpt, ratio in ungrounded:
            print(f"  [check_hallucination] Ungrounded sentence (overlap={ratio:.0%}): \"{excerpt}...\"")
        return True

    return False


# ─── Guard 2: PII leak detection ─────────────────────────────────────────────

def check_pii_leak(value: Any, rule_config: dict) -> bool:
    """
    Return True if the answer contains an email address or phone number.

    RAG knowledge bases often embed contact details inside support docs.
    Without this guard, the LLM quotes them verbatim — even when the
    contact is internal-only or the record is out of date.
    """
    text = str(value)

    email_pattern = r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"
    phone_pattern = r"\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)(\d{3}[-.\s]?\d{4})\b"

    if re.search(email_pattern, text):
        print("  [check_pii_leak] Email address found in answer.")
        return True
    if re.search(phone_pattern, text):
        print("  [check_pii_leak] Phone number found in answer.")
        return True
    return False


def recover_redacted_answer(value: Any, rule_config: dict) -> str:
    """Redact PII in-place rather than replacing the whole answer."""
    text = str(value)
    email_pattern = r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"
    phone_pattern = r"\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)(\d{3}[-.\s]?\d{4})\b"
    text = re.sub(email_pattern, "[email redacted]", text)
    text = re.sub(phone_pattern, "[phone redacted]", text)
    return text
