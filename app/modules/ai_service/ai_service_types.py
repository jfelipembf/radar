"""
Tipos e constantes específicos do módulo AI Service
"""

# Modelos disponíveis da OpenAI
AI_MODELS = {
    'gpt4o_mini': 'gpt-4o-mini',
    'gpt4o': 'gpt-4o',
    'gpt4': 'gpt-4'
}

# Configurações padrão da IA
AI_CONFIG = {
    'default_model': AI_MODELS['gpt4o_mini'],
    'max_tokens': 1000,
    'temperature': 0.7
}

# Status de resposta da IA
AI_STATUS = {
    'success': 'success',
    'error': 'error',
    'timeout': 'timeout'
}

# Palavras-chave para detecção de produtos
PRODUCT_KEYWORDS = [
    'quanto custa', 'preço', 'valor', 'onde comprar', 'mais barato',
    'procurando', 'preciso de', 'quero comprar', 'buscando',
    'filtro', 'óleo', 'pastilha', 'freio', 'bateria', 'correia',
    'lâmpada', 'aditivo', 'palheta'
]

# Mapeamento de termos para produtos
PRODUCT_MAPPINGS = {
    'óleo': 'óleo',
    'filtro de óleo': 'filtro de óleo',
    'filtro de ar': 'filtro de ar',
    'pastilha de freio': 'pastilha de freio',
    'fluido de freio': 'fluido de freio',
    'lâmpada': 'lâmpada',
    'aditivo': 'aditivo',
    'palheta': 'palheta',
    'bateria': 'bateria',
    'correia': 'correia'
}
