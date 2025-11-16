# 🗄️ ANÁLISE COMPLETA DO BANCO DE DADOS

## 📊 TABELAS EXISTENTES

### **1. stores (9 registros)**
```
Campos atuais:
- id (UUID)
- name (TEXT, UNIQUE)
- segment (TEXT)
- phone (TEXT)
- created_at (TIMESTAMP)

✅ JÁ TEM: id, name, segment, phone
❌ FALTANDO: email, status, address, logo_url, description, updated_at
```

### **2. products (133 registros)**
```
Campos atuais:
- id (UUID)
- store_id (UUID → stores.id)
- segment (TEXT)
- sector (TEXT)
- name (TEXT)
- description (TEXT)
- brand (TEXT)
- unit_label (TEXT)
- price (NUMERIC) ← PREÇO DE VENDA
- keywords (TEXT[])
- delivery_info (TEXT)
- store_phone (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

✅ JÁ TEM: price (venda), keywords, description
❌ FALTANDO: purchase_price, stock_quantity, status, category
```

### **3. clients (1 registro)**
```
Campos atuais:
- id (UUID)
- phone (VARCHAR, UNIQUE)
- name (VARCHAR)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

✅ ESTÁ OK - Não precisa alterar
```

### **4. conversation_context (3 registros)**
```
✅ ESTÁ OK - Sistema de chat
```

### **5. temporary_messages (0 registros)**
```
✅ ESTÁ OK - Sistema de chat
```

---

## 🔧 MIGRATIONS NECESSÁRIAS

### **MIGRATION 1: Atualizar `stores`**

```sql
-- Adicionar campos para sistema admin
ALTER TABLE stores
ADD COLUMN IF NOT EXISTS email TEXT UNIQUE,
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active',
ADD COLUMN IF NOT EXISTS address TEXT,
ADD COLUMN IF NOT EXISTS logo_url TEXT,
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Atualizar registros existentes
UPDATE stores SET updated_at = created_at WHERE updated_at IS NULL;

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_stores_segment ON stores(segment);
CREATE INDEX IF NOT EXISTS idx_stores_status ON stores(status);
CREATE INDEX IF NOT EXISTS idx_stores_email ON stores(email);

-- Adicionar constraints
ALTER TABLE stores
ADD CONSTRAINT check_store_status 
CHECK (status IN ('active', 'inactive', 'pending'));

COMMENT ON COLUMN stores.email IS 'Email da loja para login';
COMMENT ON COLUMN stores.status IS 'Status: active, inactive, pending';
COMMENT ON COLUMN stores.logo_url IS 'URL do logo no Supabase Storage';
```

### **MIGRATION 2: Atualizar `products`**

```sql
-- Adicionar campos de gestão
ALTER TABLE products
ADD COLUMN IF NOT EXISTS purchase_price DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS sale_price DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS stock_quantity INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active',
ADD COLUMN IF NOT EXISTS category TEXT;

-- Migrar price para sale_price (se ainda não foi feito)
UPDATE products SET sale_price = price WHERE sale_price IS NULL;

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_keywords ON products USING GIN(keywords);

-- Adicionar constraints
ALTER TABLE products
ADD CONSTRAINT check_product_status 
CHECK (status IN ('active', 'inactive', 'out_of_stock'));

ALTER TABLE products
ADD CONSTRAINT check_product_prices 
CHECK (sale_price >= 0 AND (purchase_price IS NULL OR purchase_price >= 0));

ALTER TABLE products
ADD CONSTRAINT check_product_stock 
CHECK (stock_quantity >= 0);

COMMENT ON COLUMN products.purchase_price IS 'Preço de compra (quanto a loja paga)';
COMMENT ON COLUMN products.sale_price IS 'Preço de venda (quanto a loja cobra)';
COMMENT ON COLUMN products.stock_quantity IS 'Quantidade em estoque';
COMMENT ON COLUMN products.status IS 'Status: active, inactive, out_of_stock';
```

### **MIGRATION 3: Criar `store_users`**

```sql
-- Tabela de usuários das lojas (autenticação)
CREATE TABLE IF NOT EXISTS store_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT DEFAULT 'admin',
  last_login TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT check_store_user_role 
  CHECK (role IN ('admin', 'operator', 'viewer'))
);

-- Índices
CREATE INDEX idx_store_users_store ON store_users(store_id);
CREATE INDEX idx_store_users_email ON store_users(email);

-- RLS (Row Level Security)
ALTER TABLE store_users ENABLE ROW LEVEL SECURITY;

-- Policy: usuário só vê dados da própria loja
CREATE POLICY store_users_select_own 
ON store_users FOR SELECT 
USING (
  auth.uid() = id 
  OR store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid())
);

COMMENT ON TABLE store_users IS 'Usuários das lojas para login no sistema';
COMMENT ON COLUMN store_users.role IS 'Papel: admin (total), operator (produtos), viewer (apenas visualizar)';
```

### **MIGRATION 4: Criar `admin_users`**

```sql
-- Tabela de usuários do sistema central
CREATE TABLE IF NOT EXISTS admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT DEFAULT 'admin',
  last_login TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT check_admin_user_role 
  CHECK (role IN ('super_admin', 'admin', 'analyst'))
);

-- Índices
CREATE INDEX idx_admin_users_email ON admin_users(email);

-- RLS
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

-- Policy: apenas admins podem ver
CREATE POLICY admin_users_select 
ON admin_users FOR SELECT 
USING (auth.uid() IN (SELECT id FROM admin_users));

COMMENT ON TABLE admin_users IS 'Usuários do sistema central (admin)';
COMMENT ON COLUMN admin_users.role IS 'super_admin (tudo), admin (gerenciar), analyst (apenas visualizar)';
```

### **MIGRATION 5: Criar `budgets`**

```sql
-- Tabela de orçamentos gerados pelo chatbot
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
  finalized_at TIMESTAMP,
  cancelled_at TIMESTAMP,
  cancellation_reason TEXT,
  
  CONSTRAINT check_budget_status 
  CHECK (status IN ('pending', 'finalized', 'cancelled'))
);

-- Índices
CREATE INDEX idx_budgets_customer ON budgets(customer_phone);
CREATE INDEX idx_budgets_store ON budgets(cheapest_store_id);
CREATE INDEX idx_budgets_status ON budgets(status);
CREATE INDEX idx_budgets_created ON budgets(created_at DESC);
CREATE INDEX idx_budgets_stores ON budgets USING GIN(stores);
CREATE INDEX idx_budgets_segment ON budgets(segment);

-- RLS
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;

-- Policy: admins veem tudo
CREATE POLICY budgets_select_admin 
ON budgets FOR SELECT 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: lojas veem apenas orçamentos que as incluem
CREATE POLICY budgets_select_store 
ON budgets FOR SELECT 
USING (
  cheapest_store_id IN (
    SELECT store_id FROM store_users WHERE id = auth.uid()
  )
);

COMMENT ON TABLE budgets IS 'Orçamentos gerados pelo chatbot';
COMMENT ON COLUMN budgets.stores IS 'JSON com array de lojas e produtos do orçamento';
COMMENT ON COLUMN budgets.status IS 'pending (aguardando), finalized (fechado), cancelled (cancelado)';
```

### **MIGRATION 6: Criar `activity_logs`**

```sql
-- Tabela de logs de atividade (auditoria)
CREATE TABLE IF NOT EXISTS activity_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  user_type TEXT NOT NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  details JSONB,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT check_user_type 
  CHECK (user_type IN ('admin', 'store')),
  
  CONSTRAINT check_entity_type 
  CHECK (entity_type IN ('store', 'product', 'budget', 'user'))
);

-- Índices
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_entity ON activity_logs(entity_type, entity_id);
CREATE INDEX idx_activity_logs_created ON activity_logs(created_at DESC);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);

-- RLS
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- Policy: admins veem tudo
CREATE POLICY activity_logs_select_admin 
ON activity_logs FOR SELECT 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: lojas veem apenas próprios logs
CREATE POLICY activity_logs_select_store 
ON activity_logs FOR SELECT 
USING (
  user_id IN (SELECT id FROM store_users WHERE id = auth.uid())
);

COMMENT ON TABLE activity_logs IS 'Logs de auditoria de todas as ações';
COMMENT ON COLUMN activity_logs.action IS 'Ação realizada: create, update, delete, login, etc';
```

### **MIGRATION 7: Atualizar RLS em `stores` e `products`**

```sql
-- STORES: Habilitar RLS
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;

-- Policy: Admins veem tudo
CREATE POLICY stores_select_admin 
ON stores FOR SELECT 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: Lojas veem apenas a própria
CREATE POLICY stores_select_store 
ON stores FOR SELECT 
USING (id IN (SELECT store_id FROM store_users WHERE id = auth.uid()));

-- Policy: Admins podem atualizar tudo
CREATE POLICY stores_update_admin 
ON stores FOR UPDATE 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: Lojas atualizam apenas a própria
CREATE POLICY stores_update_store 
ON stores FOR UPDATE 
USING (id IN (SELECT store_id FROM store_users WHERE id = auth.uid()));

-- PRODUCTS: Habilitar RLS
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- Policy: Admins veem tudo
CREATE POLICY products_select_admin 
ON products FOR SELECT 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: Lojas veem apenas próprios produtos
CREATE POLICY products_select_store 
ON products FOR SELECT 
USING (store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid()));

-- Policy: Lojas inserem apenas em sua própria store
CREATE POLICY products_insert_store 
ON products FOR INSERT 
WITH CHECK (store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid()));

-- Policy: Admins podem atualizar tudo
CREATE POLICY products_update_admin 
ON products FOR UPDATE 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: Lojas atualizam apenas próprios produtos
CREATE POLICY products_update_store 
ON products FOR UPDATE 
USING (store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid()));

-- Policy: Admins podem deletar tudo
CREATE POLICY products_delete_admin 
ON products FOR DELETE 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: Lojas deletam apenas próprios produtos
CREATE POLICY products_delete_store 
ON products FOR DELETE 
USING (store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid()));
```

---

## 📊 RESUMO DAS MUDANÇAS

### **Tabelas Atualizadas:**
1. ✅ `stores` - Adicionar email, status, address, logo_url, description
2. ✅ `products` - Adicionar purchase_price, sale_price, stock_quantity, status, category

### **Tabelas Novas:**
3. ✅ `store_users` - Autenticação das lojas
4. ✅ `admin_users` - Autenticação do sistema central
5. ✅ `budgets` - Orçamentos do chatbot
6. ✅ `activity_logs` - Auditoria

### **Segurança:**
7. ✅ RLS habilitado em todas as tabelas
8. ✅ Policies para admins e lojas
9. ✅ Constraints de validação

---

## 🎯 PRÓXIMOS PASSOS

1. **Executar migrations** no Supabase
2. **Criar usuário admin inicial**
3. **Testar RLS policies**
4. **Iniciar desenvolvimento do frontend**

**Quer que eu execute as migrations agora?**
