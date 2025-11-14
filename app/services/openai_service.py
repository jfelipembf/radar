"""OpenAI service wrapper."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

try:
    from app.prompt_template import PROMPT_SHOPPING_ASSISTANT
except Exception:  # noqa: BLE001
    PROMPT_SHOPPING_ASSISTANT = "Você é um assistente virtual útil e cordial."


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
            PROMPT_SHOPPING_ASSISTANT,
        )

    async def generate_response(
        self,
        message: Optional[str] = None,
        history: Optional[List[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate a response using single message or full history."""
        prompt = system_prompt or self._system_prompt

        if history:
            messages = [{"role": "system", "content": prompt}] + history
        elif message:
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": message},
            ]
        else:
            raise ValueError("É necessário fornecer message ou history")

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
    
    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
    ) -> Any:
        """Generate response with function calling support (MCP).
        
        Args:
            messages: Lista de mensagens da conversa
            tools: Lista de ferramentas (tools) disponíveis para a IA
            tool_choice: "auto", "none", ou {"type": "function", "function": {"name": "..."}}
            
        Returns:
            Response object do OpenAI com possíveis tool_calls
        """
        try:
            kwargs = {
                "model": self._model,
                "messages": messages,
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice
            
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                **kwargs
            )
            
            logger.debug("OpenAI response with tools: %s", response.choices[0].message)
            return response
            
        except Exception as exc:
            logger.exception("Erro ao gerar resposta com tools: %s", exc)
            raise


__all__ = ["OpenAIService"]
