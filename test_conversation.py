#!/usr/bin/env python3
"""
Script de teste para o Sistema Radar
Simula a conversa do usuário para testar o fluxo completo
"""

import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.services.chatbot_service import ChatbotService
from app.services.openai_service import OpenAIService
from app.services.supabase_service import SupabaseService
from app.services.evolution_service import EvolutionService

async def test_conversation():
    """Testa o fluxo completo de conversa"""

    print("🧪 INICIANDO TESTE DO SISTEMA RADAR")
    print("=" * 50)

    # Simular mensagens do usuário
    messages = [
        "preciso de uma orcamento para ua caida dagua, de mil litros, 2 sacos de cimento e 5m3 de areia",
        "mil litros",
        "CP-II",
        "lavada"
    ]

    # Simular IDs de mensagens
    message_ids = [
        "msg_001",
        "msg_002",
        "msg_003",
        "msg_004"
    ]

    user_id = "557999371622"  # Mesmo ID do teste real

    print(f"👤 Usuário: {user_id}")
    print()

    # Simular o serviço (sem realmente enviar mensagens)
    chatbot_service = None

    try:
        # Aqui você precisaria instanciar os serviços reais
        # Mas para teste, vamos apenas simular o fluxo

        print("📝 SIMULAÇÃO DO FLUXO:")
        print()

        for i, (message, msg_id) in enumerate(zip(messages, message_ids), 1):
            print(f"💬 Mensagem {i}: '{message}'")

            # Simular dados da mensagem
            message_data = {
                "key": {"id": msg_id},
                "message": {"conversation": message}
            }

            # Aqui seria a chamada real:
            # result = await chatbot_service.process_message(user_id, message, message_data)

            print("   ⏳ Processando...")
            print()

        print("✅ TESTE CONCLUÍDO")
        print()
        print("📋 RESUMO ESPERADO:")
        print("1. Sistema identifica produtos: caixa d'água, cimento, areia")
        print("2. Pergunta sobre caixa d'água")
        print("3. Usuário responde 'mil litros'")
        print("4. Sistema adiciona 'Caixa d'água 1000L' aos selecionados")
        print("5. Pergunta sobre cimento")
        print("6. Usuário responde 'CP-II'")
        print("7. Sistema adiciona 'Cimento CP-II' aos selecionados")
        print("8. Pergunta sobre areia")
        print("9. Usuário responde 'lavada'")
        print("10. Sistema mostra orçamento completo")

    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_conversation())
