"""
Operações de banco de dados específicas do módulo Product Radar
"""
# Removendo import do supabase do nível do módulo para evitar erros de inicialização

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
        import os
        from supabase import create_client

        from .product_radar_domain import normalize_product_name

        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            return {
                'success': False,
                'error': 'Supabase não configurado',
                'data': []
            }

        supabase = create_client(supabase_url, supabase_key)
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
        import os
        from supabase import create_client

        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            return {
                'success': False,
                'error': 'Supabase não configurado',
                'data': []
            }

        supabase = create_client(supabase_url, supabase_key)
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
        import os
        from supabase import create_client
        from datetime import datetime, timedelta

        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            return {
                'success': False,
                'error': 'Supabase não configurado',
                'data': []
            }

        supabase = create_client(supabase_url, supabase_key)
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
        import os
        from supabase import create_client

        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            return {
                'success': False,
                'error': 'Supabase não configurado',
                'data': []
            }

        supabase = create_client(supabase_url, supabase_key)
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
