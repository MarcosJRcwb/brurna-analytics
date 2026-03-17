-- migrations_v2.sql
-- Execute este SQL no banco de dados ANTES de rodar o processamento
-- Data: 2026-01-28

-- ============================================================================
-- TABELA: section_metadata (atualização)
-- ============================================================================

-- Adiciona coluna pk (chave primária composta)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='section_metadata' AND column_name='pk') THEN
        ALTER TABLE section_metadata ADD COLUMN pk VARCHAR(30);
        RAISE NOTICE 'Coluna pk adicionada em section_metadata';
    END IF;
END $$;

-- Adiciona coluna eleitores_sem_biometria
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='section_metadata' AND column_name='eleitores_sem_biometria') THEN
        ALTER TABLE section_metadata ADD COLUMN eleitores_sem_biometria INTEGER DEFAULT 0;
        RAISE NOTICE 'Coluna eleitores_sem_biometria adicionada em section_metadata';
    END IF;
END $$;

-- Adiciona coluna biometria_analysis (JSONB)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='section_metadata' AND column_name='biometria_analysis') THEN
        ALTER TABLE section_metadata ADD COLUMN biometria_analysis JSONB;
        RAISE NOTICE 'Coluna biometria_analysis adicionada em section_metadata';
    END IF;
END $$;

-- Índice para busca por PK composta
CREATE INDEX IF NOT EXISTS idx_section_metadata_pk ON section_metadata(pk);

-- Atualiza PK para registros existentes (se houver)
UPDATE section_metadata 
SET pk = municipio_codigo || '-' || zona || '-' || secao
WHERE pk IS NULL 
  AND municipio_codigo IS NOT NULL 
  AND zona IS NOT NULL 
  AND secao IS NOT NULL;


-- ============================================================================
-- TABELA: mesarios (nova)
-- ============================================================================

CREATE TABLE IF NOT EXISTS mesarios (
    id SERIAL PRIMARY KEY,
    
    -- Identificação da seção
    uf VARCHAR(2) NOT NULL,
    turno INTEGER NOT NULL,
    municipio_codigo VARCHAR(10),
    zona VARCHAR(10),
    secao VARCHAR(10),
    pk VARCHAR(30),  -- Chave composta: municipio-zona-secao
    
    -- Dados do mesário
    numero_mesario VARCHAR(12) NOT NULL,  -- Título de eleitor (12 dígitos)
    eleitor_secao BOOLEAN,  -- True = eleitor da seção, False = não é, NULL = não identificado
    arquivo_biometria VARCHAR(20),  -- Número do arquivo onde a biometria foi encontrada coletada
    
    -- Eventos
    eventos JSONB,  -- Lista de eventos: [{tipo, timestamp}, ...]
    primeiro_evento TIMESTAMP,
    ultimo_evento TIMESTAMP,
    
    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint única
    UNIQUE(uf, turno, municipio_codigo, zona, secao, numero_mesario)
);

-- Índices para mesários
CREATE INDEX IF NOT EXISTS idx_mesarios_pk ON mesarios(pk);
CREATE INDEX IF NOT EXISTS idx_mesarios_numero ON mesarios(numero_mesario);
CREATE INDEX IF NOT EXISTS idx_mesarios_eleitor_secao ON mesarios(eleitor_secao);
CREATE INDEX IF NOT EXISTS idx_mesarios_uf_turno ON mesarios(uf, turno);

-- Comentários nas colunas
COMMENT ON TABLE mesarios IS 'Dados dos mesários extraídos dos logs da urna eletrônica';
COMMENT ON COLUMN mesarios.numero_mesario IS 'Título de eleitor do mesário (12 dígitos)';
COMMENT ON COLUMN mesarios.eleitor_secao IS 'Indica se o mesário é eleitor da própria seção onde trabalhou';
COMMENT ON COLUMN mesarios.arquivo_biometria IS 'Número do arquivo onde a biometria foi encontrada';
COMMENT ON COLUMN mesarios.eventos IS 'JSON com lista de eventos: biometria_lida, registrado, eleitor_secao, etc.';
