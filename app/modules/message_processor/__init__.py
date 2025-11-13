"""
Módulo Message Processor - Processamento de mensagens WhatsApp
"""

from .message_processor_functions import process_message_async, process_message_with_context, get_welcome_message
from .message_processor_domain import determine_processing_strategy, validate_message_context, prepare_ai_context
from .message_processor_types import PROCESSING_STATUS, PROCESSING_TYPES, DEBOUNCE_CONFIG, CONTEXT_LIMITS

__all__ = [
    'process_message_async',
    'process_message_with_context',
    'get_welcome_message',
    'determine_processing_strategy',
    'validate_message_context',
    'prepare_ai_context',
    'PROCESSING_STATUS',
    'PROCESSING_TYPES',
    'DEBOUNCE_CONFIG',
    'CONTEXT_LIMITS'
]
