# 🔍 INSTRUÇÕES DE DEBUG EM PRODUÇÃO

## 📋 **COMANDOS PARA EXECUTAR NO SERVIDOR**

### **1. Testar Busca de Produtos**

```bash
# No servidor Evolution, execute:
cd /caminho/do/projeto
python3 debug_search.py
```

Este script vai testar:
- ✅ Conexão com Supabase
- ✅ Busca direta por keywords ('heineken')
- ✅ Busca em lote (como a IA faz)
- ✅ Busca com erro de digitação ('hineken')
- ✅ Keywords no banco de dados

---

### **2. Ver Logs em Tempo Real**

```bash
# Ver logs da aplicação
tail -f logs/app.log

# OU se usar PM2:
pm2 logs radar --lines 100

# OU se usar Docker:
docker logs -f container_name
```

---

### **3. Testar Endpoint Diretamente**

```bash
# Testar se a API está respondendo
curl http://localhost:8000/health

# Resultado esperado:
# {"status":"healthy","services":{"openai":true,"evolution":true,"supabase":true}}
```

---

### **4. Verificar Variáveis de Ambiente**

```bash
# Verificar se as variáveis estão configuradas
echo "SUPABASE_URL: $SUPABASE_URL"
echo "SUPABASE_SERVICE_ROLE_KEY: ${SUPABASE_SERVICE_ROLE_KEY:0:20}..."
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."
```

---

### **5. Reiniciar Aplicação**

```bash
# Se usar PM2:
pm2 restart radar

# Se usar systemd:
sudo systemctl restart radar

# Se usar Docker:
docker restart container_name
```

---

## 🐛 **COMANDOS DE DEBUG AVANÇADO**

### **Verificar Logs do OpenAI**

```bash
# Adicionar logging temporário
export LOG_LEVEL=DEBUG
python3 -m app.main
```

### **Testar MCP Tools Diretamente**

```python
# Execute no Python interativo:
python3

from app.services.supabase_service import SupabaseService
from app.mcp.product_mcp_server import ProductMCPServer

supabase = SupabaseService()
mcp = ProductMCPServer(supabase)

# Testar busca
result = mcp.search_multiple_products([
    {'keywords': ['heineken'], 'quantity': 12}
])

print(result)
```

---

## 📊 **O QUE VERIFICAR**

### **Se debug_search.py funcionar mas WhatsApp não:**

1. **Problema está na IA (OpenAI)**
   - IA não está chamando a ferramenta correta
   - IA não está extraindo keywords corretamente
   - Verificar logs do OpenAI

2. **Problema está no Evolution API**
   - Mensagens não estão chegando
   - Webhook não está configurado
   - Verificar logs do Evolution

### **Se debug_search.py NÃO funcionar:**

1. **Problema está no Supabase**
   - Conexão falhou
   - Keywords não foram atualizadas
   - Verificar credenciais

2. **Problema está no código**
   - Erro de importação
   - Erro de lógica
   - Verificar traceback

---

## 🔧 **FORÇAR ATUALIZAÇÃO DAS KEYWORDS**

Se as keywords não foram atualizadas no banco:

```sql
-- Execute no Supabase SQL Editor:
UPDATE products SET updated_at = updated_at;
```

Isso vai forçar o trigger a atualizar todas as keywords.

---

## 📝 **EXEMPLO DE OUTPUT ESPERADO**

```
============================================================
🔍 DEBUG - BUSCA DE PRODUTOS
============================================================

1️⃣ Inicializando Supabase...
   ✅ Supabase conectado

2️⃣ Inicializando MCP Server...
   ✅ MCP Server pronto

============================================================
📊 TESTE 1: Busca direta por keywords
============================================================

🔎 Buscando: ['heineken']

✅ Encontrados: 5 produtos
   1. Cerveja Heineken Long Neck - R$ 6.20 - Adega Premium
   2. Cerveja Heineken Long Neck - R$ 6.30 - Gelada Express
   ...

============================================================
📊 TESTE 2: Busca em lote (search_multiple_products)
============================================================

🔎 Buscando: [{'keywords': ['heineken'], 'quantity': 12}]

✅ Resultado:
   Success: True
   Total encontrado: 1/1

   Produtos:
   1. Cerveja Heineken Long Neck - R$ 6.20 - Adega Premium
      Quantidade: 12

============================================================
✅ TESTES CONCLUÍDOS
============================================================
```

---

## 🚨 **SE NADA FUNCIONAR**

Execute este comando para ver TODOS os logs:

```bash
python3 debug_search.py 2>&1 | tee debug_output.txt
```

Depois envie o arquivo `debug_output.txt` para análise.
