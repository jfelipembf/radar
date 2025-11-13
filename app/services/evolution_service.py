"""Evolution WhatsApp service."""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class EvolutionService:
    """Send messages using the Evolution API."""

    def __init__(self) -> None:
        self._base_url = os.getenv("EVOLUTION_API_URL")
        self._api_key = os.getenv("EVOLUTION_API_KEY")
        self._instance = os.getenv("EVOLUTION_INSTANCE")

        if not all([self._base_url, self._api_key, self._instance]):
            raise ValueError("Variáveis da Evolution ausentes (EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE)")

    def send_message(self, number: str, text: str) -> Optional[requests.Response]:
        if not number or not text:
            raise ValueError("Número e texto são obrigatórios")

        url = f"{self._base_url.rstrip('/')}/message/sendText/{self._instance}"
        headers = {
            "Content-Type": "application/json",
            "apikey": self._api_key,
        }
        payload = {"number": number, "text": text}

        logger.info("Evolution → enviando mensagem para %s", number)
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            logger.info(
                "Evolution → status=%s body=%s",
                response.status_code,
                response.text[:200],
            )
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao enviar mensagem para Evolution: %s", exc)
            raise

    def send_presence(self, number: str, presence: str, delay_ms: Optional[int] = None) -> Optional[requests.Response]:
        if not number or not presence:
            raise ValueError("Número e presença são obrigatórios")

        url = f"{self._base_url.rstrip('/')}/chat/sendPresence/{self._instance}"
        headers = {
            "Content-Type": "application/json",
            "apikey": self._api_key,
        }
        payload = {
            "number": number,
            "presence": presence,
        }
        if delay_ms is not None:
            payload["delay"] = delay_ms

        logger.info("Evolution → ajustando presença de %s para %s", number, presence)
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            logger.info(
                "Evolution presença → status=%s body=%s",
                response.status_code,
                response.text[:200],
            )
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro ao ajustar presença na Evolution: %s", exc)
            raise


__all__ = ["EvolutionService"]
