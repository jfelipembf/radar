#!/bin/bash

# Script de teste direto do sistema de contexto
# Testa primeira mensagem e debounce

echo "🧪 TESTANDO SISTEMA DE CONTEXTO - TESTE DIRETO"
echo "==============================================="

echo "1. Testando primeira mensagem do dia..."
echo "   Enviando: 'Olá, quero um filtro de óleo'"
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "key": {
        "remoteJid": "5511999999999@s.whatsapp.net",
        "fromMe": false
      },
      "message": {
        "conversation": "Olá, quero um filtro de óleo"
      }
    }
  }' &
echo ""
echo "   ✅ Webhook chamado (processamento em background)"
echo ""

echo "2. Aguardando 3 segundos..."
sleep 3
echo ""

echo "3. Testando segunda mensagem (deve aguardar debounce)..."
echo "   Enviando: 'Qual o preço?'"
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "key": {
        "remoteJid": "5511999999999@s.whatsapp.net",
        "fromMe": false
      },
      "message": {
        "conversation": "Qual o preço?"
      }
    }
  }' &
echo ""
echo "   ⏱️  Debounce de 15 segundos iniciado"
echo ""

echo "4. Aguardando debounce completar..."
echo "   (Isso deve levar 15 segundos)"
sleep 16
echo ""

echo "✅ Teste concluído!"
echo ""
echo "📊 RESULTADOS ESPERADOS:"
echo "   - Primeira mensagem: boas-vindas + resposta imediata"
echo "   - Segunda mensagem: resposta após 15 segundos"
echo "   - Verificar logs da aplicação para confirmar"
