"""
Operações de banco de dados específicas do módulo Product Radar
"""
import os
from supabase import create_client, Client
from .product_radar_domain import normalize_product_name

# Conexão com Supabase
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

def search_products_by_name(product_name: str, sector: str = 'autopecas') -> dict:
    """
    Busca produtos por nome aproximado

    Args:
        product_name: Nome do produto
        sector: Setor do produto

    Returns:
        dict: Resultado da busca
    """
    try:
        normalized_name = normalize_product_name(product_name)

        query = supabase.table('products').select('*').ilike('produto', f'%{normalized_name}%')

        if sector:
            query = query.eq('setor', sector)

        result = query.execute()

        return {
            'success': True,
            'data': result.data,
            'count': len(result.data) if result.data else 0
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': []
        }

def search_products_by_category(category: str, max_price: float = None) -> dict:
    """
    Busca produtos por categoria

    Args:
        category: Categoria do produto
        max_price: Preço máximo (opcional)

    Returns:
        dict: Resultado da busca
    """
    try:
        query = supabase.table('products').select('*').eq('categoria', category).eq('disponivel', True)

        if max_price:
            query = query.lte('preco', max_price)

        result = query.limit(20).execute()

        return {
            'success': True,
            'data': result.data,
            'count': len(result.data) if result.data else 0
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': []
        }

def get_recent_products(days: int = 7) -> dict:
    """
    Busca produtos atualizados recentemente

    Args:
        days: Número de dias

    Returns:
        dict: Resultado da busca
    """
    try:
        from datetime import datetime, timedelta

        limit_date = datetime.now() - timedelta(days=days)

        result = supabase.table('products').select('*').gte('atualizado_em', limit_date.isoformat()).execute()

        return {
            'success': True,
            'data': result.data,
            'count': len(result.data) if result.data else 0
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': []
        }

def get_store_products(store_id: str) -> dict:
    """
    Busca produtos de uma loja específica

    Args:
        store_id: ID da loja

    Returns:
        dict: Resultado da busca
    """
    try:
        result = supabase.table('products').select('*').eq('loja_id', store_id).execute()

        return {
            'success': True,
            'data': result.data,
            'count': len(result.data) if result.data else 0
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': []
        }
