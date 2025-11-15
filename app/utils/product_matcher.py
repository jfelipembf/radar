"""Helper para matching de produtos com keywords."""

from typing import List, Dict, Any


def match_all_keywords(product: Dict[str, Any], query_keywords: List[str]) -> bool:
    """
    Verifica se produto tem TODAS as keywords solicitadas.
    
    Args:
        product: Produto do Supabase com campo 'keywords'
        query_keywords: Lista de keywords a buscar
        
    Returns:
        True se produto tem TODAS as keywords
    """
    product_keywords = [pk.lower() for pk in product.get('keywords', [])]
    normalized_query = [qk.lower().strip() for qk in query_keywords]
    
    # Verificar se TODAS as keywords da query estão presentes
    # Cada keyword da query deve estar contida em pelo menos uma keyword do produto
    return all(
        any(qk in pk or pk in qk for pk in product_keywords)
        for qk in normalized_query
    )


__all__ = ["match_all_keywords"]
