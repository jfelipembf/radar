"""
Tipos e constantes específicos do módulo Product Radar
"""

# Configurações do radar
RADAR_CONFIG = {
    'default_limit': 50,
    'price_tolerance': 0.05,  # 5% de tolerância para preços
    'min_results': 3,
    'max_results': 10
}

# Status de busca
SEARCH_STATUS = {
    'success': 'success',
    'no_results': 'no_results',
    'error': 'error',
    'timeout': 'timeout'
}

# Tipos de produtos suportados
PRODUCT_TYPES = {
    'oleo': 'óleo',
    'filtro_oleo': 'filtro de óleo',
    'filtro_ar': 'filtro de ar',
    'pastilha_freio': 'pastilha de freio',
    'fluido_freio': 'fluido de freio',
    'lampada': 'lâmpada',
    'aditivo': 'aditivo',
    'palheta': 'palheta',
    'bateria': 'bateria',
    'correia': 'correia'
}

# Campos obrigatórios de produto
PRODUCT_REQUIRED_FIELDS = [
    'produto', 'loja', 'preco', 'marca', 'unidade'
]
