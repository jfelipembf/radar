"""
Funções específicas do módulo WhatsApp (Edge Functions equivalentes)
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

# Configurações da Evolution API
EVOLUTION_URL = os.getenv('EVOLUTION_API_URL')
EVOLUTION_KEY = os.getenv('EVOLUTION_API_KEY')
EVOLUTION_INSTANCE = os.getenv('EVOLUTION_INSTANCE')

async def send_whatsapp_message(number: str, text: str) -> dict:
    """
    Envia mensagem via WhatsApp usando Evolution API

    Args:
        number: Número do telefone
        text: Texto da mensagem

    Returns:
        dict: Resultado do envio
    """
    try:
        url = f"{EVOLUTION_URL}message/sendText/{EVOLUTION_INSTANCE}"
        headers = {
            'Content-Type': 'application/json',
            'apikey': EVOLUTION_KEY
        }
        data = {
            "number": number,
            "text": text
        }

        logger.info(f"Sending message to {number}: {text}")
        response = requests.post(url, headers=headers, json=data)

        logger.info(f"Send response status: {response.status_code}, body: {response.text}")

        return {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response': response.text
        }

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return {
            'success': False,
            'error': str(e)
        }
