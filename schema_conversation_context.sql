-- Tabela para contexto de conversas com TTL de 24 horas
-- Mantém histórico para contexto da IA e controle de primeira mensagem do dia

CREATE TABLE conversation_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) NOT NULL, -- ID do usuário WhatsApp
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL, -- conteúdo da mensagem
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Índices para performance
    INDEX idx_conversation_user_time ON (user_id, created_at DESC),
    INDEX idx_conversation_created_at ON (created_at)
);

-- Função para limpar conversas antigas (TTL 24 horas)
CREATE OR REPLACE FUNCTION cleanup_old_conversations()
RETURNS void AS $$
BEGIN
    DELETE FROM conversation_context
    WHERE created_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Trigger para limpeza automática (executa a cada hora)
CREATE EXTENSION IF NOT EXISTS pg_cron;
SELECT cron.schedule('cleanup-conversations', '0 * * * *', 'SELECT cleanup_old_conversations();');

-- Função para verificar se é primeira mensagem do dia
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

-- Função para obter contexto da conversa (últimas 10 mensagens)
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

-- Função para salvar mensagem no contexto
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
