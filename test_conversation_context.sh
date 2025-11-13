#!/bin/bash

# Script de teste do sistema de contexto de conversa
# Testa primeira mensagem do dia, debounce e contexto

echo "🧪 TESTANDO SISTEMA DE CONTEXTO DE CONVERSA"
echo "=========================================="

# Testar primeira mensagem do dia
echo "1. Testando primeira mensagem do dia..."
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "key": {
        "remoteJid": "5511999999999@s.whatsapp.net",
        "fromMe": false
      },
      "message": {
        "conversation": "Olá, quero comprar um filtro de óleo"
      }
    }
  }'

echo -e "\n\n⏳ Aguardando 16 segundos para debounce..."
sleep 16

# Testar segunda mensagem (não deve ser primeira do dia)
echo -e "\n2. Testando segunda mensagem do mesmo usuário..."
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "key": {
        "remoteJid": "5511999999999@s.whatsapp.net",
        "fromMe": false
      },
      "message": {
        "conversation": "Qual o preço do filtro de ar?"
      }
    }
  }'

echo -e "\n\n✅ Testes concluídos!"
echo "Verifique os logs da aplicação para confirmar:"
echo "  - Mensagem de boas-vindas 'RADAR ATIVADO' na primeira mensagem"
echo "  - Debounce de 15 segundos funcionando"
echo "  - Contexto sendo mantido entre mensagens"
