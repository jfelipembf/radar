"""
Regras de negócio e validações do módulo WhatsApp
"""
from .whatsapp_types import WEBHOOK_STATUS

def validate_webhook_data(data: dict) -> dict:
    """
    Valida dados recebidos do webhook do WhatsApp

    Args:
        data: Dados recebidos do webhook

    Returns:
        dict: Status da validação
    """
    if not isinstance(data, dict):
        return {'valid': False, 'status': WEBHOOK_STATUS['invalid_data']}

    if 'data' not in data:
        return {'valid': False, 'status': WEBHOOK_STATUS['invalid_data']}

    return {'valid': True}

def extract_message_data(webhook_data: dict) -> dict:
    """
    Extrai informações da mensagem do webhook

    Args:
        webhook_data: Dados do webhook

    Returns:
        dict: Dados extraídos da mensagem
    """
    message_data = webhook_data['data']
    key = message_data.get('key', {})
    message = message_data.get('message', {})

    # Extrair texto da mensagem
    text = ""
    if 'conversation' in message:
        text = message.get('conversation', '')
    elif 'extendedTextMessage' in message:
        text = message['extendedTextMessage'].get('text', '')

    # Extrair informações do usuário
    remote_jid = key.get('remoteJid')
    from_me = key.get('fromMe', False)
    user_id = remote_jid.split('@')[0] if remote_jid else ""

    return {
        'user_id': user_id,
        'remote_jid': remote_jid,
        'from_me': from_me,
        'text': text,
        'message_data': message_data
    }

def should_process_message(message_info: dict) -> dict:
    """
    Determina se a mensagem deve ser processada

    Args:
        message_info: Informações da mensagem

    Returns:
        dict: Decisão de processamento
    """
    # Ignorar mensagens enviadas pelo próprio bot
    if message_info['from_me']:
        return {'should_process': False, 'status': WEBHOOK_STATUS['ignored']}

    # Ignorar mensagens sem texto
    if not message_info['text'].strip():
        return {'should_process': False, 'status': WEBHOOK_STATUS['no_text']}

    return {'should_process': True}

def format_error_response(error: Exception) -> dict:
    """
    Formata resposta de erro do webhook

    Args:
        error: Exceção ocorrida

    Returns:
        dict: Resposta formatada
    """
    return {
        'status': WEBHOOK_STATUS['error'],
        'message': str(error)
    }
