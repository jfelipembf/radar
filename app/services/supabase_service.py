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
    ) -> List[Dict[str, Any]]:
        """Busca produtos cadastrados, opcionalmente filtrando por segmento e termos."""

        params: Dict[str, Any] = {
            "select": "id,segment,sector,name,description,brand,unit_label,price,updated_at,delivery_info,store_phone,store:stores(name,phone)",
            "order": "name.asc",
            "limit": str(limit),
        }

        if segment:
            params["segment"] = f"eq.{segment}"

        # Se há termos de busca, adicionar filtro OR para cada termo
        if search_terms:
            # Criar filtro OR para buscar produtos que contenham qualquer um dos termos
            or_conditions = []
            for term in search_terms:
                # Usar ilike para busca case-insensitive
                or_conditions.append(f"name.ilike.%{term}%")

            if or_conditions:
                params["or"] = f"({','.join(or_conditions)})"

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
