"""
Módulo Product Radar - Busca e comparação de produtos
"""

# Importar apenas tipos e constantes que não dependem de conexões externas
from .product_radar_types import RADAR_CONFIG, SEARCH_STATUS, PRODUCT_TYPES, PRODUCT_REQUIRED_FIELDS

# Funções que dependem de banco serão importadas sob demanda
def get_compare_prices_function():
    """Importa função compare_prices sob demanda"""
    from .product_radar_functions import compare_prices
    return compare_prices

def get_search_by_category_function():
    """Importa função search_by_category sob demanda"""
    from .product_radar_functions import search_by_category
    return search_by_category

__all__ = [
    'RADAR_CONFIG',
    'SEARCH_STATUS',
    'PRODUCT_TYPES',
    'PRODUCT_REQUIRED_FIELDS',
    'get_compare_prices_function',
    'get_search_by_category_function'
]
