"""Utilitários para parsing e extração de dados."""

from datetime import datetime, timezone
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


def _extract_created_at(message_data: dict) -> str:
    """Extrai timestamp da mensagem."""
    timestamp = message_data.get('messageTimestamp') or message_data.get('messageTimestamp')
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc).isoformat()


def _sort_key(message: dict) -> str:
    """Chave de ordenação para mensagens."""
    created_at = message.get("created_at")
    if isinstance(created_at, str):
        return created_at
    return ""


__all__ = [
    "_consolidate_temp_messages",
    "_latest_user_content",
    "_extract_created_at",
    "_sort_key",
]
