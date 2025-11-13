#!/usr/bin/env python3
"""
Script específico para testar a detecção de produtos e busca no radar
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_product_detection():
    """Testa se a detecção de produtos está funcionando"""
    print("🧪 Testando detecção de produtos...\n")

    # Importar função de detecção
    from app.modules.ai_service.ai_service_domain import detect_product_query

    # Mensagens de teste
    test_messages = [
        "Ola, gostaria de saber o melhor local para comprar esse óleo Óleo 5W30 sintético",
        "Quanto custa filtro de ar para meu carro?",
        "Preciso de pastilhas de freio",
        "Onde comprar bateria de carro?",
        "Oi, tudo bem?",
        "Como está o tempo hoje?"
    ]

    print("📝 Testando detecção de produtos:\n")

    for message in test_messages:
        product = detect_product_query(message)
        status = "✅ DETECTADO" if product else "❌ NÃO DETECTADO"
        print(f"{status}: '{message[:50]}...' -> Produto: {product}")

    print("\n🎯 Testando busca no radar com mock...\n")

    # Testar com mock do radar
    class MockRadar:
        def compare_prices(self, product_name):
            return {
                "melhor_opcao": {
                    "loja": "Auto Peças Silva",
                    "produto": product_name,
                    "preco": 45.90,
                    "marca": "Castrol",
                    "unidade": "litro"
                },
                "comparacao": [
                    {"loja": "Auto Peças Silva", "preco": 45.90, "diferenca": 0},
                    {"loja": "Peças do Zé", "preco": 48.50, "diferenca": 2.60}
                ],
                "economia_total": {"valor": 2.60, "percentual": 5.4}
            }

    # Simular o fluxo completo de detecção + busca
    test_message = "Ola, gostaria de saber o melhor local para comprar esse óleo Óleo 5W30 sintético"
    radar = MockRadar()

    print(f"📨 Mensagem: '{test_message}'")

    # Passo 1: Detectar produto
    product = detect_product_query(test_message)
    print(f"🔍 Produto detectado: {product}")

    if product:
        # Passo 2: Buscar no radar
        result = radar.compare_prices(product)
        print(f"📊 Resultado da busca:")
        print(f"   🏪 Melhor opção: {result['melhor_opcao']['loja']}")
        print(f"   💵 Preço: R$ {result['melhor_opcao']['preco']:.2f}")
        print(f"   📈 Economia: R$ {result['economia_total']['valor']:.1f} ({result['economia_total']['percentual']:.1f}%)")

        # Passo 3: Formatar resposta
        from app.modules.ai_service.ai_service_functions import format_product_response
        formatted_response = format_product_response(result)
        print(f"\n📝 Resposta formatada:")
        print(formatted_response[:200] + "..." if len(formatted_response) > 200 else formatted_response)

    print("\n🎉 Teste de detecção de produtos concluído!")

if __name__ == "__main__":
    test_product_detection()
