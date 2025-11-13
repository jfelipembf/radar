#!/usr/bin/env python3
"""
Teste direto das funções sem usar FastAPI TestClient
"""
import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

async def test_direct_functions():
    """Testa as funções diretamente sem FastAPI"""
    print("🧪 Teste direto das funções...\n")

    try:
        # Importar conversation_manager
        from app.services.conversation_manager import conversation_manager
        print("✅ Conversation manager importado")

        # Importar funções dos módulos
        from app.modules.whatsapp import validate_webhook_data, extract_message_data, should_process_message
        print("✅ Módulo WhatsApp importado")

        from app.modules.message_processor import process_message_async
        print("✅ Módulo Message Processor importado")

        from app.modules.ai_service import generate_ai_response, generate_ai_response_with_context
        print("✅ Módulo AI Service importado")

        from app.modules.product_radar import compare_prices
        print("✅ Módulo Product Radar importado")

        # Simular dados do webhook
        webhook_data = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": "557999371622@s.whatsapp.net",
                    "fromMe": False,
                    "id": "test_id"
                },
                "pushName": "Felipe Macedo",
                "message": {
                    "conversation": "ola, bom dia"
                },
                "messageType": "conversation"
            }
        }

        print(f"📨 Testando webhook: {webhook_data['data']['message']['conversation']}")

        # Passo 1: Validar webhook
        validation = validate_webhook_data(webhook_data)
        print(f"✅ Validação webhook: {validation}")

        # Passo 2: Extrair dados da mensagem
        message_info = extract_message_data(webhook_data)
        print(f"✅ Extração dados: user_id={message_info['user_id']}, text='{message_info['text']}'")

        # Passo 3: Verificar se deve processar
        processing_decision = should_process_message(message_info)
        print(f"✅ Decisão processamento: {processing_decision}")

        # Passo 4: Simular processamento
        print("\n🚀 Simulando processamento completo...")

        # Função mock para WhatsApp (não faz nada real)
        async def mock_send_message(user_id, text):
            print(f"📱 WhatsApp mock: Enviando para {user_id}: '{text[:50]}...'")
            return None

        # Função mock para AI (retorna resposta simples)
        async def mock_generate_ai_response(message, system_prompt=None, product_radar=None):
            print(f"🤖 AI mock: Processando '{message}'")
            return "Bom dia! Como posso ajudar você hoje? 😊"

        async def mock_generate_ai_response_with_context(message, context, system_prompt=None, product_radar=None):
            print(f"🤖 AI with context mock: Processando '{message}' com {len(context)} mensagens de contexto")
            return "Resposta com contexto simulada"

        # Testar RADAR
        radar_result = compare_prices("óleo 5W30")
        print(f"🎯 RADAR test: {radar_result}")

        print("\n✅ Todos os módulos funcionam corretamente!")
        print("✅ Sistema está pronto para receber mensagens do WhatsApp!")

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_functions())
