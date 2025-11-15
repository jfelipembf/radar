"""Supabase service helper via REST endpoints."""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class SupabaseService:
    """Wrapper to interact with Supabase REST endpoints."""

    def __init__(self) -> None:
        self._url = os.getenv("SUPABASE_URL")
        self._key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self._table = os.getenv("SUPABASE_MESSAGES_TABLE", "conversation_context")
        self._temp_table = os.getenv("SUPABASE_TEMP_MESSAGES_TABLE", "temporary_messages")

        if not self._url or not self._key:
            raise ValueError("SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não configurados")

        self._rest_base = self._url.rstrip("/") + "/rest/v1"
        self._headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }

    def save_message(self, payload: Dict[str, Any], upsert: bool = False) -> None:
        """Insere ou upserte uma mensagem na tabela configurada."""
        headers = self._headers.copy()
        if upsert:
            headers["Prefer"] = "resolution=ignore-duplicates"

        url = f"{self._rest_base}/{self._table}"
        logger.debug("Supabase → salvando payload: %s", payload)
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao salvar: %s", response.text)
            response.raise_for_status()

    def save_temp_message(self, payload: Dict[str, Any], upsert: bool = False) -> None:
        """Persiste mensagem temporária."""
        headers = self._headers.copy()
        if upsert:
            headers["Prefer"] = "resolution=ignore-duplicates"

        url = f"{self._rest_base}/{self._temp_table}"
        logger.debug("Supabase → salvando mensagem temporária: %s", payload)
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao salvar temporário: %s", response.text)
            response.raise_for_status()

    def get_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna mensagens recentes do usuário."""
        params = {
            "select": "*",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        url = f"{self._rest_base}/{self._table}"
        logger.debug("Supabase → buscando mensagens para %s", user_id)
        response = requests.get(url, headers=self._headers, params=params, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao buscar: %s", response.text)
            response.raise_for_status()
        return response.json()

    def get_temp_messages(self, user_id: str) -> List[Dict[str, Any]]:
        """Busca mensagens temporárias ordenadas pelo horário."""
        params = {
            "select": "*",
            "user_id": f"eq.{user_id}",
            "order": "created_at.asc",
        }
        url = f"{self._rest_base}/{self._temp_table}"
        logger.debug("Supabase → buscando temporários para %s", user_id)
        response = requests.get(url, headers=self._headers, params=params, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao buscar temporários: %s", response.text)
            response.raise_for_status()
        return response.json()

    def get_latest_message(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retorna a mensagem mais recente registrada para o usuário."""
        params = {
            "select": "*",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
            "limit": "1",
        }
        url = f"{self._rest_base}/{self._table}"
        logger.debug("Supabase → buscando última mensagem para %s", user_id)
        response = requests.get(url, headers=self._headers, params=params, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao buscar última mensagem: %s", response.text)
            response.raise_for_status()
        data = response.json()
        if not data:
            return None
        return data[0]

    def get_products(
        self,
        segment: Optional[str] = None,
        search_terms: Optional[List[str]] = None,
        limit: int = 50,
        exact_filters: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Busca produtos cadastrados usando keywords otimizadas.
        
        Args:
            segment: Segmento do produto (opcional, filtra por categoria de negócio)
            search_terms: Termos de busca genéricos
            limit: Limite de resultados
            exact_filters: Filtros exatos para aplicar (ex: {'brand': 'MarcaX', 'unit_label': 'unidade'})
        """
        # Se há termos de busca, usar busca otimizada com keywords
        if search_terms:
            return self.search_products_by_keywords(
                keywords=search_terms,
                segment=segment,
                limit=limit
            )

        # Busca simples sem filtros
        params: Dict[str, Any] = {
            "select": "id,segment,sector,name,description,brand,unit_label,price,updated_at,delivery_info,store_phone,keywords,store:stores(name,phone)",
            "order": "price.asc",
            "limit": str(limit),
        }

        if segment:
            params["segment"] = f"eq.{segment}"

        url = f"{self._rest_base}/products"
        logger.debug(
            "Supabase → buscando produtos (segment=%s)",
            segment,
        )
        response = requests.get(url, headers=self._headers, params=params, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao buscar produtos: %s", response.text)
            response.raise_for_status()
        return response.json()
    
    def search_products_by_keywords(
        self,
        keywords: List[str],
        segment: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Busca produtos usando keywords com índice GIN (MUITO RÁPIDO).
        
        Args:
            keywords: Lista de palavras-chave para buscar
            segment: Segmento opcional para filtrar
            limit: Limite de resultados
            
        Returns:
            Lista de produtos que contêm qualquer uma das keywords
        """
        # Normalizar keywords
        normalized_keywords = [k.lower().strip() for k in keywords if k.strip()]
        
        if not normalized_keywords:
            return []
        
        # Construir query com operador && (overlap) para busca em array
        # keywords && ARRAY['cerveja', 'skol'] retorna produtos que têm qualquer uma dessas palavras
        keywords_array = "{" + ",".join(normalized_keywords) + "}"
        
        params: Dict[str, Any] = {
            "select": "id,segment,sector,name,description,brand,unit_label,price,updated_at,delivery_info,store_phone,keywords,store:stores(name,phone)",
            "keywords": f"ov.{keywords_array}",  # ov = overlap operator
            "order": "price.asc",
            "limit": str(limit),
        }
        
        if segment:
            params["segment"] = f"eq.{segment}"
        
        url = f"{self._rest_base}/products"
        logger.info(
            "Supabase → busca otimizada com keywords: %s (segment=%s)",
            normalized_keywords,
            segment
        )
        
        response = requests.get(url, headers=self._headers, params=params, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro na busca por keywords: %s", response.text)
            response.raise_for_status()
        
        results = response.json()
        logger.info("Supabase → encontrados %d produtos com keywords", len(results))
        return results
    
    def search_multiple_products_batch(
        self,
        product_queries: List[Dict[str, Any]],
        segment: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Busca múltiplos produtos em uma única chamada otimizada.
        
        Args:
            product_queries: Lista de queries, ex: [{'keywords': ['cerveja', 'skol']}, {'keywords': ['coca-cola']}]
            segment: Segmento opcional
            
        Returns:
            Dict mapeando query -> produtos encontrados
        """
        results = {}
        
        # Coletar todas as keywords únicas
        all_keywords = set()
        for query in product_queries:
            keywords = query.get('keywords', [])
            all_keywords.update(k.lower().strip() for k in keywords if k.strip())
        
        if not all_keywords:
            return results
        
        # Buscar TODOS os produtos com qualquer keyword de uma vez
        all_products = self.search_products_by_keywords(
            keywords=list(all_keywords),
            segment=segment,
            limit=200  # Buscar mais para garantir cobertura
        )
        
        # Agrupar produtos por query
        for i, query in enumerate(product_queries):
            query_keywords = [k.lower().strip() for k in query.get('keywords', [])]
            query_key = f"query_{i}"
            
            # Filtrar produtos que correspondem a esta query
            matching_products = []
            for product in all_products:
                product_keywords = [pk.lower() for pk in product.get('keywords', [])]
                # Verificar se alguma keyword da query está contida em alguma keyword do produto
                if any(any(qk in pk or pk in qk for pk in product_keywords) for qk in query_keywords):
                    matching_products.append(product)
            
            results[query_key] = matching_products
        
        logger.info(
            "Supabase → busca em lote: %d queries, %d produtos totais",
            len(product_queries),
            len(all_products)
        )
        
        return results

    def delete_temp_messages(self, message_ids: List[str]) -> None:
        """Remove mensagens temporárias processadas."""
        if not message_ids:
            return

        unique_ids = list(dict.fromkeys(message_ids))
        ids_clause = ",".join(f'"{mid}"' for mid in unique_ids)
        params = {"id": f"in.({ids_clause})"}
        url = f"{self._rest_base}/{self._temp_table}"
        logger.debug("Supabase → removendo temporários: %s", message_ids)
        response = requests.delete(url, headers=self._headers, params=params, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao remover temporários: %s", response.text)
            response.raise_for_status()


__all__ = ["SupabaseService"]
