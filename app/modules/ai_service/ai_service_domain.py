"""
Regras de negócio e validações do módulo AI Service
"""
import re
from .ai_service_types import PRODUCT_KEYWORDS, PRODUCT_MAPPINGS

def detect_product_query(message: str) -> str:
    """
    Detecta se a mensagem é uma consulta de produto

    Args:
        message: Mensagem do usuário

    Returns:
        str: Nome do produto detectado ou None
    """
    message_lower = message.lower()

    # Verificar se contém palavras-chave
    for keyword in PRODUCT_KEYWORDS:
        if keyword in message_lower:
            # Extrair possível nome do produto
            return extract_product_name(message)

    return None

def extract_product_name(message: str) -> str:
    """
    Extrai o nome do produto da mensagem

    Args:
        message: Mensagem do usuário

    Returns:
        str: Nome do produto
    """
    message_lower = message.lower()

    for term, product in PRODUCT_MAPPINGS.items():
        if term in message_lower:
            return product

    # Retornar a própria mensagem se não encontrar mapeamento específico
    return message.strip()

def validate_ai_response(response: str) -> dict:
    """
    Valida resposta da IA

    Args:
        response: Resposta da IA

    Returns:
        dict: Resultado da validação
    """
    if not response or not response.strip():
        return {'valid': False, 'error': 'empty_response'}

    if len(response.strip()) < 10:
        return {'valid': False, 'error': 'response_too_short'}

    # Verificar se não contém erros óbvios
    error_indicators = ['error', 'exception', 'failed', 'unable']
    response_lower = response.lower()

    for indicator in error_indicators:
        if indicator in response_lower and 'desculpe' not in response_lower:
            return {'valid': False, 'error': 'possible_error_response'}

    return {'valid': True}

def prepare_messages_for_ai(system_prompt: str, context_messages: list = None, user_message: str = None) -> list:
    """
    Prepara mensagens para envio à IA

    Args:
        system_prompt: Prompt do sistema
        context_messages: Mensagens de contexto (opcional)
        user_message: Mensagem do usuário (opcional)

    Returns:
        list: Mensagens formatadas para OpenAI
    """
    messages = [{"role": "system", "content": system_prompt}]

    # Adicionar contexto se fornecido
    if context_messages:
        for ctx_msg in context_messages[-8:]:  # Últimas 8 mensagens
            messages.append({
                "role": ctx_msg.role,
                "content": ctx_msg.content
            })

    # Adicionar mensagem do usuário se fornecida
    if user_message:
        messages.append({"role": "user", "content": user_message})

    return messages

def extract_latest_user_message(context_messages: list, fallback_message: str = None) -> str:
    """
    Extrai a última mensagem do usuário do contexto

    Args:
        context_messages: Mensagens do contexto
        fallback_message: Mensagem de fallback

    Returns:
        str: Última mensagem do usuário
    """
    if not context_messages:
        return fallback_message

    user_messages = [msg for msg in context_messages if msg.role == 'user']
    if user_messages:
        return user_messages[-1].content

    return fallback_message

def should_use_context(context_messages: list) -> bool:
    """
    Determina se deve usar contexto na resposta

    Args:
        context_messages: Mensagens do contexto

    Returns:
        bool: Se deve usar contexto
    """
    if not context_messages:
        return False

    # Usar contexto se houver pelo menos 2 mensagens
    return len(context_messages) >= 2
