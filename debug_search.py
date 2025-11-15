#!/usr/bin/env python3
"""
Script de debug para testar busca de produtos em produção
Execute: python3 debug_search.py
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.supabase_service import SupabaseService
from app.mcp.product_mcp_server import ProductMCPServer

async def test_search():
    """Testa a busca de produtos"""
    
    print("=" * 60)
    print("🔍 DEBUG - BUSCA DE PRODUTOS")
    print("=" * 60)
    
    try:
        # Inicializar serviços
        print("\n1️⃣ Inicializando Supabase...")
        supabase_service = SupabaseService()
        print("   ✅ Supabase conectado")
        
        print("\n2️⃣ Inicializando MCP Server...")
        mcp_server = ProductMCPServer(supabase_service)
        print("   ✅ MCP Server pronto")
        
        # Teste 1: Busca direta por keywords
        print("\n" + "=" * 60)
        print("📊 TESTE 1: Busca direta por keywords")
        print("=" * 60)
        
        test_keywords = ['heineken']
        print(f"\n🔎 Buscando: {test_keywords}")
        
        products = supabase_service.search_products_by_keywords(
            keywords=test_keywords,
            limit=5
        )
        
        print(f"\n✅ Encontrados: {len(products)} produtos")
        for i, p in enumerate(products, 1):
            print(f"   {i}. {p.get('name')} - R$ {p.get('price')} - {p.get('store', {}).get('name', 'N/A')}")
            print(f"      Keywords: {p.get('keywords', [])[:5]}...")
        
        # Teste 2: Busca em lote (como a IA faz)
        print("\n" + "=" * 60)
        print("📊 TESTE 2: Busca em lote (search_multiple_products)")
        print("=" * 60)
        
        test_products = [
            {'keywords': ['heineken'], 'quantity': 12}
        ]
        print(f"\n🔎 Buscando: {test_products}")
        
        result = await asyncio.to_thread(
            mcp_server.search_multiple_products,
            test_products
        )
        
        print(f"\n✅ Resultado:")
        print(f"   Success: {result.get('success')}")
        print(f"   Total encontrado: {result.get('total_found')}/{result.get('total_requested')}")
        
        if result.get('products'):
            print(f"\n   Produtos:")
            for i, p in enumerate(result['products'], 1):
                print(f"   {i}. {p.get('name')} - R$ {p.get('price')} - {p.get('store')}")
                print(f"      Quantidade: {p.get('quantity')}")
        else:
            print("   ❌ Nenhum produto retornado!")
            if 'error' in result:
                print(f"   Erro: {result['error']}")
        
        # Teste 3: Busca com erro de digitação
        print("\n" + "=" * 60)
        print("📊 TESTE 3: Busca com erro de digitação (hineken)")
        print("=" * 60)
        
        test_products_typo = [
            {'keywords': ['hineken'], 'quantity': 12}
        ]
        print(f"\n🔎 Buscando: {test_products_typo}")
        
        result_typo = await asyncio.to_thread(
            mcp_server.search_multiple_products,
            test_products_typo
        )
        
        print(f"\n✅ Resultado:")
        print(f"   Success: {result_typo.get('success')}")
        print(f"   Total encontrado: {result_typo.get('total_found')}/{result_typo.get('total_requested')}")
        
        if result_typo.get('products'):
            print(f"\n   Produtos:")
            for i, p in enumerate(result_typo['products'], 1):
                print(f"   {i}. {p.get('name')} - R$ {p.get('price')} - {p.get('store')}")
        else:
            print("   ❌ Nenhum produto retornado!")
        
        # Teste 4: Verificar keywords no banco
        print("\n" + "=" * 60)
        print("📊 TESTE 4: Verificar keywords no banco")
        print("=" * 60)
        
        print("\n🔎 Consultando produtos Heineken diretamente...")
        products_direct = supabase_service.get_products(
            search_terms=['heineken'],
            limit=3
        )
        
        print(f"\n✅ Encontrados: {len(products_direct)} produtos")
        for i, p in enumerate(products_direct, 1):
            print(f"\n   {i}. {p.get('name')}")
            print(f"      Preço: R$ {p.get('price')}")
            print(f"      Loja: {p.get('store', {}).get('name', 'N/A')}")
            print(f"      Keywords: {p.get('keywords', [])}")
        
        print("\n" + "=" * 60)
        print("✅ TESTES CONCLUÍDOS")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())
