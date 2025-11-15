"""OpenAI service wrapper."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

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
