#!/bin/bash

# Script para commit e push das mudanças do projeto Painel Swim
# Uso: ./git_commit_push.sh "mensagem do commit"

if [ $# -eq 0 ]; then
    echo "❌ Erro: Você deve fornecer uma mensagem de commit"
    echo "Uso: ./git_commit_push.sh \"Sua mensagem de commit\""
    exit 1
fi

COMMIT_MESSAGE="$1"

echo "🚀 Iniciando commit e push..."
echo "📝 Mensagem: $COMMIT_MESSAGE"
echo

# Verificar se estamos em um repositório git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Erro: Não estamos em um repositório git"
    exit 1
fi

# Verificar status do repositório
echo "📊 Status atual do repositório:"
git status --porcelain
echo

# Adicionar todos os arquivos
echo "📦 Adicionando arquivos..."
git add .
echo "✅ Arquivos adicionados"
echo

# Fazer commit
echo "💾 Fazendo commit..."
if git commit -m "$COMMIT_MESSAGE"; then
    echo "✅ Commit realizado com sucesso"
    echo

    # Fazer push
    echo "⬆️  Fazendo push..."
    if git push origin HEAD; then
        echo "✅ Push realizado com sucesso!"
        echo
        echo "🎉 Todas as operações concluídas!"
        echo "📋 Resumo:"
        git log --oneline -5
    else
        echo "❌ Erro no push. Verifique sua conexão e permissões."
        exit 1
    fi
else
    echo "❌ Erro no commit. Verifique se há mudanças para commitar."
    exit 1
fi
