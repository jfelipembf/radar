#!/usr/bin/env python3
"""
Script para testar o processamento de mensagens simulando o webhook
"""
import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock das APIs para teste
class MockConversationManager:
    async def process_incoming_message(self, user_id, text):
        print(f"📝 Conversation Manager: Processando mensagem '{text}' do usuário {user_id}")
        return True, []  # Simula primeira mensagem do dia

    async def process_outgoing_message(self, user_id, response_text):
        print(f"💬 Conversation Manager: Salvando resposta '{response_text[:50]}...' para {user_id}")

    async def get_conversation_context(self, user_id, limit=10):
        print(f"📚 Conversation Manager: Buscando contexto para {user_id}")
        return []

class MockWhatsappService:
    async def send_whatsapp_message(self, user_id, text):
        print(f"📱 WhatsApp: Enviando mensagem para {user_id}: '{text[:100]}...'")

class MockProductRadar:
    def compare_prices(self, product_name):
        print(f"🎯 Product Radar: Buscando '{product_name}'")
        # Simula resultado de busca
        return {
            "melhor_opcao": {
                "loja": "Auto Peças Silva",
                "produto": "Óleo 5W30 Sintético",
                "preco": 45.90,
                "marca": "Castrol",
                "unidade": "litro"
            },
            "comparacao": [
                {"loja": "Auto Peças Silva", "preco": 45.90, "diferenca": 0},
                {"loja": "Peças do Zé", "preco": 48.50, "diferenca": 2.60},
                {"loja": "Auto Center", "preco": 52.00, "diferenca": 6.10}
            ],
            "economia_total": {"valor": 6.10, "percentual": 11.8}
        }

class MockAIService:
    async def generate_ai_response(self, message, system_prompt=None, product_radar=None):
        print(f"🤖 AI Service: Gerando resposta sem contexto para '{message[:50]}...'")
        return "Resposta simulada da IA sem contexto"

    async def generate_ai_response_with_context(self, message, context_messages, system_prompt=None, product_radar=None):
        print(f"🤖 AI Service: Gerando resposta com contexto para '{message[:50]}...'")
        return "Resposta simulada da IA com contexto"

async def test_message_processing():
    """Testa o processamento de uma mensagem específica"""
    print("🧪 Iniciando teste de processamento de mensagens...\n")

    # Importar o módulo de processamento
    from app.modules.message_processor import process_message_async

    # Criar mocks
    conversation_manager = MockConversationManager()
    whatsapp_service = {'send_whatsapp_message': MockWhatsappService().send_whatsapp_message}
    ai_service = {
        'generate_ai_response': MockAIService().generate_ai_response,
        'generate_ai_response_with_context': MockAIService().generate_ai_response_with_context
    }
    product_radar = {'compare_prices': MockProductRadar().compare_prices}

    # Mensagem de teste
    user_id = "5511999999999"
    message = "Ola, gosatria de saber o melhor local para comprar esse oleto Óleo 5W30 sintético"
    system_prompt = "Você é um assistente virtual amigável que conversa com o usuário pelo WhatsApp. Responda de forma breve, natural e útil."

    print(f"📨 Testando mensagem: '{message}'\n")

    # Processar mensagem
    result = await process_message_async(
        user_id=user_id,
        text=message,
        conversation_manager=conversation_manager,
        ai_service=ai_service,
        whatsapp_service=whatsapp_service,
        system_prompt=system_prompt,
        product_radar=product_radar
    )

    print(f"\n✅ Resultado do processamento: {result}")
    print("\n🎉 Teste concluído!")

if __name__ == "__main__":
    asyncio.run(test_message_processing())
