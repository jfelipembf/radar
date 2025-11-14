"""Utilitários para formatação de dados."""

from datetime import datetime, timezone
from typing import Any, Optional

LOCAL_TIMEZONE = None  # Será definido no módulo principal

def _coerce_price(value: Any) -> float:
    """Converte valor para float, tratando strings monetárias."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            cleaned = value.replace("R$", "").strip()
            cleaned = cleaned.replace(".", "").replace(",", ".")
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _format_currency(value: float) -> str:
    """Formata valor monetário em reais."""
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_date(dt: Optional[datetime]) -> str:
    """Formata data para exibição."""
    if not dt:
        return "-"
    if LOCAL_TIMEZONE:
        return dt.astimezone(LOCAL_TIMEZONE).strftime("%d/%m/%Y")
    return dt.strftime("%d/%m/%Y")


def _format_phone(phone: Optional[str]) -> str:
    """Formata número de telefone."""
    if not phone:
        return ""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if not digits:
        return ""
    if not digits.startswith("55"):
        digits = f"55{digits}"
    return digits


def _parse_created_at(value: Optional[str]) -> Optional[datetime]:
    """Converte string de data para objeto datetime."""
    if not value or not isinstance(value, str):
        return None

    normalized = value
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
    "_coerce_price",
    "_format_currency",
    "_format_date",
    "_format_phone",
    "_parse_created_at",
    "_extract_created_at",
    "_sort_key",
]
