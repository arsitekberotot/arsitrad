from __future__ import annotations

"""Conversation contextualization for follow-up regulatory questions."""

from typing import Iterable, Mapping

FOLLOWUP_PREFIXES = (
    "bagaimana kalau",
    "kalau",
    "bagaimana",
    "lalu",
    "terus",
    "untuk yang",
)
STANDALONE_PREFIXES = (
    "apa itu",
    "apa beda",
    "berapa",
    "siapa",
    "kapan",
    "di mana",
    "mengapa",
    "kenapa",
)
DEICTIC_TERMS = ("itu", "tersebut", "di sana", "yang tadi", "yang sama")


def _last_user_message(history: Iterable[Mapping[str, str]]) -> str | None:
    for item in reversed(list(history)):
        if item.get("role") == "user" and item.get("content"):
            return item["content"].strip()
    return None


def needs_contextualization(question: str) -> bool:
    lowered = question.strip().lower()
    if any(lowered.startswith(prefix) for prefix in STANDALONE_PREFIXES):
        return False
    if any(lowered.startswith(prefix) for prefix in FOLLOWUP_PREFIXES):
        return True
    if any(term in lowered for term in DEICTIC_TERMS):
        return True
    return len(lowered.split()) <= 3 and lowered.startswith(("yang", "dan", "atau"))


def contextualize_question(question: str, history: Iterable[Mapping[str, str]] | None = None) -> str:
    if not history:
        return question.strip()

    previous_user = _last_user_message(history)
    if not previous_user or not needs_contextualization(question):
        return question.strip()

    base = previous_user.strip().rstrip("? .")
    followup = question.strip()
    lowered = followup.lower()

    if lowered.startswith("bagaimana kalau"):
        suffix = followup[len("Bagaimana") :] if followup.startswith("Bagaimana") else followup[len("bagaimana") :]
        return f"{base} {suffix.strip()}".strip()
    if lowered.startswith("kalau"):
        return f"{base} {followup}".strip()
    if lowered.startswith("bagaimana"):
        return f"{base}; {followup}".strip()
    if any(term in lowered for term in DEICTIC_TERMS):
        return f"{followup} dalam konteks: {base}".strip()
    return f"{base}; {followup}".strip()
