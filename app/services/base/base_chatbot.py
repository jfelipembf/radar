"""
Serviço base de chatbot - lógica comum a todos os segmentos
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.mcp import ProductMCPServer
from app.services.openai_service import OpenAIService
from app.services.supabase_service import SupabaseService
from app.services.evolution_service import EvolutionService
from app.utils.parsers import _consolidate_temp_messages, _latest_user_content, _sort_key, _extract_created_at

logger = logging.getLogger(__name__)


class BaseChatbotService:
    """
    Serviço base de chatbot com lógica comum.
    Subclasses devem definir system_prompt e segment.
    """
    
    # Constantes
    HISTORY_LIMIT = 10
    DEBOUNCE_SECONDS = 15
    
    def __init__(
        self,
        openai_service: OpenAIService,
        supabase_service: SupabaseService,
        evolution_service: EvolutionService
    ):
        self.openai_service = openai_service
        self.supabase_service = supabase_service
        self.evolution_service = evolution_service
        
        # Inicializar MCP Server (compartilhado)
        self.mcp_server = ProductMCPServer(supabase_service)
        self.tools = self.mcp_server.get_tools_schema()
        
        # Definidos por subclasse
        self.system_prompt = ""
        self.segment = None
        
        logger.info(f"{self.__class__.__name__} inicializado com MCP ({len(self.tools)} ferramentas)")
    
    async def process_message(self, user_id: str, text: str, message_data: dict) -> str:
        """Processa mensagem do usuário."""
        logger.info(f"Processing message from {user_id}: {text}")
        
        # Verificar saudação diária
        await self._maybe_send_daily_greeting(user_id)
        
        # Registrar mensagem temporária
        await self._record_temp_message(user_id, text, message_data)
        
        # Agendar processamento (debounced)
        await self._schedule_user_processing(user_id)
        
        return "queued"
    
    async def process_debounced_messages(self, user_id: str) -> Optional[str]:
        """Processa mensagens com debounce usando MCP."""
        if not self.supabase_service:
            return None
        
        # Buscar mensagens temporárias
        temp_messages = await asyncio.to_thread(
            self.supabase_service.get_temp_messages, 
            user_id
        )
        if not temp_messages:
            return None
        
        # Buscar histórico
        history = await self._build_message_history(user_id)
        
        # Consolidar mensagens temporárias
        consolidated = _consolidate_temp_messages(temp_messages)
        if consolidated:
            history.append(consolidated)
        
        # Preparar mensagens para a IA com prompt específico do segmento
        messages = [
            {
                "role": "system",
                "content": self.system_prompt  # Prompt específico da subclasse
            }
        ] + history
        
        # Processar com MCP
        response_text = await self._process_with_mcp(messages)
        
        # Limpar e salvar
        await self._cleanup_and_save(user_id, temp_messages, consolidated, response_text)
        
        # Enviar resposta
        await self._send_whatsapp_message(user_id, response_text)
        await self._update_presence(user_id, "paused")
        
        return response_text
    
    async def _process_with_mcp(self, messages: List[Dict[str, str]]) -> str:
        """Processa mensagens com MCP, permitindo múltiplas chamadas de ferramentas."""
        max_iterations = 10
        iteration = 0
        tool_call_history = []
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"MCP iteration {iteration}")
            
            # Fazer chamada com tools
            response = await self.openai_service.chat_with_tools(
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # Se não usou ferramentas, retornar resposta
            if not assistant_message.tool_calls:
                return assistant_message.content or "Desculpe, não entendi."
            
            # IA usou ferramentas - processar
            logger.info(f"IA usou {len(assistant_message.tool_calls)} ferramenta(s)")
            
            # Adicionar mensagem do assistente
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Executar cada ferramenta
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                # Detectar loop
                call_signature = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
                if call_signature in tool_call_history[-3:]:
                    logger.warning(f"Loop detectado: {call_signature}")
                    return "Desculpe, encontrei um problema ao processar sua solicitação. Pode reformular?"
                tool_call_history.append(call_signature)
                
                logger.info(f"Executando: {tool_name}({arguments})")
                
                # Executar via MCP
                result = await asyncio.to_thread(
                    self.mcp_server.execute_tool,
                    tool_name,
                    arguments
                )
                
                logger.info(f"Resultado: {result.get('success', False)}")
                
                # Se foi finalize_purchase, enviar mensagem para a loja
                if tool_name == "finalize_purchase" and result.get("success"):
                    store_phone = result.get("store_phone")
                    store_message = result.get("store_message")
                    
                    if store_phone and store_message:
                        try:
                            logger.info(f"Enviando mensagem para loja: {store_phone}")
                            await self._send_whatsapp_message(store_phone, store_message)
                            logger.info("Mensagem enviada para loja com sucesso")
                        except Exception as exc:
                            logger.error(f"Erro ao enviar mensagem para loja: {exc}")
                
                # Adicionar resultado
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
        
        logger.warning(f"Atingiu max_iterations ({max_iterations})")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."
    
    async def _build_message_history(self, user_id: str) -> List[Dict[str, str]]:
        """Constrói histórico de mensagens."""
        if not self.supabase_service:
            return []
        
        recent_messages = await asyncio.to_thread(
            self.supabase_service.get_recent_messages,
            user_id,
            self.HISTORY_LIMIT,
        )
        
        history = []
        for msg in sorted(recent_messages, key=_sort_key):
            if msg.get("content"):
                history.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content")
                })
        
        return history
    
    async def _cleanup_and_save(self, user_id: str, temp_messages: list, consolidated: dict, response_text: str):
        """Limpa mensagens temporárias e salva no histórico."""
        if not self.supabase_service:
            return
        
        # Deletar temporárias
        temp_ids = [m.get("id") for m in temp_messages if m.get("id")]
        if temp_ids:
            await asyncio.to_thread(
                self.supabase_service.delete_temp_messages,
                temp_ids
            )
        
        # Salvar no histórico
        if consolidated:
            await self._log_message(user_id, consolidated.get("content", ""), role="user")
        
        await self._log_message(user_id, response_text, role="assistant")
    
    async def _log_message(self, user_id: str, content: str, role: str = "user"):
        """Salva mensagem no histórico."""
        if not self.supabase_service:
            return
        
        payload = {
            "user_id": user_id,
            "role": role,
            "content": content
        }
        
        await asyncio.to_thread(
            self.supabase_service.save_message,
            payload
        )
    
    async def _send_whatsapp_message(self, phone: str, text: str):
        """Envia mensagem via WhatsApp."""
        await asyncio.to_thread(self.evolution_service.send_message, phone, text)
    
    async def _update_presence(self, phone: str, presence: str):
        """Atualiza presença no WhatsApp."""
        await asyncio.to_thread(self.evolution_service.update_presence, phone, presence)
    
    async def _maybe_send_daily_greeting(self, user_id: str):
        """Envia saudação diária se for primeira mensagem do dia."""
        if not self.supabase_service:
            return
        
        try:
            latest_message = await asyncio.to_thread(
                self.supabase_service.get_recent_messages,
                user_id,
                1
            )
        except Exception as exc:
            logger.error(f"Erro ao verificar primeira mensagem: {exc}")
            return
        
        if not latest_message:
            greeting = "Radar ativado 🚨"
            await self._log_message(user_id, greeting, role="assistant")
            await self._send_whatsapp_message(user_id, greeting)
    
    async def _record_temp_message(self, user_id: str, text: str, message_data: dict):
        """Registra mensagem temporária."""
        created_at = _extract_created_at(message_data)
        message_id = message_data.get('key', {}).get('id') or message_data.get('id') or ""
        
        payload = {
            "user_id": user_id,
            "role": "user",
            "content": text,
            "message_id": message_id,
            "created_at": created_at,
        }
        
        if self.supabase_service:
            await asyncio.to_thread(
                self.supabase_service.save_temp_message,
                payload
            )
    
    async def _schedule_user_processing(self, user_id: str):
        """Agenda processamento com debounce."""
        await asyncio.sleep(self.DEBOUNCE_SECONDS)
        await self.process_debounced_messages(user_id)


__all__ = ["BaseChatbotService"]
