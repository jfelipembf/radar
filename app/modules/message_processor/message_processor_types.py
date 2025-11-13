"""
Tipos e constantes específicos do módulo Message Processor
"""

# Status de processamento de mensagens
PROCESSING_STATUS = {
    'success': 'success',
    'error': 'error',
    'first_message': 'first_message',
    'debounced': 'debounced'
}

# Tipos de processamento
PROCESSING_TYPES = {
    'async': 'async',
    'with_context': 'with_context',
    'immediate': 'immediate'
}

# Configurações de debounce
DEBOUNCE_CONFIG = {
    'default_delay': 5,  # segundos
    'max_delay': 30      # segundos
}

# Limites de contexto
CONTEXT_LIMITS = {
    'max_messages': 10,
    'ai_context_limit': 8
}
