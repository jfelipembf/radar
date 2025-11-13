-- ESTRUTURA OTIMIZADA PARA RADAR - PRODUTOS E PREÇOS

-- Tabela principal de produtos
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setor VARCHAR(50) NOT NULL, -- autopecas, supermercado, farmacia, etc.
    comercio VARCHAR(100) NOT NULL, -- nome da loja
    produto VARCHAR(200) NOT NULL, -- nome do produto
    descricao TEXT, -- descrição completa
    marca VARCHAR(100), -- marca do produto
    unidade VARCHAR(50), -- 1L, unidade, kg, 500ml, etc.
    preco DECIMAL(10,2) NOT NULL, -- preço em R$
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Campos adicionais para IA
    categoria VARCHAR(100), -- categoria mais específica (ex: oleo_motor, filtro_ar)
    compatibilidade TEXT[], -- array de compatibilidades (ex: ['toyota_corolla', 'flex'])
    sku_loja VARCHAR(100), -- código interno da loja
    url_produto VARCHAR(500), -- link para o produto na loja
    disponivel BOOLEAN DEFAULT true, -- se está disponível
    promocao BOOLEAN DEFAULT false, -- se está em promoção

    -- Constraints
    CHECK (preco > 0),
    CHECK (setor IN ('autopecas', 'supermercado', 'farmacia', 'construcao', 'eletronicos', 'vestuario', 'outros'))
);

-- Índices para buscas rápidas da IA
CREATE INDEX idx_products_setor_produto ON products(setor, produto);
CREATE INDEX idx_products_comercio_preco ON products(comercio, preco);
CREATE INDEX idx_products_categoria ON products(categoria);
CREATE INDEX idx_products_atualizado_em ON products(atualizado_em DESC);
CREATE INDEX idx_products_preco ON products(preco);
CREATE INDEX idx_products_disponivel ON products(disponivel) WHERE disponivel = true;

-- Tabela de compatibilidades (opcional, para produtos específicos)
CREATE TABLE product_compatibilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    tipo VARCHAR(50), -- carro, moto, aparelho, etc.
    modelo TEXT[], -- ['toyota_corolla_2020', 'honda_civic_2019']
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
