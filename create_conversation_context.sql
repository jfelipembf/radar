-- Script para criar tabela de contexto de conversa e limpeza automática
-- Execute este script no Supabase SQL Editor

-- Criar tabela de contexto de conversa
CREATE TABLE IF NOT EXISTS conversation_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_conversation_user_time ON conversation_context(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_created_at ON conversation_context(created_at);

-- Função para limpeza automática de conversas antigas (TTL 24 horas)
CREATE OR REPLACE FUNCTION cleanup_old_conversations()
RETURNS void AS $$
BEGIN
    DELETE FROM conversation_context
    WHERE created_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Função para verificar primeira mensagem do dia
CREATE OR REPLACE FUNCTION is_first_message_today(user_phone VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    today_start TIMESTAMP := DATE_TRUNC('day', NOW() AT TIME ZONE 'America/Sao_Paulo');
BEGIN
    RETURN NOT EXISTS (
        SELECT 1 FROM conversation_context
        WHERE user_id = user_phone
        AND role = 'user'
        AND created_at >= today_start
    );
END;
$$ LANGUAGE plpgsql;

-- Função para obter contexto da conversa
CREATE OR REPLACE FUNCTION get_conversation_context(user_phone VARCHAR, limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    role VARCHAR(20),
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT cc.role, cc.content, cc.created_at
    FROM conversation_context cc
    WHERE cc.user_id = user_phone
    ORDER BY cc.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Função para salvar mensagem
CREATE OR REPLACE FUNCTION save_message_context(
    p_user_id VARCHAR,
    p_role VARCHAR,
    p_content TEXT
) RETURNS UUID AS $$
DECLARE
    new_id UUID;
BEGIN
    INSERT INTO conversation_context (user_id, role, content)
    VALUES (p_user_id, p_role, p_content)
    RETURNING id INTO new_id;

    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- Configurar limpeza automática (executa a cada hora)
-- NOTA: Para produção, considere usar pg_cron ou um job scheduler
-- Por enquanto, a limpeza pode ser feita manualmente ou via função

-- Exemplo de uso das funções:
/*
-- Verificar se é primeira mensagem do dia
SELECT is_first_message_today('5511999999999');

-- Salvar mensagem
SELECT save_message_context('5511999999999', 'user', 'Olá, quero um filtro de óleo');

-- Obter contexto
SELECT * FROM get_conversation_context('5511999999999', 5);

-- Limpar conversas antigas
SELECT cleanup_old_conversations();
*/
