#!/usr/bin/env python3
"""
Teste completo do debounce simulando servidor real
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

async def simulate_server_flow():
    """Simula exatamente o fluxo do servidor FastAPI"""
    print("🚀 Simulação completa do fluxo do servidor FastAPI\n")

    # Importações (como no main.py)
    from app.services.conversation_manager import conversation_manager
    from app.modules.message_processor import process_message_async

    # Configurar debounce para 3 segundos (igual ao servidor)
    conversation_manager.debounce_delay = 3

    # Mock services (iguais aos do servidor)
    async def mock_generate_ai_response_with_context(*args, **kwargs):
        return f"🤖 Resposta simulada com contexto para: '{kwargs.get('latest_message', {}).get('content', 'N/A')[:30]}...'"

    async def mock_generate_ai_response(*args, **kwargs):
        return "🤖 Resposta simples simulada"

    async def mock_send_whatsapp_message(user, msg):
        print(f"📱 WhatsApp → {user}: {msg[:80]}...")

    ai_service = {
        'generate_ai_response_with_context': mock_generate_ai_response_with_context,
        'generate_ai_response': mock_generate_ai_response
    }

    whatsapp_service = {
        'send_whatsapp_message': mock_send_whatsapp_message
    }

    product_radar = {
        'compare_prices': lambda query: {'resultado': f"Preços simulados para: {query}"}
    }

    print(f"⚙️ Configuração: debounce_delay = {conversation_manager.debounce_delay}s\n")

    # Simular recebimento de webhook (igual ao servidor)
    user_id = "557999371622"

    print("📨 Simulando webhook recebido...")
    print("1️⃣ Processando mensagem 'ola'...")

    start_time = datetime.now()
    print(f"🕐 Início: {start_time.strftime('%H:%M:%S')}")

    # Chamar process_message_async (igual ao servidor)
    await process_message_async(
        user_id=user_id,
        text="ola",
        conversation_manager=conversation_manager,
        ai_service=ai_service,
        whatsapp_service=whatsapp_service,
        system_prompt="Você é um assistente virtual amigável",
        product_radar=product_radar
    )

    print("⏳ Aguardando debounce completar...")

    # Aguardar tempo suficiente para o debounce (3s + margem)
    await asyncio.sleep(5)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"🕐 Fim: {end_time.strftime('%H:%M:%S')}")
    print(f"⏱️ Duração total: {duration:.1f} segundos")

    if duration >= 3:
        print("✅ SUCESSO: Debounce esperou o tempo necessário!")
    else:
        print("❌ FALHA: Debounce não esperou tempo suficiente!")

    # Verificar estado final
    context = await conversation_manager.get_conversation_context(user_id)
    print(f"📊 Estado final: {len(context)} mensagens salvas")

    # Verificar se há tarefas ativas
    active_tasks = len(conversation_manager.active_conversations)
    print(f"🎯 Conversas ativas: {active_tasks}")

if __name__ == "__main__":
    print("🧪 Teste: Simulação completa do debounce no servidor")
    print("=" * 50)

    asyncio.run(simulate_server_flow())

    print("\n🏁 Teste concluído!")
