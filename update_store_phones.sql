-- Atualizar todos os telefones das lojas para 79999371611
-- Execute este script no SQL Editor do Supabase

UPDATE material_construcao
SET store_phone = '79999371611'
WHERE store_phone IS NOT NULL AND store_phone != '';

-- Verificar se a atualização foi feita
SELECT DISTINCT store->>'name' as store_name, store_phone
FROM material_construcao
WHERE store_phone IS NOT NULL
ORDER BY store_name;
