#!/bin/bash
echo "🔍 Verificando arquivos no container..."

# Verificar se arquivos existem
echo "📁 Arquivos principais:"
ls -la /app/app/services/conversation_manager.py 2>/dev/null || echo "❌ conversation_manager.py não encontrado"
ls -la /app/app/modules/message_processor/message_processor_functions.py 2>/dev/null || echo "❌ message_processor_functions.py não encontrado"

echo ""
echo "🔧 Verificando configuração do debounce:"
grep -n "debounce_delay.*=" /app/app/services/conversation_manager.py 2>/dev/null || echo "❌ Configuração não encontrada"

echo ""
echo "📊 Status geral:"
echo "Total de arquivos Python: $(find /app -name "*.py" 2>/dev/null | wc -l)"
echo "Arquivos no app/: $(find /app/app -name "*.py" 2>/dev/null | wc -l)"

echo ""
echo "✅ Verificação concluída"
