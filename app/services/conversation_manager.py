"""
Gerenciador de Contexto de Conversas
Responsável por:
- Controle de primeira mensagem do dia
- Sistema de debounce de 15 segundos
- Gerenciamento de contexto de conversa com TTL
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from supabase import create_client, Client

from app.config.settings import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

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
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.active_conversations: Dict[str, ConversationState] = {}
        self.debounce_delay = 15  # segundos
        logger.info("ConversationManager inicializado")

    async def check_first_message_today(self, user_id: str) -> bool:
        """
        Verifica se é a primeira mensagem do dia do usuário
        """
        try:
            # Usar função SQL para verificar
            result = self.supabase.rpc('is_first_message_today', {
                'user_phone': user_id
            }).execute()

            is_first = result.data[0] if result.data else True
            logger.info(f"Primeira mensagem do dia para {user_id}: {is_first}")
            return is_first

        except Exception as e:
            logger.error(f"Erro ao verificar primeira mensagem: {e}")
            return True  # Assume primeira mensagem em caso de erro

    async def save_message(self, user_id: str, role: str, content: str) -> None:
        """
        Salva mensagem no contexto da conversa
        """
        try:
            # Usar função SQL para salvar
            self.supabase.rpc('save_message_context', {
                'p_user_id': user_id,
                'p_role': role,
                'p_content': content
            }).execute()

            logger.info(f"Mensagem salva: {user_id} - {role}")

        except Exception as e:
            logger.error(f"Erro ao salvar mensagem: {e}")
            raise

    async def get_conversation_context(self, user_id: str, limit: int = 10) -> List[MessageContext]:
        """
        Obtém contexto da conversa (últimas N mensagens)
        """
        try:
            # Usar função SQL para obter contexto
            result = self.supabase.rpc('get_conversation_context', {
                'user_phone': user_id,
                'limit_count': limit
            }).execute()

            # Converter para objetos MessageContext
            messages = []
            for row in result.data:
                messages.append(MessageContext(
                    role=row['role'],
                    content=row['content'],
                    created_at=row['created_at']
                ))

            # Retornar em ordem cronológica (mais antiga primeiro)
            messages.reverse()
            return messages

        except Exception as e:
            logger.error(f"Erro ao obter contexto: {e}")
            return []

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
