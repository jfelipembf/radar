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

## 📁 Estrutura do Projeto

```
├── app/
│   ├── main.py              # Aplicação principal
│   └── config/
│       └── radar_config.py  # Configurações do RADAR
├── RADAR_PROMPT.md          # Prompt detalhado do sistema
├── RADAR_EXEMPLOS.md        # Exemplos de uso
├── requirements.txt         # Dependências
├── Dockerfile              # Container
└── README.md              # Esta documentação
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
