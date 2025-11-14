"""Handler para webhooks do WhatsApp."""

import logging
from typing import Dict, Any

from fastapi import Request

from app.services.chatbot_service import ChatbotService

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handler para processar webhooks recebidos."""

    def __init__(self, chatbot_service: ChatbotService):
        self.chatbot_service = chatbot_service

    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        """Processa webhook do WhatsApp."""
        try:
            data = await request.json()

            # Extrair dados da mensagem
            message_data = self._extract_message_data(data)
            if not message_data:
                return {"status": "invalid_data"}

            # Validar se é mensagem do usuário
            user_id, text = self._validate_user_message(message_data)
            if not user_id or not text:
                return {"status": "ignored"}

            # Processar mensagem
            result = await self.chatbot_service.process_message(user_id, text, message_data)

            return {"status": result}

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {"status": "error", "message": str(e)}

    def _extract_message_data(self, data: dict) -> dict:
        """Extrai dados da mensagem do payload."""
        if 'data' not in data:
            return {}
        return data['data']

    def _validate_user_message(self, message_data: dict) -> tuple[str, str]:
        """Valida e extrai informações da mensagem do usuário."""
        key = message_data.get('key', {})

        # Ignorar mensagens enviadas pelo bot
        if key.get('fromMe', False):
            return "", ""

        # Extrair número do usuário
        remote_jid = key.get('remoteJid')
        user_id = remote_jid.split('@')[0] if remote_jid else ""

        # Extrair texto da mensagem
        message = message_data.get('message', {})
        text = ""
        if 'conversation' in message:
            text = message.get('conversation', '')
        elif 'extendedTextMessage' in message:
            text = message['extendedTextMessage'].get('text', '')

        return user_id, text.strip()


__all__ = ["WebhookHandler"]
