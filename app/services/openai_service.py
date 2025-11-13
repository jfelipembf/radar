"""OpenAI service wrapper."""

import asyncio
import logging
import os
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIService:
    """Handle interactions with OpenAI Chat Completions API."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não configurada")

        self._client = OpenAI(api_key=api_key)
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._system_prompt = os.getenv(
            "OPENAI_SYSTEM_PROMPT",
            "Você é um assistente virtual útil e cordial.",
        )

    async def generate_response(self, message: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response for the given user message."""
        if not message:
            raise ValueError("Mensagem vazia")

        prompt = system_prompt or self._system_prompt
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": message}]

        try:
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self._model,
                messages=messages,
            )
            choice = response.choices[0].message.content.strip()
            logger.debug("OpenAI response generated: %s", choice)
            return choice
        except Exception as exc:  # noqa: BLE001 - queremos logar erros genéricos da API
            logger.exception("Erro ao gerar resposta da OpenAI: %s", exc)
            raise


__all__ = ["OpenAIService"]
