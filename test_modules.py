#!/usr/bin/env python3
"""
Script de teste para verificar se os módulos foram criados corretamente
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Testa se todos os módulos podem ser importados"""
    print("🧪 Testando imports dos módulos...")

    try:
        # Testar módulo whatsapp
        from app.modules.whatsapp import send_whatsapp_message, validate_webhook_data
        print("✅ Módulo whatsapp importado com sucesso")

        # Testar módulo message_processor
        from app.modules.message_processor import process_message_async, get_welcome_message
        print("✅ Módulo message_processor importado com sucesso")

        # Testar módulo product_radar (somente tipos e constantes)
        from app.modules.product_radar import RADAR_CONFIG, SEARCH_STATUS, PRODUCT_TYPES
        print("✅ Módulo product_radar importado com sucesso")

        # Pular ai_service por enquanto (depende de OpenAI API key)
        print("⚠️  Módulo ai_service pulado (requer OpenAI API key)")

        print("\n🎉 Módulos principais importados com sucesso!")
        return True

    except ImportError as e:
        print(f"❌ Erro ao importar módulo: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def test_functions():
    """Testa algumas funções básicas"""
    print("\n🧪 Testando funções básicas...")

    try:
        from app.modules.whatsapp import validate_webhook_data
        from app.modules.message_processor import determine_processing_strategy

        # Testar validação de webhook
        result = validate_webhook_data({'data': {}})
        print(f"✅ Validação de webhook: {result}")

        # Testar estratégia de processamento
        strategy = determine_processing_strategy(True, True)
        print(f"✅ Estratégia de processamento: {strategy}")

        print("🎉 Funções básicas testadas com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro ao testar funções: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        test_functions()
    else:
        sys.exit(1)
