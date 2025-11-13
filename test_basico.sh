#!/bin/bash

# Teste básico do sistema funcionando
echo "🔧 TESTANDO SISTEMA RADAR + CONTEXTO"
echo "====================================="

echo "1. Testando webhook básico..."
RESPONSE=$(curl -s -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "key": {
        "remoteJid": "5511988889999@s.whatsapp.net",
        "fromMe": false
      },
      "message": {
        "conversation": "teste"
      }
    }
  }')

echo "   Status: $RESPONSE"
if [[ $RESPONSE == *"received"* ]]; then
    echo "   ✅ Webhook funcionando"
else
    echo "   ❌ Webhook com problema"
fi

echo ""
echo "2. Verificando se aplicação está rodando..."
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    echo "   ✅ Aplicação rodando"
else
    echo "   ❌ Aplicação não está rodando"
    echo "   Execute: python app/main.py"
fi

echo ""
echo "3. Teste manual:"
echo "   - Envie uma mensagem no WhatsApp: 'Olá'"
echo "   - Deve receber boas-vindas + resposta imediata"
echo "   - Aguarde alguns segundos e envie: 'quero filtro de óleo'"
echo "   - Deve aguardar 15 segundos e responder com comparação"
