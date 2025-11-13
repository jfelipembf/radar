"""
Módulo AI Service - Integração com OpenAI
"""

from .ai_service_functions import generate_ai_response, generate_ai_response_with_context, format_product_response
from .ai_service_domain import detect_product_query, extract_product_name, validate_ai_response
from .ai_service_types import AI_MODELS, AI_CONFIG, AI_STATUS, PRODUCT_KEYWORDS, PRODUCT_MAPPINGS

__all__ = [
    'generate_ai_response',
    'generate_ai_response_with_context',
    'format_product_response',
    'detect_product_query',
    'extract_product_name',
    'validate_ai_response',
    'AI_MODELS',
    'AI_CONFIG',
    'AI_STATUS',
    'PRODUCT_KEYWORDS',
    'PRODUCT_MAPPINGS'
]
