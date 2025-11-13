"""
Regras de negócio e validações do módulo Message Processor
"""
import asyncio
from .message_processor_types import PROCESSING_STATUS, DEBOUNCE_CONFIG, CONTEXT_LIMITS

def determine_processing_strategy(is_first_today: bool, has_context: bool = True) -> str:
    """
    Determina a estratégia de processamento baseada no contexto

    Args:
        is_first_today: Se é a primeira mensagem do dia
        has_context: Se há contexto de conversa disponível

    Returns:
        str: Estratégia de processamento
    """
    if is_first_today:
        return 'immediate'  # Processar imediatamente com boas-vindas

    if has_context:
        return 'debounced'  # Usar debounce para contexto

    return 'fallback'  # Fallback sem contexto

def should_apply_debounce(user_id: str, debounce_timers: dict) -> bool:
    """
    Verifica se deve aplicar debounce para o usuário

    Args:
        user_id: ID do usuário
        debounce_timers: Timers ativos

    Returns:
        bool: Se deve aplicar debounce
    """
    return user_id not in debounce_timers

def calculate_debounce_delay(message_count: int) -> int:
    """
    Calcula o delay do debounce baseado na quantidade de mensagens

    Args:
        message_count: Número de mensagens no contexto

    Returns:
        int: Delay em segundos
    """
    base_delay = DEBOUNCE_CONFIG['default_delay']
    max_delay = DEBOUNCE_CONFIG['max_delay']

    # Aumentar delay com mais mensagens (até o máximo)
    delay = min(base_delay + (message_count * 2), max_delay)

    return delay

def validate_message_context(context_messages: list) -> dict:
    """
    Valida o contexto de mensagens

    Args:
        context_messages: Lista de mensagens do contexto

    Returns:
        dict: Resultado da validação
    """
    if not context_messages:
        return {'valid': False, 'error': 'no_context'}

    user_messages = [msg for msg in context_messages if msg.role == 'user']
    if not user_messages:
        return {'valid': False, 'error': 'no_user_messages'}

    # Verificar se há mensagens não processadas
    latest_user_message = user_messages[-1]
    assistant_messages = [msg for msg in context_messages if msg.role == 'assistant']

    # Se a última mensagem do usuário foi após a última resposta do assistente
    if not assistant_messages or latest_user_message.timestamp > assistant_messages[-1].timestamp:
        return {'valid': True, 'needs_processing': True, 'latest_message': latest_user_message}

    return {'valid': True, 'needs_processing': False}

def prepare_ai_context(context_messages: list, current_message: str = None) -> list:
    """
    Prepara o contexto para envio à IA

    Args:
        context_messages: Mensagens do contexto
        current_message: Mensagem atual (opcional)

    Returns:
        list: Mensagens formatadas para IA
    """
    # Limitar número de mensagens para não exceder limite
    recent_messages = context_messages[-CONTEXT_LIMITS['ai_context_limit']:]

    # Formatar para API da OpenAI
    ai_messages = []
    for msg in recent_messages:
        ai_messages.append({
            'role': msg.role,
            'content': msg.content
        })

    # Adicionar mensagem atual se não estiver no contexto
    if current_message and not any(msg['content'] == current_message for msg in ai_messages):
        ai_messages.append({'role': 'user', 'content': current_message})

    return ai_messages

async def execute_with_timeout(coro, timeout: int = 30):
    """
    Executa uma coroutine com timeout

    Args:
        coro: Coroutine a executar
        timeout: Timeout em segundos

    Returns:
        Resultado da coroutine ou None se timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return None
