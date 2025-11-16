# 💳 MIGRATIONS PARA SISTEMA DE PAGAMENTOS

## 🎯 ESTRUTURA DE ASSINATURAS

### **Planos Sugeridos:**

```
┌─────────────────────────────────────────────────────────────┐
│ PLANO BÁSICO - R$ 49,90/mês                                 │
│ - Até 50 produtos                                           │
│ - Dashboard básico                                          │
│ - Suporte por email                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PLANO PROFISSIONAL - R$ 99,90/mês                          │
│ - Produtos ilimitados                                       │
│ - Dashboard avançado                                        │
│ - Relatórios detalhados                                     │
│ - Suporte prioritário                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PLANO ENTERPRISE - R$ 199,90/mês                           │
│ - Tudo do Profissional                                     │
│ - API dedicada                                              │
│ - Suporte 24/7                                              │
│ - Gerente de conta                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ MIGRATIONS SQL

### **MIGRATION 8: Criar tabela `subscription_plans`**

```sql
-- Planos de assinatura disponíveis
CREATE TABLE IF NOT EXISTS subscription_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  description TEXT,
  price_monthly DECIMAL(10,2) NOT NULL,
  price_yearly DECIMAL(10,2),
  max_products INTEGER,
  features JSONB,
  is_active BOOLEAN DEFAULT true,
  stripe_price_id TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Inserir planos iniciais
INSERT INTO subscription_plans (name, slug, price_monthly, price_yearly, max_products, features) VALUES
('Básico', 'basico', 49.90, 499.00, 50, '["Dashboard básico", "Até 50 produtos", "Suporte por email"]'::jsonb),
('Profissional', 'profissional', 99.90, 999.00, NULL, '["Produtos ilimitados", "Dashboard avançado", "Relatórios", "Suporte prioritário"]'::jsonb),
('Enterprise', 'enterprise', 199.90, 1999.00, NULL, '["Tudo do Profissional", "API dedicada", "Suporte 24/7", "Gerente de conta"]'::jsonb);

CREATE INDEX idx_subscription_plans_slug ON subscription_plans(slug);

COMMENT ON TABLE subscription_plans IS 'Planos de assinatura disponíveis';
COMMENT ON COLUMN subscription_plans.max_products IS 'NULL = ilimitado';
COMMENT ON COLUMN subscription_plans.stripe_price_id IS 'ID do preço no Stripe';
```

### **MIGRATION 9: Criar tabela `subscriptions`**

```sql
-- Assinaturas das lojas
CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  plan_id UUID NOT NULL REFERENCES subscription_plans(id),
  status TEXT NOT NULL DEFAULT 'trialing',
  
  -- Stripe
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  stripe_price_id TEXT,
  
  -- Datas
  trial_ends_at TIMESTAMP,
  current_period_start TIMESTAMP,
  current_period_end TIMESTAMP,
  cancelled_at TIMESTAMP,
  
  -- Pagamento
  payment_method TEXT, -- 'credit_card', 'pix', 'boleto'
  last_payment_at TIMESTAMP,
  last_payment_amount DECIMAL(10,2),
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT check_subscription_status 
  CHECK (status IN ('trialing', 'active', 'past_due', 'cancelled', 'unpaid'))
);

-- Índices
CREATE INDEX idx_subscriptions_store ON subscriptions(store_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_period_end ON subscriptions(current_period_end);

-- RLS
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Policy: Admins veem tudo
CREATE POLICY subscriptions_select_admin 
ON subscriptions FOR SELECT 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: Lojas veem apenas própria assinatura
CREATE POLICY subscriptions_select_store 
ON subscriptions FOR SELECT 
USING (store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid()));

COMMENT ON TABLE subscriptions IS 'Assinaturas ativas das lojas';
COMMENT ON COLUMN subscriptions.status IS 'trialing (teste), active (ativa), past_due (atrasada), cancelled (cancelada), unpaid (não paga)';
```

### **MIGRATION 10: Criar tabela `payments`**

```sql
-- Histórico de pagamentos
CREATE TABLE IF NOT EXISTS payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id UUID NOT NULL REFERENCES subscriptions(id),
  store_id UUID NOT NULL REFERENCES stores(id),
  
  -- Stripe
  stripe_payment_intent_id TEXT,
  stripe_invoice_id TEXT,
  
  -- Valores
  amount DECIMAL(10,2) NOT NULL,
  currency TEXT DEFAULT 'BRL',
  
  -- Status
  status TEXT NOT NULL DEFAULT 'pending',
  payment_method TEXT,
  
  -- Datas
  paid_at TIMESTAMP,
  refunded_at TIMESTAMP,
  
  -- Metadata
  metadata JSONB,
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT check_payment_status 
  CHECK (status IN ('pending', 'processing', 'succeeded', 'failed', 'refunded'))
);

-- Índices
CREATE INDEX idx_payments_subscription ON payments(subscription_id);
CREATE INDEX idx_payments_store ON payments(store_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created ON payments(created_at DESC);
CREATE INDEX idx_payments_stripe_intent ON payments(stripe_payment_intent_id);

-- RLS
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Policy: Admins veem tudo
CREATE POLICY payments_select_admin 
ON payments FOR SELECT 
USING (auth.uid() IN (SELECT id FROM admin_users));

-- Policy: Lojas veem apenas próprios pagamentos
CREATE POLICY payments_select_store 
ON payments FOR SELECT 
USING (store_id IN (SELECT store_id FROM store_users WHERE id = auth.uid()));

COMMENT ON TABLE payments IS 'Histórico de todos os pagamentos';
COMMENT ON COLUMN payments.status IS 'pending, processing, succeeded, failed, refunded';
```

### **MIGRATION 11: Atualizar tabela `stores`**

```sql
-- Adicionar campos de assinatura
ALTER TABLE stores
ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'inactive',
ADD COLUMN IF NOT EXISTS subscription_ends_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS is_trial BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP;

-- Índices
CREATE INDEX idx_stores_subscription_status ON stores(subscription_status);
CREATE INDEX idx_stores_subscription_ends ON stores(subscription_ends_at);

-- Constraint
ALTER TABLE stores
ADD CONSTRAINT check_store_subscription_status 
CHECK (subscription_status IN ('active', 'inactive', 'past_due', 'cancelled'));

COMMENT ON COLUMN stores.subscription_status IS 'Status da assinatura: active (pode usar), inactive (bloqueado), past_due (atrasado), cancelled (cancelado)';
COMMENT ON COLUMN stores.is_trial IS 'Se está em período de teste gratuito';
```

### **MIGRATION 12: Criar função para verificar acesso**

```sql
-- Função para verificar se loja pode acessar o sistema
CREATE OR REPLACE FUNCTION can_store_access(store_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM stores
    WHERE id = store_uuid
    AND (
      -- Assinatura ativa
      subscription_status = 'active'
      OR
      -- Em período de teste
      (is_trial = true AND trial_ends_at > NOW())
    )
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION can_store_access IS 'Verifica se loja tem acesso ao sistema (assinatura ativa ou trial)';

-- Usar em RLS policies
-- Exemplo:
-- CREATE POLICY products_insert_paid_store 
-- ON products FOR INSERT 
-- WITH CHECK (can_store_access(store_id));
```

### **MIGRATION 13: Criar tabela `webhook_events`**

```sql
-- Log de webhooks do Stripe
CREATE TABLE IF NOT EXISTS webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stripe_event_id TEXT UNIQUE NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  processed BOOLEAN DEFAULT false,
  processed_at TIMESTAMP,
  error TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_webhook_events_type ON webhook_events(event_type);
CREATE INDEX idx_webhook_events_processed ON webhook_events(processed);
CREATE INDEX idx_webhook_events_created ON webhook_events(created_at DESC);

COMMENT ON TABLE webhook_events IS 'Log de webhooks recebidos do Stripe';
```

---

## 🔄 FLUXO DE PAGAMENTO

### **1. Cadastro da Loja (Admin):**

```
Admin cria loja
    ↓
Sistema cria trial de 7 dias
    ↓
stores.is_trial = true
stores.trial_ends_at = NOW() + 7 days
stores.subscription_status = 'active'
    ↓
Loja pode usar o sistema
```

### **2. Fim do Trial:**

```
Trial expira (7 dias)
    ↓
Cron job verifica trials expirados
    ↓
stores.subscription_status = 'inactive'
    ↓
Loja não pode mais acessar
    ↓
Email: "Seu trial expirou. Assine agora!"
```

### **3. Loja Assina:**

```
Loja escolhe plano
    ↓
Redireciona para Stripe Checkout
    ↓
Cliente paga
    ↓
Stripe envia webhook
    ↓
Sistema processa webhook
    ↓
INSERT em subscriptions
INSERT em payments
UPDATE stores SET subscription_status = 'active'
    ↓
Loja pode usar o sistema
```

### **4. Renovação Automática:**

```
Stripe cobra automaticamente
    ↓
Webhook: invoice.payment_succeeded
    ↓
UPDATE subscriptions
INSERT em payments
UPDATE stores.subscription_ends_at
    ↓
Loja continua ativa
```

### **5. Pagamento Falha:**

```
Stripe tenta cobrar
    ↓
Pagamento falha
    ↓
Webhook: invoice.payment_failed
    ↓
UPDATE stores.subscription_status = 'past_due'
    ↓
Email: "Pagamento falhou. Atualize seu cartão"
    ↓
Após 3 tentativas (7 dias):
UPDATE stores.subscription_status = 'inactive'
    ↓
Loja bloqueada
```

---

## 🔒 PROTEÇÕES DE ACESSO

### **Middleware de Verificação:**

```typescript
// middleware.ts
export async function middleware(req: NextRequest) {
  // ... autenticação ...
  
  // Verificar se é rota de loja
  if (req.nextUrl.pathname.startsWith('/loja')) {
    const supabase = createMiddlewareClient({ req, res })
    
    // Buscar loja do usuário
    const { data: storeUser } = await supabase
      .from('store_users')
      .select('store:stores(subscription_status, trial_ends_at, is_trial)')
      .eq('id', session.user.id)
      .single()
    
    const store = storeUser?.store
    
    // Verificar se pode acessar
    const canAccess = 
      store?.subscription_status === 'active' ||
      (store?.is_trial && new Date(store.trial_ends_at) > new Date())
    
    if (!canAccess) {
      // Redirecionar para página de assinatura
      return NextResponse.redirect(new URL('/loja/assinar', req.url))
    }
  }
  
  return NextResponse.next()
}
```

### **RLS com Verificação de Pagamento:**

```sql
-- Produtos: apenas lojas com assinatura ativa podem inserir
CREATE POLICY products_insert_paid_only 
ON products FOR INSERT 
WITH CHECK (
  can_store_access(store_id)
);

-- Produtos: apenas lojas com assinatura ativa podem atualizar
CREATE POLICY products_update_paid_only 
ON products FOR UPDATE 
USING (
  can_store_access(store_id)
);
```

---

## 📊 DASHBOARD DE PAGAMENTOS (Admin)

### **Métricas:**
- 💰 MRR (Monthly Recurring Revenue)
- 📈 Crescimento de assinaturas
- 💳 Taxa de churn
- 🔄 Taxa de renovação
- ⚠️ Assinaturas em atraso
- 📊 Receita por plano

### **Queries:**

```sql
-- MRR (receita mensal recorrente)
SELECT 
  SUM(sp.price_monthly) as mrr,
  COUNT(*) as active_subscriptions
FROM subscriptions s
JOIN subscription_plans sp ON s.plan_id = sp.id
WHERE s.status = 'active';

-- Assinaturas por status
SELECT 
  status,
  COUNT(*) as count
FROM subscriptions
GROUP BY status;

-- Receita por plano
SELECT 
  sp.name,
  COUNT(s.id) as subscriptions,
  SUM(sp.price_monthly) as monthly_revenue
FROM subscriptions s
JOIN subscription_plans sp ON s.plan_id = sp.id
WHERE s.status = 'active'
GROUP BY sp.name;

-- Trials expirando nos próximos 3 dias
SELECT 
  st.name,
  st.email,
  st.trial_ends_at
FROM stores st
WHERE st.is_trial = true
AND st.trial_ends_at BETWEEN NOW() AND NOW() + INTERVAL '3 days'
ORDER BY st.trial_ends_at;
```

---

## 🚀 INTEGRAÇÃO COM STRIPE

### **Configuração Inicial:**

```bash
# Instalar SDK
npm install stripe @stripe/stripe-js

# Variáveis de ambiente
STRIPE_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

### **Criar Checkout Session:**

```typescript
// app/api/create-checkout/route.ts
import Stripe from 'stripe'
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(req: Request) {
  const { planId, storeId } = await req.json()
  
  // Buscar plano
  const { data: plan } = await supabase
    .from('subscription_plans')
    .select('*')
    .eq('id', planId)
    .single()
  
  // Criar checkout session
  const session = await stripe.checkout.sessions.create({
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{
      price: plan.stripe_price_id,
      quantity: 1,
    }],
    success_url: `${process.env.NEXT_PUBLIC_URL}/loja/dashboard?success=true`,
    cancel_url: `${process.env.NEXT_PUBLIC_URL}/loja/assinar?cancelled=true`,
    metadata: {
      store_id: storeId,
      plan_id: planId,
    }
  })
  
  return Response.json({ url: session.url })
}
```

### **Webhook Handler:**

```typescript
// app/api/webhooks/stripe/route.ts
import Stripe from 'stripe'
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(req: Request) {
  const body = await req.text()
  const sig = req.headers.get('stripe-signature')!
  
  let event: Stripe.Event
  
  try {
    event = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET!
    )
  } catch (err) {
    return Response.json({ error: 'Webhook signature verification failed' }, { status: 400 })
  }
  
  // Log webhook
  await supabase.from('webhook_events').insert({
    stripe_event_id: event.id,
    event_type: event.type,
    payload: event.data.object
  })
  
  // Processar evento
  switch (event.type) {
    case 'checkout.session.completed':
      await handleCheckoutCompleted(event.data.object)
      break
    
    case 'invoice.payment_succeeded':
      await handlePaymentSucceeded(event.data.object)
      break
    
    case 'invoice.payment_failed':
      await handlePaymentFailed(event.data.object)
      break
    
    case 'customer.subscription.deleted':
      await handleSubscriptionCancelled(event.data.object)
      break
  }
  
  return Response.json({ received: true })
}
```

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### **Fase 1: Estrutura (Agora)**
- [x] Criar migrations de pagamentos
- [x] Documentar fluxo
- [x] Planejar integração

### **Fase 2: Backend (Depois do MVP)**
- [ ] Configurar Stripe
- [ ] Criar API routes
- [ ] Implementar webhooks
- [ ] Criar cron jobs

### **Fase 3: Frontend (Depois do MVP)**
- [ ] Página de planos
- [ ] Checkout
- [ ] Dashboard de assinatura
- [ ] Gerenciar cartão

### **Fase 4: Testes**
- [ ] Testar trial
- [ ] Testar pagamento
- [ ] Testar renovação
- [ ] Testar falha de pagamento

---

## 🎯 RECOMENDAÇÃO FINAL

**AGORA:**
1. ✅ Executar migrations 8-13
2. ✅ Deixar estrutura pronta
3. ✅ Focar no MVP (cadastro de lojas e produtos)

**DEPOIS DO MVP:**
1. Configurar Stripe
2. Implementar checkout
3. Ativar webhooks
4. Testar fluxo completo

**A estrutura está pronta para quando você quiser ativar os pagamentos!**
