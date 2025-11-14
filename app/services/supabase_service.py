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
        """Busca produtos cadastrados, opcionalmente filtrando por segmento e termos.
        
        Args:
            segment: Segmento do produto (ex: 'material_construcao')
            search_terms: Termos de busca genéricos
            limit: Limite de resultados
            exact_filters: Filtros exatos para aplicar (ex: {'capacity': '1000L', 'type': 'CP-II'})
        """

        params: Dict[str, Any] = {
            "select": "id,segment,sector,name,description,brand,unit_label,price,updated_at,delivery_info,store_phone,store:stores(name,phone)",
            "order": "name.asc",
            "limit": str(limit),
        }

        if segment:
            params["segment"] = f"eq.{segment}"

        # Se há termos de busca, fazer busca sem filtro e filtrar depois
        if search_terms:
            # Buscar todos os produtos do segmento e filtrar em Python
            all_products = self._get_products_by_segment(segment, limit * 3)  # Buscar mais para ter margem
            filtered_products = []

            for product in all_products:
                product_name = product.get("name", "").lower()
                product_desc = product.get("description", "").lower()
                
                # Verificar se algum termo de busca está no nome ou descrição
                matches_search = any(term.lower() in product_name or term.lower() in product_desc for term in search_terms)
                
                if matches_search:
                    # Se há filtros exatos, aplicar
                    if exact_filters:
                        matches_filters = True
                        for filter_key, filter_value in exact_filters.items():
                            filter_value_lower = filter_value.lower()
                            # Verificar se o filtro está no nome ou descrição
                            if filter_value_lower not in product_name and filter_value_lower not in product_desc:
                                matches_filters = False
                                break
                        
                        if matches_filters:
                            filtered_products.append(product)
                    else:
                        filtered_products.append(product)

            logger.debug(
                "Supabase → filtrados %d produtos de %d (termos=%s, filtros=%s)",
                len(filtered_products),
                len(all_products),
                search_terms,
                exact_filters,
            )

            # Limitar resultado
            return filtered_products[:limit]

        url = f"{self._rest_base}/products"
        logger.debug(
            "Supabase → buscando produtos (segment=%s search_terms=%s)",
            segment,
            search_terms,
        )
        response = requests.get(url, headers=self._headers, params=params, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao buscar produtos: %s", response.text)
            response.raise_for_status()
        return response.json()

    def _get_products_by_segment(self, segment: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Busca produtos por segmento (método auxiliar)."""
        params: Dict[str, Any] = {
            "select": "id,segment,sector,name,description,brand,unit_label,price,updated_at,delivery_info,store_phone,store:stores(name,phone)",
            "order": "name.asc",
            "limit": str(limit),
        }

        if segment:
            params["segment"] = f"eq.{segment}"

        url = f"{self._rest_base}/products"
        logger.debug("Supabase → buscando produtos por segmento: %s", segment)
        response = requests.get(url, headers=self._headers, params=params, timeout=10)
        if not response.ok:
            logger.error("Supabase → erro ao buscar produtos por segmento: %s", response.text)
            response.raise_for_status()
        return response.json()

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
