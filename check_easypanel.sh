#!/bin/bash
echo "🔍 Verificação completa do EasyPanel"
echo "===================================="

echo "📁 Estrutura de arquivos:"
find /app -name "*.py" | grep -E "(conversation_manager|message_processor)" | head -5

echo ""
echo "🔧 Configuração do debounce:"
grep -A2 -B2 "debounce_delay.*=" /app/app/services/conversation_manager.py 2>/dev/null || echo "❌ Não encontrado"

echo ""
echo "📊 Estatísticas:"
echo "PID atual: $$"
echo "Tempo de atividade do container: $(ps -p 1 -o etime=)"
echo "Arquivos Python: $(find /app -name "*.py" 2>/dev/null | wc -l)"

echo ""
echo "✅ Verificação concluída - copie e execute este comando no terminal do EasyPanel"
