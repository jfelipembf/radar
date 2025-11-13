"""
Gerenciador de Contexto de Conversas
Responsável por:
- Controle de primeira mensagem do dia
- Sistema de debounce de 15 segundos
- Gerenciamento de contexto de conversa com TTL
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

@dataclass
class MessageContext:
    """Estrutura para uma mensagem no contexto"""
    role: str  # 'user' ou 'assistant'
    content: str
    created_at: datetime

@dataclass
class ConversationState:
    """Estado atual da conversa"""
    user_id: str
    is_first_message_today: bool
    context_messages: List[MessageContext]
    debounce_task: Optional[asyncio.Task] = None
    last_message_time: Optional[datetime] = None

class ConversationManager:
    """Gerenciador centralizado de contexto de conversas"""

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not self.supabase_url or not self.supabase_key:
            logger.warning("SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não configuradas. ConversationManager funcionará em modo limitado.")
            self.supabase_available = False
        else:
            self.supabase_available = True

        self.active_conversations: Dict[str, ConversationState] = {}
        self.debounce_delay = 15  # segundos
        logger.info("ConversationManager inicializado")

    async def _call_supabase_rpc(self, function_name: str, payload: dict):
        """Executa função RPC no Supabase."""
        if not self.supabase_available:
            logger.warning("Supabase não disponível, pulo chamada RPC: %s", function_name)
            return None

        url = f"{self.supabase_url}/rest/v1/rpc/{function_name}"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }

        logger.debug("Chamando RPC Supabase: %s payload=%s", function_name, payload)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.debug("Resposta RPC %s: status=%s body=%s", function_name, response.status_code, response.text)
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Erro HTTP ao chamar RPC %s: %s - %s", function_name, exc.response.status_code, exc.response.text)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Erro ao chamar RPC %s: %s", function_name, exc)

        return None

    async def check_first_message_today(self, user_id: str) -> bool:
        """
        Verifica se é a primeira mensagem do dia do usuário
        """
        result = await self._call_supabase_rpc('is_first_message_today', {'user_phone': user_id})

        if result is None:
            logger.warning("Falha ao verificar primeira mensagem via Supabase. Assumindo True para %s", user_id)
            return True

        # A função RPC pode retornar lista com boolean ou boolean direto
        if isinstance(result, list):
            is_first = bool(result[0]) if result else True
        else:
            is_first = bool(result)

        logger.info("Primeira mensagem do dia para %s: %s", user_id, is_first)
        return is_first

    async def save_message(self, user_id: str, role: str, content: str) -> None:
        """
        Salva mensagem no contexto da conversa
        """
        result = await self._call_supabase_rpc('save_message_context', {
            'p_user_id': user_id,
            'p_role': role,
            'p_content': content
        })

        if result is None:
            logger.warning("Mensagem não salva em Supabase para %s (%s)", user_id, role)
        else:
            logger.info("Mensagem salva em Supabase: %s - %s (id=%s)", user_id, role, result)

    async def get_conversation_context(self, user_id: str, limit: int = 10) -> List[MessageContext]:
        """
        Obtém contexto da conversa (últimas N mensagens)
        """
        result = await self._call_supabase_rpc('get_conversation_context', {
            'user_phone': user_id,
            'limit_count': limit
        })

        if result is None:
            logger.warning("Contexto não retornado pelo Supabase para %s", user_id)
            return []

        messages: List[MessageContext] = []
        for row in result:
            created_at_raw = row.get('created_at')
            created_at = None
            if isinstance(created_at_raw, str):
                try:
                    created_at = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
                except ValueError:
                    created_at = datetime.now()

            messages.append(MessageContext(
                role=row.get('role', 'user'),
                content=row.get('content', ''),
                created_at=created_at or datetime.now()
            ))

        logger.info("Contexto recuperado para %s: %s mensagens", user_id, len(messages))
        messages.reverse()
        return messages

    async def start_debounce_timer(self, user_id: str, callback_func) -> None:
        """
        Inicia/cancela timer de debounce de 15 segundos
        """
        # Cancelar timer anterior se existir
        if user_id in self.active_conversations:
            old_task = self.active_conversations[user_id].debounce_task
            if old_task and not old_task.done():
                old_task.cancel()
                logger.info(f"Timer anterior cancelado para {user_id}")

        # Criar novo timer
        async def debounce_callback():
            try:
                logger.info(f"Aguardando {self.debounce_delay} segundos para {user_id}...")
                await asyncio.sleep(self.debounce_delay)
                logger.info(f"Debounce concluído para {user_id}, executando callback")

                # Verificar se ainda é relevante (não foi cancelado por nova mensagem)
                if user_id in self.active_conversations:
                    await callback_func()
                else:
                    logger.info(f"Callback ignorado para {user_id} - conversa removida")

            except asyncio.CancelledError:
                logger.info(f"Debounce cancelado para {user_id}")
                raise
            except Exception as e:
                logger.error(f"Erro no callback de debounce para {user_id}: {e}")

        task = asyncio.create_task(debounce_callback())
        self.active_conversations[user_id].debounce_task = task
        logger.info(f"Novo timer de debounce iniciado para {user_id} ({self.debounce_delay}s)")

    async def process_incoming_message(self, user_id: str, message_text: str) -> Tuple[bool, List[MessageContext]]:
        """
        Processa mensagem recebida, retorna (is_first_today, context_messages)
        """
        # Verificar se é primeira mensagem do dia
        is_first_today = await self.check_first_message_today(user_id)

        # Salvar mensagem do usuário
        await self.save_message(user_id, 'user', message_text)

        # Obter contexto atual
        context = await self.get_conversation_context(user_id)

        # Inicializar estado da conversa se necessário
        if user_id not in self.active_conversations:
            self.active_conversations[user_id] = ConversationState(
                user_id=user_id,
                is_first_message_today=is_first_today,
                context_messages=context
            )
        else:
            self.active_conversations[user_id].context_messages = context

        return is_first_today, context

    async def process_outgoing_message(self, user_id: str, message_text: str) -> None:
        """
        Processa mensagem enviada (resposta da IA)
        """
        await self.save_message(user_id, 'assistant', message_text)

        # Atualizar contexto
        context = await self.get_conversation_context(user_id)
        if user_id in self.active_conversations:
            self.active_conversations[user_id].context_messages = context

    async def cleanup_expired_conversations(self) -> None:
        """
        Limpa conversas expiradas da memória (mantém apenas ativas)
        """
        # Remove conversas sem atividade recente (mais de 1 hora)
        cutoff_time = datetime.now() - timedelta(hours=1)
        expired_users = []

        for user_id, state in self.active_conversations.items():
            if state.last_message_time and state.last_message_time < cutoff_time:
                expired_users.append(user_id)

        for user_id in expired_users:
            del self.active_conversations[user_id]
            logger.info(f"Conversa expirada removida: {user_id}")

        if expired_users:
            logger.info(f"Limpeza concluída: {len(expired_users)} conversas removidas")

# Instância global
conversation_manager = ConversationManager()
