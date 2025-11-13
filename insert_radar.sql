-- EXEMPLO DE INSERÇÃO DOS DADOS DO USUÁRIO

INSERT INTO products (setor, comercio, produto, descricao, marca, unidade, preco, categoria, compatibilidade, disponivel) VALUES
-- Óleo 5W30
('autopecas', 'Auto Peças Macedo', 'Óleo 5W30 sintético', 'Óleo de motor 5W30 totalmente sintético para carros flex', 'Marca X', '1L', 44.00, 'oleo_motor', ARRAY['toyota_corolla', 'honda_civic', 'carros_flex'], true),

-- Pastilha de freio
('autopecas', 'Auto Peças Macedo', 'Pastilha de freio dianteira', 'Pastilha de freio dianteira para Gol G5', 'Marca Y', 'jogo', 43.00, 'freios', ARRAY['volkswagen_gol_g5'], true),

-- Fluido de freio
('autopecas', 'Auto Peças Macedo', 'Fluido de freio DOT 4', 'Fluido de freio DOT 4 para sistema hidráulico', 'Marca Z', '500ml', 53.00, 'freios', ARRAY['sistema_hidraulico_geral'], true),

-- Filtro de óleo
('autopecas', 'Auto Peças Macedo', 'Filtro de óleo', 'Filtro de óleo para motor 1.0 popular', 'Marca X', 'unidade', 39.00, 'filtros', ARRAY['motor_1_0_popular'], true),

-- Filtro de ar
('autopecas', 'Auto Peças Macedo', 'Filtro de ar', 'Filtro de ar para Onix 1.0', 'Marca Y', 'unidade', 39.00, 'filtros', ARRAY['chevrolet_onix_1_0'], true),

-- Lâmpada H7
('autopecas', 'Auto Peças Macedo', 'Lâmpada H7', 'Lâmpada de farol H7 55W', 'Genérica', 'unidade', 19.00, 'iluminacao', ARRAY['farol_h7'], true),

-- Aditivo para radiador
('autopecas', 'Auto Peças Macedo', 'Aditivo para radiador', 'Aditivo pronto uso para sistema de arrefecimento', 'Marca Z', '1L', 34.00, 'arrefecimento', ARRAY['sistema_arrefecimento'], true),

-- Palheta limpador
('autopecas', 'Auto Peças Macedo', 'Palheta limpador 16"', 'Palheta de limpador de para-brisa 16 polegadas', 'Marca X', 'unidade', 27.00, 'limpadores', ARRAY['para_brisa_16_polegadas'], true),

-- Bateria 60Ah
('autopecas', 'Auto Peças Macedo', 'Bateria 60Ah', 'Bateria automotiva 60Ah 12V selada', 'Marca Y', 'unidade', 549.00, 'baterias', ARRAY['12v_60ah'], true),

-- Correia dentada
('autopecas', 'Auto Peças Macedo', 'Correia dentada', 'Correia dentada para HB20 1.0', 'Marca Z', 'unidade', 119.00, 'transmissao', ARRAY['hyundai_hb20_1_0'], true);

-- Atualizar timestamp para 07/11/2025
UPDATE products SET atualizado_em = '2025-11-07 00:00:00+00' WHERE comercio = 'Auto Peças Macedo';
