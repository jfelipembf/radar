"""
Módulo Product Radar - Busca e comparação de produtos
"""

# Importar apenas tipos e constantes que não dependem de conexões externas
from .product_radar_types import RADAR_CONFIG, SEARCH_STATUS, PRODUCT_TYPES, PRODUCT_REQUIRED_FIELDS

# Função mock que funciona sem Supabase
def compare_prices(product_name: str, sector: str = 'autopecas') -> dict:
    """
    Função mock que simula busca no RADAR quando Supabase não está disponível
    """
    return {
        "erro": f"RADAR indisponível: Sistema de busca não configurado. Para buscar '{product_name}', configure as variáveis SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY."
    }

__all__ = [
    'RADAR_CONFIG',
    'SEARCH_STATUS',
    'PRODUCT_TYPES',
    'PRODUCT_REQUIRED_FIELDS',
    'compare_prices'
]
