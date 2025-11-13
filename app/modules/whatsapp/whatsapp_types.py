"""
Tipos e constantes específicos do módulo WhatsApp
"""

# Status de resposta do webhook
WEBHOOK_STATUS = {
    'received': 'received',
    'invalid_data': 'invalid_data',
    'ignored': 'ignored',
    'no_text': 'no_text',
    'error': 'error'
}

# Tipos de mensagem WhatsApp
MESSAGE_TYPES = {
    'conversation': 'conversation',
    'extended_text_message': 'extendedTextMessage'
}

# Campos obrigatórios do webhook
WEBHOOK_REQUIRED_FIELDS = {
    'data': 'data',
    'key': 'key',
    'remoteJid': 'remoteJid',
    'fromMe': 'fromMe',
    'message': 'message'
}
