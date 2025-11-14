"""Serviço principal do chatbot para processamento de mensagens."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.business.construction_rules import (
    should_search_products,
    extract_product_names,
    format_product_catalog,
)
from app.services.openai_service import OpenAIService
from app.services.supabase_service import SupabaseService
from app.services.evolution_service import EvolutionService
from app.utils.parsers import _consolidate_temp_messages, _latest_user_content
from app.utils.formatters import _sort_key

logger = logging.getLogger(__name__)


class ChatbotService:
    """Serviço principal para processamento de mensagens do chatbot."""

    def __init__(
        self,
        openai_service: OpenAIService,
        supabase_service: Optional[SupabaseService],
        evolution_service: EvolutionService
    ):
        self.openai_service = openai_service
        self.supabase_service = supabase_service
        self.evolution_service = evolution_service

    async def process_message(self, user_id: str, text: str, message_data: dict) -> str:
        """Processa uma mensagem do usuário e retorna a resposta."""
        logger.info(f"Processing message from {user_id}: {text}")

        # Se Supabase não está disponível, responder imediatamente
        if not self.supabase_service:
            response_text = await self.openai_service.generate_response(message=text)
            logger.debug(f"Generated response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
            return response_text

        # Verificar saudação diária
        await self._maybe_send_daily_greeting(user_id)

        # Registrar mensagem temporária
        await self._record_temp_message(user_id, text, message_data)

        # Agendar processamento (debounced)
        await self._schedule_user_processing(user_id)

        return "queued"  # Resposta será enviada posteriormente via debounce

    async def process_debounced_messages(self, user_id: str) -> Optional[str]:
        """Processa mensagens consolidadas após debounce."""
        if not self.supabase_service:
            return None

        # Buscar mensagens temporárias
        temp_messages = await asyncio.to_thread(self.supabase_service.get_temp_messages, user_id)
        if not temp_messages:
            return None

        # Buscar histórico de mensagens
        history = await self._build_message_history(user_id)

        # Consolidar mensagens temporárias
        consolidated = _consolidate_temp_messages(temp_messages)
        if consolidated:
            history.append(consolidated)

        # Encontrar texto para busca de produtos
        search_source = consolidated["content"] if consolidated else _latest_user_content(history)

        # Buscar produtos se aplicável
        catalog_context = await self._build_product_context(search_source)

        # Preparar resposta
        response_text = await self._prepare_response(user_id, history, catalog_context)

        # Limpar mensagens temporárias e salvar resposta
        await self._cleanup_and_save(user_id, temp_messages, consolidated, response_text)

        # ENVIAR resposta final via WhatsApp
        await self._send_whatsapp_message(user_id, response_text)

        # Atualizar presença para "paused"
        await self._update_presence(user_id, "paused")

        return response_text

    async def _build_message_history(self, user_id: str) -> List[Dict[str, str]]:
        """Constrói histórico de mensagens do usuário."""
        HISTORY_LIMIT = 40  # TODO: mover para configuração

        history: List[Dict[str, str]] = []
        recent_messages = await asyncio.to_thread(
            self.supabase_service.get_recent_messages,
            user_id,
            HISTORY_LIMIT,
        )

        for msg in sorted(recent_messages, key=_sort_key):
            if msg.get("content"):
                history.append({
                    "role": msg.get("role", "user"),
                    "content": msg["content"],
                })

        return history

    async def _build_product_context(self, search_text: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
        """Constrói contexto de produtos baseado no texto de busca."""
        if not search_text:
            return None

        # Primeiro, perguntar à IA se deve buscar produtos
        should_search = await should_search_products(search_text, self.openai_service)
        if not should_search:
            logger.info("Catálogo → IA decidiu não buscar produtos para: %s", search_text)
            return None

        # Extrair produtos específicos mencionados usando IA
        product_names = await extract_product_names(search_text, self.openai_service)
        if not product_names:
            logger.info("Catálogo → Nenhum produto específico identificado em: %s", search_text)
            return None

        logger.debug("Catálogo → produtos identificados: %s", product_names)

        try:
            # Buscar produtos específicos no Supabase
            products = await asyncio.to_thread(
                self.supabase_service.get_products,
                "material_construcao",
                product_names,
                40,
            )

            # Filtrar apenas produtos que contenham os nomes identificados
            filtered_products = []
            for product in products:
                product_name = product.get("name", "").lower()
                if any(prod_name in product_name for prod_name in product_names):
                    filtered_products.append(product)

            logger.info("Catálogo → %d produtos retornados, %d após filtro específico", len(products), len(filtered_products))

            if not filtered_products:
                logger.info("Catálogo → nenhum produto correspondente após filtro")
                return None

            model_context, user_message = format_product_catalog(filtered_products, self.supabase_service)
            if not model_context and not user_message:
                logger.info("Catálogo → nenhum produto formatado para os termos %s", product_names)
            return {"model": model_context, "user": user_message}
        except Exception as exc:
            logger.error("Erro ao buscar catálogo de produtos: %s", exc)
            return None

    async def _prepare_response(
        self,
        user_id: str,
        history: List[Dict[str, str]],
        catalog_context: Optional[Dict[str, Optional[str]]]
    ) -> str:
        """Prepara a resposta final baseada no contexto."""
        catalog_message = None
        if catalog_context:
            model_context = catalog_context.get("model")
            catalog_message = catalog_context.get("user")
            if model_context:
                history.append({"role": "system", "content": model_context})

        if catalog_message:
            logger.info("Catálogo Supabase encontrado para %s; respondendo com dados estruturados", user_id)
            response_text = catalog_message
        else:
            logger.info("Nenhum catálogo disponível para %s; delegando resposta à OpenAI", user_id)
            response_text = await self.openai_service.generate_response(history=history)

        logger.debug(f"Generated response after debounce for {user_id}: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
        return response_text

    async def _cleanup_and_save(
        self,
        user_id: str,
        temp_messages: List[dict],
        consolidated: Optional[Dict[str, str]],
        response_text: str
    ):
        """Limpa mensagens temporárias e salva a conversa."""
        # Coletar IDs para limpeza
        temp_ids: List[str] = []
        if consolidated:
            for temp in temp_messages:
                temp_id = temp.get("id")
                if temp_id:
                    temp_ids.append(str(temp_id))

            # Salvar mensagem consolidada
            await self._log_message(
                user_id=user_id,
                content=consolidated["content"],
                role=consolidated["role"],
                created_at=consolidated.get("created_at"),
            )

        # Salvar resposta do assistente
        await self._log_message(user_id, response_text, role="assistant")

        # Limpar mensagens temporárias
        await asyncio.to_thread(self.supabase_service.delete_temp_messages, temp_ids)

    async def _maybe_send_daily_greeting(self, user_id: str):
        """Verifica e envia saudação diária se necessário."""
        if not self.supabase_service or not user_id:
            return

        try:
            latest_message = await asyncio.to_thread(self.supabase_service.get_latest_message, user_id)
        except Exception as exc:
            logger.error("Erro ao verificar primeira mensagem do dia para %s: %s", user_id, exc)
            return

        # Lógica de saudação diária (simplificada)
        now_local = asyncio.get_event_loop().time()  # TODO: implementar timezone
        should_send = not latest_message

        if should_send:
            greeting = "Radar ativado 🚨"
            await self._log_message(user_id, greeting, role="assistant")
            await self._send_whatsapp_message(user_id, greeting)

    async def _record_temp_message(self, user_id: str, text: str, message_data: dict):
        """Registra mensagem temporária."""
        from app.utils.formatters import _extract_created_at

        created_at = _extract_created_at(message_data)
        message_id = message_data.get('key', {}).get('id') or message_data.get('id') or ""

        payload = {
            "user_id": user_id,
            "role": "user",
            "content": text,
            "message_id": message_id,
            "created_at": created_at,
        }
        await asyncio.to_thread(self.supabase_service.save_temp_message, payload)

    async def _schedule_user_processing(self, user_id: str):
        """Agenda processamento debounced."""
        # Aguardar debounce e processar
        await asyncio.sleep(2)  # Debounce simplificado de 2 segundos para teste
        await self.process_debounced_messages(user_id)

    async def _log_message(self, user_id: str, content: str, role: str, created_at: Optional[str] = None):
        """Persiste mensagem no Supabase."""
        if not self.supabase_service:
            return

        try:
            from datetime import datetime, timezone
            payload = {
                "user_id": user_id,
                "role": role,
                "content": content,
                "created_at": created_at or datetime.now(timezone.utc).isoformat(),
            }
            await asyncio.to_thread(self.supabase_service.save_message, payload)
        except Exception as exc:
            logger.error("Erro ao salvar mensagem no Supabase: %s", exc)

    async def _update_presence(self, user_id: str, presence: str, delay_ms: Optional[int] = None):
        """Atualiza presença do WhatsApp."""
        try:
            await asyncio.to_thread(self.evolution_service.send_presence, user_id, presence, delay_ms)
        except Exception as exc:
            logger.error("Erro ao atualizar presença (%s) para %s: %s", presence, user_id, exc)
