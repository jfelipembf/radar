"""
Funções específicas do módulo Product Radar
"""
import logging
from .product_radar_db import search_products_by_name, search_products_by_category, get_recent_products, get_store_products
from .product_radar_domain import validate_search_results, calculate_price_economy, format_product_comparison

logger = logging.getLogger(__name__)

def compare_prices(product_name: str, sector: str = 'autopecas') -> dict:
    """
    Compara preços de um produto em diferentes lojas

    Args:
        product_name: Nome do produto
        sector: Setor do produto

    Returns:
        dict: Resultado da comparação
    """
    try:
        logger.info(f"Comparing prices for product: {product_name}")

        # Buscar produtos
        search_result = search_products_by_name(product_name, sector)

        # Se Supabase não está disponível, retorna mensagem mock
        if not search_result['success'] and 'Supabase não configurado' in search_result.get('error', ''):
            logger.warning(f"Supabase não configurado, retornando resposta mock para '{product_name}'")
            return {
                "erro": f"RADAR indisponível: Sistema de busca não configurado. Para buscar '{product_name}', configure as variáveis SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY."
            }

        if not search_result['success'] or not search_result['data']:
            return {"erro": f"Nenhum produto encontrado para: {product_name}"}

        products = search_result['data']

        # Validar resultados
        validation = validate_search_results(products)
        if not validation['valid']:
            return {"erro": f"Resultados insuficientes para: {product_name}"}

        # Ordenar por preço (menor para maior)
        products_sorted = sorted(products, key=lambda x: x['preco'])

        # Melhor opção
        best_product = products_sorted[0]

        # Calcular economia
        economy_data = calculate_price_economy(products_sorted)

        # Formatar comparação
        comparison = format_product_comparison(products_sorted, best_product)

        result = {
            "melhor_opcao": {
                "loja": best_product['comercio'],
                "produto": best_product['produto'],
                "preco": best_product['preco'],
                "marca": best_product['marca'],
                "unidade": best_product['unidade']
            },
            "comparacao": comparison,
            "economia_total": economy_data
        }

        logger.info(f"Price comparison completed for {product_name}: {len(products)} products found")
        return result

    except Exception as e:
        logger.error(f"Error comparing prices for {product_name}: {e}")
        return {"erro": f"Erro ao comparar preços: {str(e)}"}

def search_by_category(category: str, max_price: float = None) -> dict:
    """
    Busca produtos por categoria

    Args:
        category: Categoria do produto
        max_price: Preço máximo (opcional)

    Returns:
        dict: Resultado da busca
    """
    try:
        result = search_products_by_category(category, max_price)
        return result

    except Exception as e:
        logger.error(f"Error searching by category {category}: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': []
        }

def get_recent_products_list(days: int = 7) -> dict:
    """
    Obtém lista de produtos recentes

    Args:
        days: Número de dias

    Returns:
        dict: Lista de produtos recentes
    """
    try:
        result = get_recent_products(days)
        return result

    except Exception as e:
        logger.error(f"Error getting recent products: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': []
        }

def get_store_products_list(store_id: str) -> dict:
    """
    Obtém produtos de uma loja específica

    Args:
        store_id: ID da loja

    Returns:
        dict: Produtos da loja
    """
    try:
        result = get_store_products(store_id)
        return result

    except Exception as e:
        logger.error(f"Error getting store products for {store_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': []
        }
