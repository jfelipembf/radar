# 🤖 WhatsApp AI Automation - Sistema RADAR

Este projeto configura uma automação para WhatsApp usando **Evolution API** e **OpenAI**, com o sistema **RADAR** especializado em orçamentos e comparações de preços.

## 🎯 O que é o RADAR?

O **RADAR** é um sistema de inteligência artificial avançado que ajuda usuários a encontrarem os melhores preços e ofertas através de:

- ✅ **Análise inteligente** de produtos em múltiplas lojas
- ✅ **Comparação automática** de preços e condições
- ✅ **Recomendações personalizadas** baseadas em localização
- ✅ **Sugestões econômicas** e oportunidades de economia

## 🏪 Segmentos Suportados

- 🛒 **Supermercados**: Alimentos, bebidas, limpeza
- 🛍️ **Vestuário**: Roupas, calçados, acessórios
- 🏠 **Casa & Construção**: Materiais, ferramentas, decoração
- 💻 **Eletrônicos**: Celulares, TVs, computadores
- 🚗 **Auto Peças**: Peças, acessórios, manutenção
- 🏥 **Farmácias**: Medicamentos, higiene, beleza
- 🎯 **Outros**: Livros, brinquedos, esportes, etc.

## 📋 Como Funciona

### 1. **Recebimento de Mensagens**
- O Evolution API recebe mensagens do WhatsApp
- Sistema extrai o texto e identifica a intenção

### 2. **Processamento com RADAR**
- IA analisa a solicitação usando prompt especializado
- Busca informações em múltiplas fontes de dados
- Compara preços e condições

### 3. **Resposta Inteligente**
- Apresenta melhor opção encontrada
- Mostra comparação detalhada
- Fornece dicas práticas de economia

## 🚀 Instalação e Configuração

### Pré-requisitos
- Python 3.8+
- Conta Evolution API
- Chave OpenAI API

### 1. Instale as dependências:
```bash
pip install -r requirements.txt
```

### 2. Configure o arquivo `.env`:
```env
OPENAI_API_KEY=sua-chave-aqui
OPENAI_MODEL=gpt-4o-mini
EVOLUTION_API_URL=https://sua-api.evolution.com
EVOLUTION_API_KEY=sua-chave-api
EVOLUTION_INSTANCE=seu-instance
LOG_LEVEL=INFO
```

### 3. Execute o servidor:
```bash
python app/main.py
```

## 🧪 Teste Local

### Usando ngrok:
1. Instale ngrok: `brew install ngrok` (macOS)
2. Execute: `python app/main.py`
3. Novo terminal: `ngrok http 8000`
4. Configure webhook no Evolution API

### Teste direto:
```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{"event":"messages.upsert","data":{"key":{"remoteJid":"5511999999999@s.whatsapp.net","fromMe":false},"message":{"conversation":"Preciso de óleo para meu carro"}}}'
```

## 💾 Comandos de Git

### Comando Completo (Recomendado)
```bash
./git_commit_push.sh "feat: Implementar nova funcionalidade X"
```

### Comando Rápido
```bash
./git-push "update: Correções menores"
# ou apenas:
./git-push  # usa mensagem automática com data
```

### Comandos Individuais
```bash
git add .
git commit -m "sua mensagem"
git push origin HEAD
```

## 🧪 Scripts de Teste

### Teste dos Módulos
```bash
python3 test_modules.py
```

### Teste de Detecção de Produtos
```bash
python3 test_product_detection.py
```

### Teste do Fluxo Completo
```bash
python3 test_message_flow.py
```

## 📁 Estrutura do Projeto

```
├── app/
│   ├── main.py                 # Servidor FastAPI principal (80 linhas)
│   ├── modules/               # 🆕 Módulos especializados
│   │   ├── whatsapp/          # Integração Evolution API
│   │   │   ├── whatsapp_types.py      # Constantes WhatsApp
│   │   │   ├── whatsapp_domain.py     # Regras de negócio
│   │   │   ├── whatsapp_functions.py  # Envio de mensagens
│   │   │   └── whatsapp_db.py         # DB operations
│   │   ├── message_processor/ # Processamento de mensagens
│   │   │   ├── message_processor_types.py     # Configurações
│   │   │   ├── message_processor_domain.py    # Estratégias
│   │   │   ├── message_processor_functions.py # Processamento async
│   │   │   └── message_processor_db.py        # DB operations
│   │   ├── ai_service/        # Serviço OpenAI
│   │   │   ├── ai_service_types.py       # Configurações IA
│   │   │   ├── ai_service_domain.py      # Detecção produtos
│   │   │   ├── ai_service_functions.py   # Geração respostas
│   │   │   └── ai_service_db.py          # DB operations
│   │   └── product_radar/     # Sistema RADAR
│   │       ├── product_radar_types.py    # Configurações radar
│   │       ├── product_radar_domain.py   # Validações produtos
│   │       ├── product_radar_functions.py # Comparação preços
│   │       └── product_radar_db.py       # Queries Supabase
│   └── services/              # Serviços externos
│       └── conversation_manager.py  # Gerenciamento contexto
├── test_*.py                  # Scripts de teste
├── git_commit_push.sh         # Script completo de commit
├── git-push                   # Comando rápido de commit
├── requirements.txt           # Dependências Python
├── Dockerfile                # Container Docker
├── README.md                 # Esta documentação
└── .env                      # Variáveis ambiente (não versionado)
```

## 🎯 Exemplos de Uso

### Peças Automotivas:
**Usuário:** "Óleo de motor 5W30 para Toyota Corolla"

**RADAR responde:**
```
🎯 **ÓLEO DE MOTOR 5W30 - TOYOTA COROLLA**

💰 **MELHOR OPÇÃO: Auto Peças Central**
📍 Rua das Flores, 123 - Centro
💵 Preço: R$ 45,90 (1L)
📊 Economia: 15% mais barato

🔍 **COMPARAÇÃO:** Mecânica do Zé R$ 52,00
💡 **DICA:** Verifique se é óleo sintético
```

### Supermercados:
**Usuário:** "Leite integral mais barato"

**RADAR responde:**
```
🎯 **LEITE INTEGRAL (1L)**

💰 **MELHOR OPÇÃO: Super Econômico**
📍 Av. Brasil, 456
💵 Preço: R$ 4,89
📊 R$ 0,61 mais barato

💡 **DICA:** Compre em caixas de 6 unidades
```

## 🏗️ Deploy no Easypanel

1. Faça upload para repositório Git
2. No Easypanel: "Deploy from Git"
3. Configure variáveis de ambiente
4. Deploy automático com Dockerfile
5. Configure webhook no Evolution API

## ⚙️ Configurações do RADAR

O sistema usa configurações específicas em `app/config/radar_config.py`:

- **Modelo:** gpt-4o-mini (otimizado para custo)
- **Temperatura:** 0.7 (balanceado)
- **Tokens:** 2000 (respostas completas)
- **Segmentos:** 7 categorias principais

## 🔧 Personalização

### Modificar Prompt:
Edite `RADAR_PROMPT.md` e `app/config/radar_config.py`

### Adicionar Segmentos:
Atualize a lista de segmentos suportados na configuração

### Ajustar Comportamento:
Modifique parâmetros de temperatura e tokens conforme necessário

## 📊 Monitoramento

### Logs Disponíveis:
- Processamento de mensagens
- Respostas da OpenAI
- Status de envio WhatsApp
- Erros e exceções

### Verificação de Saúde:
```bash
curl https://sua-url/health  # Se implementado
```

## 🚨 Troubleshooting

### Problema: Mensagens não chegam
- ✅ Verifique webhook URL no Evolution API
- ✅ Confirme chaves de API válidas
- ✅ Verifique logs da aplicação

### Problema: Respostas incorretas
- ✅ Verifique prompt do RADAR
- ✅ Teste mensagens específicas
- ✅ Ajuste temperatura do modelo

### Problema: Timeout
- ✅ Aumente timeout da API
- ✅ Otimize prompt do sistema
- ✅ Considere modelo mais rápido

## 🎯 Roadmap

- [ ] Integração com bancos de dados de preços reais
- [ ] Suporte a localização GPS do usuário
- [ ] Histórico de conversas
- [ ] Notificações de ofertas
- [ ] API para integração com outras plataformas

---

## 🤝 Suporte

Para dúvidas sobre o sistema RADAR:
- 📖 Consulte `RADAR_PROMPT.md`
- 🧪 Teste com `RADAR_EXEMPLOS.md`
- 📝 Verifique logs da aplicação

**"RADAR: Encontre o melhor preço, economize com inteligência!"** 🛒💰
