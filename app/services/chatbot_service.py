"""
Serviço de Chatbot usando MCP (Model Context Protocol)
IA decide tudo via function calling - código drasticamente simplificado
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.mcp import ProductMCPServer
from app.services.openai_service import OpenAIService
from app.services.supabase_service import SupabaseService
from app.services.evolution_service import EvolutionService
from app.utils.parsers import _consolidate_temp_messages, _latest_user_content
from app.utils.formatters import _sort_key

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Serviço de chatbot orientado por IA usando MCP.
    A IA decide autonomamente quais ferramentas usar via function calling.
    """
    
    def __init__(
        self,
        openai_service: OpenAIService,
        supabase_service: SupabaseService,
        evolution_service: EvolutionService
    ):
        self.openai_service = openai_service
        self.supabase_service = supabase_service
        self.evolution_service = evolution_service
        
        # Inicializar MCP Server
        self.mcp_server = ProductMCPServer(supabase_service)
        self.tools = self.mcp_server.get_tools_schema()
        
        logger.info(f"ChatbotService inicializado com MCP ({len(self.tools)} ferramentas)")
    
    async def process_message(self, user_id: str, text: str, message_data: dict) -> str:
        """
        Processa mensagem do usuário usando IA + MCP.
        
        Args:
            user_id: ID do usuário
            text: Mensagem do usuário
            message_data: Dados da mensagem
            
        Returns:
            Status do processamento
        """
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
        
        # Preparar mensagens para a IA
        messages = [
            {
                "role": "system",
                "content": """Você é um assistente de vendas de materiais de construção.

Você tem acesso a ferramentas para:
- search_products: buscar produtos no catálogo
- get_product_variations: ver variações disponíveis (tipos, tamanhos, etc)
- get_cheapest_product: encontrar o produto mais barato
- calculate_best_budget: calcular melhor orçamento agrupando por loja
- finalize_purchase: finalizar compra (quando usuário escolher opção 1)

INSTRUÇÕES:
1. Quando o usuário pedir um produto, use search_products
2. Se o usuário não especificar tipo/tamanho, use get_product_variations para mostrar opções
3. Quando o usuário escolher, use get_cheapest_product para adicionar ao orçamento
4. IMPORTANTE: Mantenha uma lista de todos os produtos adicionados
5. Ao final, use calculate_best_budget com TODOS os produtos para agrupar por loja
6. Mostre a loja mais barata e os totais de todas as lojas
7. Sempre confirme o que foi adicionado

FORMATO DO ORÇAMENTO FINAL:
Após adicionar todos os produtos, use calculate_best_budget e mostre:
- Lista de produtos adicionados
- Total por loja
- Loja mais barata destacada
- Opções: 1️⃣ Finalizar | 2️⃣ Ver detalhes | 3️⃣ Ver todas lojas

EXEMPLO:
Usuário: "preciso de cimento"
Você: [usa get_product_variations(category="cimento")]
Resposta: "Temos CP-II, CP-III e CP-V. Qual você prefere?"

Usuário: "CP-II"
Você: [usa get_cheapest_product(category="cimento", specification="CP-II")]
Você: [guarda produto na lista]
Resposta: "✅ Adicionei Cimento CP-II 50kg por R$ 32,00"

Usuário: "pronto"
Você: [usa calculate_best_budget(products=[...])]
Resposta: Mostra orçamento completo com totais por loja

Usuário: "1" (finalizar)
Você: [usa finalize_purchase(store_name="...", products=[...], total=X, customer_id="...")]
Resposta: Mostra mensagem de confirmação com link WhatsApp
"""
            }
        ] + history
        
        # Processar com MCP (pode ter múltiplas iterações)
        response_text = await self._process_with_mcp(messages)
        
        # Limpar e salvar
        await self._cleanup_and_save(user_id, temp_messages, consolidated, response_text)
        
        # Enviar resposta
        await self._send_whatsapp_message(user_id, response_text)
        await self._update_presence(user_id, "paused")
        
        return response_text
    
    async def _process_with_mcp(self, messages: List[Dict[str, str]]) -> str:
        """
        Processa mensagens com MCP, permitindo múltiplas chamadas de ferramentas.
        """
        max_iterations = 5  # Prevenir loops infinitos
        iteration = 0
        
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
                
                logger.info(f"Executando: {tool_name}({arguments})")
                
                # Executar via MCP
                result = await asyncio.to_thread(
                    self.mcp_server.execute_tool,
                    tool_name,
                    arguments
                )
                
                logger.info(f"Resultado: {result.get('success', False)}")
                
                # Adicionar resultado
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            
            # Continuar loop - IA pode usar mais ferramentas ou gerar resposta final
        
        # Se chegou aqui, atingiu max_iterations
        logger.warning(f"Atingiu max_iterations ({max_iterations})")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."
    
    async def _build_message_history(self, user_id: str) -> List[Dict[str, str]]:
        """Constrói histórico de mensagens."""
        HISTORY_LIMIT = 40
        
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
    
    async def _cleanup_and_save(
        self,
        user_id: str,
        temp_messages: List[dict],
        consolidated: Optional[Dict[str, str]],
        response_text: str
    ):
        """Limpa mensagens temporárias e salva."""
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
        
        # Salvar resposta
        await self._log_message(user_id, response_text, role="assistant")
        
        # Limpar temporárias
        await asyncio.to_thread(self.supabase_service.delete_temp_messages, temp_ids)
    
    async def _maybe_send_daily_greeting(self, user_id: str):
        """Envia saudação diária se necessário."""
        if not self.supabase_service or not user_id:
            return
        
        try:
            latest_message = await asyncio.to_thread(
                self.supabase_service.get_latest_message, 
                user_id
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
        """Agenda processamento com debounce."""
        # Typing indicator
        await self._update_presence(user_id, "composing", 20000)
        
        # Debounce
        await asyncio.sleep(10)
        
        # Processar
        await self._update_presence(user_id, "paused")
        await self.process_debounced_messages(user_id)
    
    async def _log_message(
        self, 
        user_id: str, 
        content: str, 
        role: str, 
        created_at: Optional[str] = None
    ):
        """Salva mensagem no Supabase."""
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
            logger.error(f"Erro ao salvar mensagem: {exc}")
    
    async def _send_whatsapp_message(self, user_id: str, text: str):
        """Envia mensagem via WhatsApp."""
        try:
            await asyncio.to_thread(self.evolution_service.send_message, user_id, text)
        except Exception as exc:
            logger.error(f"Erro ao enviar WhatsApp: {exc}")
    
    async def _update_presence(
        self, 
        user_id: str, 
        presence: str, 
        delay_ms: Optional[int] = None
    ):
        """Atualiza presença no WhatsApp."""
        try:
            await asyncio.to_thread(
                self.evolution_service.send_presence, 
                user_id, 
                presence, 
                delay_ms
            )
        except Exception as exc:
            logger.error(f"Erro ao atualizar presença: {exc}")


__all__ = ["ChatbotService"]
