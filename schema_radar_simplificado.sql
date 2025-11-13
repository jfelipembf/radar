-- ESTRUTURA SIMPLIFICADA PARA RADAR - FOCO NA IA
-- Versão otimizada para buscas rápidas da IA

-- Tabela principal de produtos (SIMPLIFICADA)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setor VARCHAR(50) NOT NULL, -- autopecas, supermercado, farmacia, etc.
    comercio VARCHAR(100) NOT NULL, -- nome da loja (DENORMALIZADO para buscas rápidas)
    produto VARCHAR(200) NOT NULL, -- nome do produto
    descricao TEXT, -- descrição completa
    marca VARCHAR(100), -- marca do produto
    unidade VARCHAR(50), -- 1L, unidade, kg, 500ml, etc.
    preco DECIMAL(10,2) NOT NULL, -- preço em R$
    categoria VARCHAR(100), -- categoria mais específica
    compatibilidade TEXT[], -- array de compatibilidades

    -- Campos para controle de acesso (simplificado)
    loja_id UUID, -- referência à loja (opcional para futuras expansões)
    criado_por VARCHAR(100), -- email do usuário que criou
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    disponivel BOOLEAN DEFAULT true,

    -- Constraints
    CHECK (preco > 0),
    CHECK (setor IN ('autopecas', 'supermercado', 'farmacia', 'construcao', 'eletronicos', 'vestuario', 'outros'))
);

-- Tabela de lojas (APENAS para autenticação futura)
CREATE TABLE lojas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(100) NOT NULL UNIQUE,
    api_key VARCHAR(100) UNIQUE,
    ativo BOOLEAN DEFAULT true
);

-- Tabela de usuários (MINIMAL para controle de acesso)
CREATE TABLE loja_usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loja_id UUID REFERENCES lojas(id),
    email VARCHAR(100) NOT NULL UNIQUE,
    papel VARCHAR(50) DEFAULT 'funcionario'
);

-- Índices ESSENCIAIS para IA
CREATE INDEX idx_products_setor_produto ON products(setor, produto);
CREATE INDEX idx_products_comercio ON products(comercio);
CREATE INDEX idx_products_categoria ON products(categoria);
CREATE INDEX idx_products_preco ON products(preco);
CREATE INDEX idx_products_disponivel ON products(disponivel) WHERE disponivel = true;
CREATE INDEX idx_products_loja_id ON products(loja_id);

-- Row Level Security SIMPLIFICADO
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- Política para CRUD da própria loja
CREATE POLICY "produtos_propria_loja" ON products
FOR ALL USING (
    loja_id IN (
        SELECT loja_id FROM loja_usuarios
        WHERE email = current_setting('app.current_user_email', TRUE)
    )
);

-- Política para LEITURA PÚBLICA (IA pode comparar)
CREATE POLICY "radar_leitura_publica" ON products
FOR SELECT USING (true);
