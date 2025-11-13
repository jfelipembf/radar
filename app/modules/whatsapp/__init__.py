"""
Módulo WhatsApp - Integração com Evolution API
"""

from .whatsapp_functions import send_whatsapp_message
from .whatsapp_domain import validate_webhook_data, extract_message_data, should_process_message, format_error_response
from .whatsapp_types import WEBHOOK_STATUS, MESSAGE_TYPES, WEBHOOK_REQUIRED_FIELDS

__all__ = [
    'send_whatsapp_message',
    'validate_webhook_data',
    'extract_message_data',
    'should_process_message',
    'format_error_response',
    'WEBHOOK_STATUS',
    'MESSAGE_TYPES',
    'WEBHOOK_REQUIRED_FIELDS'
]
