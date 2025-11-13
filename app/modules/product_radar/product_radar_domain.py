"""
Regras de negócio e validações do módulo Product Radar
"""
from .product_radar_types import RADAR_CONFIG, SEARCH_STATUS, PRODUCT_TYPES, PRODUCT_REQUIRED_FIELDS

def validate_product_data(product_data: dict) -> dict:
    """
    Valida dados de produto

    Args:
        product_data: Dados do produto

    Returns:
        dict: Resultado da validação
    """
    if not isinstance(product_data, dict):
        return {'valid': False, 'error': 'invalid_data_type'}

    # Verificar campos obrigatórios
    for field in PRODUCT_REQUIRED_FIELDS:
        if field not in product_data:
            return {'valid': False, 'error': f'missing_field_{field}'}

    # Validar preço
    if not isinstance(product_data.get('preco'), (int, float)) or product_data['preco'] <= 0:
        return {'valid': False, 'error': 'invalid_price'}

    return {'valid': True}

def calculate_price_economy(products: list) -> dict:
    """
    Calcula economia de preços

    Args:
        products: Lista de produtos ordenados por preço

    Returns:
        dict: Dados de economia
    """
    if not products:
        return {'valor': 0, 'percentual': 0}

    cheapest = products[0]['preco']
    most_expensive = products[-1]['preco']

    if most_expensive == 0:
        return {'valor': 0, 'percentual': 0}

    economy_value = most_expensive - cheapest
    economy_percentage = (economy_value / most_expensive) * 100

    return {
        'valor': round(economy_value, 2),
        'percentual': round(economy_percentage, 1)
    }

def format_product_comparison(products: list, best_product: dict) -> list:
    """
    Formata comparação de produtos

    Args:
        products: Lista de produtos
        best_product: Melhor produto

    Returns:
        list: Comparação formatada
    """
    comparison = []
    best_price = best_product['preco']

    for product in products:
        comparison.append({
            'loja': product['comercio'],
            'preco': product['preco'],
            'diferenca': round(product['preco'] - best_price, 2)
        })

    return comparison

def filter_products_by_price(products: list, max_price: float = None, min_price: float = None) -> list:
    """
    Filtra produtos por faixa de preço

    Args:
        products: Lista de produtos
        max_price: Preço máximo (opcional)
        min_price: Preço mínimo (opcional)

    Returns:
        list: Produtos filtrados
    """
    filtered = products

    if max_price is not None:
        filtered = [p for p in filtered if p['preco'] <= max_price]

    if min_price is not None:
        filtered = [p for p in filtered if p['preco'] >= min_price]

    return filtered

def validate_search_results(products: list) -> dict:
    """
    Valida resultados de busca

    Args:
        products: Lista de produtos encontrados

    Returns:
        dict: Status da validação
    """
    if not products:
        return {'valid': False, 'status': SEARCH_STATUS['no_results']}

    if len(products) < RADAR_CONFIG['min_results']:
        return {'valid': False, 'status': SEARCH_STATUS['no_results'], 'message': 'insufficient_results'}

    return {'valid': True, 'status': SEARCH_STATUS['success']}

def normalize_product_name(product_name: str) -> str:
    """
    Normaliza nome do produto para busca

    Args:
        product_name: Nome do produto

    Returns:
        str: Nome normalizado
    """
    if not product_name:
        return ""

    # Remover acentos e caracteres especiais
    import unicodedata
    normalized = unicodedata.normalize('NFD', product_name)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    # Converter para minúsculo e remover espaços extras
    return ' '.join(normalized.lower().split())
