# 🏗️ PLANO COMPLETO - SISTEMA DE ADMINISTRAÇÃO

## 📋 ÍNDICE
1. [Análise do Banco de Dados Atual](#análise-do-banco)
2. [Ajustes Necessários](#ajustes-necessários)
3. [Arquitetura de Segurança](#segurança)
4. [Estrutura do Projeto](#estrutura)
5. [Fluxo de Dados](#fluxo-de-dados)
6. [Implementação Passo a Passo](#implementação)

---

## 🗄️ ANÁLISE DO BANCO DE DADOS ATUAL

### **Verificar Tabelas Existentes:**

Primeiro, vou verificar a estrutura atual do banco:

```sql
-- Ver todas as tabelas
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Ver estrutura da tabela stores
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'stores';

-- Ver estrutura da tabela products
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'products';
```

---

## 🔧 AJUSTES NECESSÁRIOS NO BANCO

### **1. Atualizar tabela `stores`**

```sql
-- Adicionar campos para sistema admin
ALTER TABLE stores
ADD COLUMN IF NOT EXISTS email TEXT UNIQUE,
ADD COLUMN IF NOT EXISTS segment TEXT DEFAULT 'geral',
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active',
ADD COLUMN IF NOT EXISTS address TEXT,
ADD COLUMN IF NOT EXISTS logo_url TEXT,
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_stores_segment ON stores(segment);
CREATE INDEX IF NOT EXISTS idx_stores_status ON stores(status);
```

### **2. Atualizar tabela `products`**

```sql
-- Adicionar campos de preço de compra/venda
ALTER TABLE products
ADD COLUMN IF NOT EXISTS purchase_price DECIMAL(10,2), -- Preço de compra
ADD COLUMN IF NOT EXISTS sale_price DECIMAL(10,2),     -- Preço de venda
ADD COLUMN IF NOT EXISTS stock_quantity INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active',
ADD COLUMN IF NOT EXISTS category TEXT,
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Se a coluna 'price' já existe, renomear para 'sale_price'
-- ALTER TABLE products RENAME COLUMN price TO sale_price;

-- Índices
CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
```

### **3. Criar tabela `store_users` (Autenticação)**

```sql
CREATE TABLE IF NOT EXISTS store_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT DEFAULT 'admin',
  last_login TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_store_users_store ON store_users(store_id);
CREATE INDEX idx_store_users_email ON store_users(email);
```

### **4. Criar tabela `admin_users` (Sistema Central)**

```sql
CREATE TABLE IF NOT EXISTS admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT DEFAULT 'admin',
  last_login TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_admin_users_email ON admin_users(email);
```

### **5. Criar tabela `budgets` (Orçamentos)**

```sql
CREATE TABLE IF NOT EXISTS budgets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_phone TEXT NOT NULL,
  customer_name TEXT,
  stores JSONB NOT NULL,
  cheapest_store_id UUID REFERENCES stores(id),
  total_amount DECIMAL(10,2),
  status TEXT DEFAULT 'pending',
  segment TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  finalized_at TIMESTAMP
);

CREATE INDEX idx_budgets_customer ON budgets(customer_phone);
CREATE INDEX idx_budgets_store ON budgets(cheapest_store_id);
CREATE INDEX idx_budgets_status ON budgets(status);
CREATE INDEX idx_budgets_created ON budgets(created_at DESC);
```

---

## 🔒 ARQUITETURA DE SEGURANÇA

### **1. Row Level Security (RLS)**

```sql
-- Habilitar RLS em todas as tabelas
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE store_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;

-- STORES: Admins veem tudo, lojas veem apenas a própria
CREATE POLICY stores_select ON stores FOR SELECT USING (
  auth.uid() IN (SELECT id FROM admin_users)
  OR id IN (SELECT store_id FROM store_users WHERE id = auth.uid())
);

-- PRODUCTS: Lojas veem apenas próprios produtos
CREATE POLICY products_select ON products FOR SELECT USING (
  auth.uid() IN (SELECT id FROM admin_users)
  OR store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid())
);

CREATE POLICY products_insert ON products FOR INSERT WITH CHECK (
  store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid())
);

CREATE POLICY products_update ON products FOR UPDATE USING (
  auth.uid() IN (SELECT id FROM admin_users)
  OR store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid())
);
```

### **2. Proteções Implementadas**

✅ **SQL Injection:** Supabase usa prepared statements
✅ **XSS:** React escapa automaticamente
✅ **CSRF:** JWT tokens no header
✅ **Rate Limiting:** Implementar com Upstash Redis
✅ **Validação:** Zod schemas
✅ **Sanitização:** DOMPurify

---

## 🏗️ ESTRUTURA DO PROJETO

```
radar-admin/
├── app/
│   ├── (auth)/login/page.tsx
│   ├── admin/
│   │   ├── dashboard/page.tsx
│   │   ├── lojas/
│   │   │   ├── page.tsx (lista)
│   │   │   ├── nova/page.tsx
│   │   │   └── [id]/
│   │   │       ├── page.tsx (perfil)
│   │   │       └── editar/page.tsx
│   │   └── relatorios/page.tsx
│   └── loja/
│       ├── dashboard/page.tsx
│       ├── produtos/
│       │   ├── page.tsx (lista)
│       │   ├── novo/page.tsx
│       │   └── [id]/editar/page.tsx
│       └── orcamentos/page.tsx
├── components/
│   ├── admin/
│   ├── store/
│   └── ui/ (shadcn)
├── lib/
│   ├── supabase/
│   └── schemas/
└── middleware.ts
```

---

## 🔄 FLUXO DE DADOS

### **Sistema Central (Admin):**
```
1. Admin cria loja → INSERT stores + store_users
2. Admin visualiza dashboard → SELECT com agregações
3. Admin vê relatórios → SELECT com filtros
```

### **Sistema da Loja:**
```
1. Loja faz login → Supabase Auth
2. Loja cadastra produto → INSERT products (RLS valida)
3. Loja vê orçamentos → SELECT budgets WHERE store_id
4. Loja atualiza estoque → UPDATE products
```

### **Chatbot (Já Existente):**
```
1. Cliente pede orçamento → calculate_best_budget()
2. Sistema busca produtos → SELECT products WHERE keywords
3. Sistema cria orçamento → INSERT budgets
4. Cliente finaliza → UPDATE budgets + notifica loja
```

---

## 📝 IMPLEMENTAÇÃO PASSO A PASSO

### **FASE 1: Setup (Dia 1)**
1. ✅ Criar projeto Next.js com TypeScript
2. ✅ Instalar dependências (Supabase, shadcn/ui, Zod)
3. ✅ Executar migrations SQL
4. ✅ Configurar Supabase client/server

### **FASE 2: Autenticação (Dia 2)**
1. ✅ Criar página de login
2. ✅ Implementar middleware de proteção
3. ✅ Criar hook useAuth
4. ✅ Testar login admin e loja

### **FASE 3: Dashboard Admin (Dia 3-4)**
1. ✅ Criar dashboard com métricas
2. ✅ Implementar gráficos (Recharts)
3. ✅ Criar lista de lojas
4. ✅ Criar formulário de nova loja

### **FASE 4: Gestão de Lojas (Dia 5-6)**
1. ✅ Página de perfil da loja
2. ✅ Edição de loja
3. ✅ Ativar/desativar loja
4. ✅ Ver produtos da loja

### **FASE 5: Dashboard da Loja (Dia 7-8)**
1. ✅ Dashboard com métricas da loja
2. ✅ Lista de produtos
3. ✅ Cadastro de produtos
4. ✅ Edição de produtos
5. ✅ Ver orçamentos recebidos

### **FASE 6: Relatórios (Dia 9)**
1. ✅ Relatório de orçamentos
2. ✅ Relatório de lojas
3. ✅ Exportação (PDF/Excel)

### **FASE 7: Testes e Deploy (Dia 10)**
1. ✅ Testes de segurança
2. ✅ Testes de performance
3. ✅ Deploy Vercel
4. ✅ Configurar domínio

---

## 📊 PÁGINAS DETALHADAS

### **SISTEMA CENTRAL (Admin)**

#### **1. Dashboard**
- Cards: Total lojas, ativas, produtos, orçamentos
- Gráfico: Orçamentos por dia
- Tabela: Últimas atividades

#### **2. Lista de Lojas**
- Tabela com filtros
- Busca por nome
- Ações: ver, editar, ativar/desativar

#### **3. Nova Loja**
- Formulário: nome, email, telefone, segmento
- Gerar senha temporária
- Enviar credenciais por email

#### **4. Perfil da Loja**
- Informações completas
- Estatísticas
- Lista de produtos
- Histórico de orçamentos

---

### **SISTEMA DA LOJA (Store)**

#### **1. Dashboard da Loja**
- Cards: Total produtos, orçamentos recebidos, finalizados
- Gráfico: Orçamentos por dia
- Produtos mais solicitados

#### **2. Cadastro de Produtos**
- Nome do produto
- **Preço de compra** (quanto a loja paga)
- **Preço de venda** (quanto a loja cobra)
- Estoque
- Keywords (para busca do chatbot)
- Categoria
- Status (ativo/inativo)

#### **3. Lista de Produtos**
- Tabela com todos os produtos
- Filtros: categoria, status
- Ações: editar, ativar/desativar, excluir

#### **4. Orçamentos Recebidos**
- Lista de orçamentos que incluíram a loja
- Status: pendente, finalizado, cancelado
- Detalhes do cliente
- Produtos solicitados

---

## 🎯 PRÓXIMOS PASSOS

**Quer que eu:**
1. ✅ Execute as migrations SQL no Supabase?
2. ✅ Crie o projeto Next.js com a estrutura?
3. ✅ Implemente o sistema de autenticação?
4. ✅ Crie o dashboard admin primeiro?

**Qual fase você quer começar?**
