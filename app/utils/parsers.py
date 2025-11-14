"""Utilitários para parsing e extração de dados."""

from collections import defaultdict
from typing import Any, Dict, List, Optional


def _consolidate_temp_messages(messages: List[dict]) -> Optional[Dict[str, str]]:
    """Consolida múltiplas mensagens temporárias em uma."""
    if not messages:
        return None

    ordered = sorted(messages, key=lambda m: m.get("created_at", ""))
    texts = [msg.get("content", "") for msg in ordered if msg.get("content")]
    if not texts:
        return None

    created_at = ordered[0].get("created_at")
    role = ordered[0].get("role", "user")
    return {
        "role": role,
        "content": " ".join(texts).strip(),
        "created_at": created_at,
    }


def _latest_user_content(history: List[Dict[str, Any]]) -> Optional[str]:
    """Retorna o último conteúdo do usuário no histórico."""
    for message in reversed(history):
        if message.get("role") == "user" and message.get("content"):
            return str(message["content"])
    return None


def _extract_search_terms(text: Optional[str]) -> List[str]:
    """Extrai termos de busca do texto (função mantida para compatibilidade)."""
    if not text:
        return []

    normalized = text.strip().lower()
    if not normalized:
        return []

    sanitized_text = "".join(ch if ch.isalnum() or ch in {" ", "-", "_"} else " " for ch in normalized)
    words = [word for word in sanitized_text.split() if len(word) > 2]
    if not words:
        return []

    terms: List[str] = []
    seen = set()

    phrase = " ".join(words)
    if phrase and phrase not in seen:
        terms.append(phrase)
        seen.add(phrase)

    for word in words:
        if word not in seen:
            terms.append(word)
            seen.add(word)
    return terms[:10]


__all__ = [
    "_consolidate_temp_messages",
    "_latest_user_content",
    "_extract_search_terms",
]
