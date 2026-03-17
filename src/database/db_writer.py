# db_writer.py
# -*- coding: utf-8 -*-
"""
Funções para salvar dados agregados no banco de dados.

Changelog:
    v2.0 - Adicionado suporte para:
         - Chave primária composta (pk)
         - Tabela de mesários com vínculos
         - Análise de biometria
         - Eleitores sem biometria
"""

from sqlalchemy import create_engine, text
import pandas as pd
from sqlalchemy.orm import sessionmaker
from config import config
import json
from typing import List, Dict

# Cria engine de conexão
engine = create_engine(config.POSTGRES_CONN, pool_pre_ping=True, pool_recycle=3600)
Session = sessionmaker(bind=engine)


# =============================================================================
# SQL para criar/atualizar tabelas
# =============================================================================

SQL_CREATE_TABLES = """
-- Auth: users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Auth: refresh tokens
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de metadados da seção (atualizada)
CREATE TABLE IF NOT EXISTS section_metadata (
    id SERIAL PRIMARY KEY,
    uf VARCHAR(2) NOT NULL,
    turno INTEGER NOT NULL,
    municipio_codigo VARCHAR(10),
    zona VARCHAR(10),
    secao VARCHAR(10),
    pk VARCHAR(30),  -- Chave composta: municipio-zona-secao
    total_eventos INTEGER,
    periodo_inicio TIMESTAMP,
    periodo_fim TIMESTAMP,
    duracao_segundos INTEGER,
    aplicativos_usados TEXT[],
    severidades JSONB,
    hash_arquivo VARCHAR(64),
    modelo_urna VARCHAR(50),
    votos_computados INTEGER DEFAULT 0,
    eleitores_habilitados INTEGER DEFAULT 0,
    eleitores_sem_biometria INTEGER DEFAULT 0,
    biometria_analysis JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(uf, turno, municipio_codigo, zona, secao)
);

-- Tabela de padrões de log
CREATE TABLE IF NOT EXISTS log_patterns (
    id SERIAL PRIMARY KEY,
    uf VARCHAR(2) NOT NULL,
    turno INTEGER NOT NULL,
    aplicativo VARCHAR(100),
    severidade VARCHAR(20),
    mensagem_padrao TEXT,
    mensagem_exemplo TEXT,
    ocorrencias INTEGER DEFAULT 0,
    primeira_ocorrencia TIMESTAMP,
    ultima_ocorrencia TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(uf, turno, aplicativo, severidade, mensagem_padrao)
);

-- Tabela de métricas temporais
CREATE TABLE IF NOT EXISTS temporal_metrics (
    id SERIAL PRIMARY KEY,
    uf VARCHAR(2) NOT NULL,
    turno INTEGER NOT NULL,
    data DATE,
    hora INTEGER,
    aplicativo VARCHAR(100),
    severidade VARCHAR(20),
    quantidade INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(uf, turno, data, hora, aplicativo, severidade)
);

-- Tabela de mesários
CREATE TABLE IF NOT EXISTS mesarios (
    id SERIAL PRIMARY KEY,
    uf VARCHAR(2) NOT NULL,
    turno INTEGER NOT NULL,
    municipio_codigo VARCHAR(10),
    zona VARCHAR(10),
    secao VARCHAR(10),
    pk VARCHAR(30),  -- Referência à seção
    numero_mesario VARCHAR(12) NOT NULL,  -- Título de eleitor
    eleitor_secao BOOLEAN,  -- True = eleitor da seção, False = não é
    arquivo_biometria VARCHAR(20),  -- Número do arquivo
    eventos JSONB,  -- Lista de eventos
    primeiro_evento TIMESTAMP,
    ultimo_evento TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(uf, turno, municipio_codigo, zona, secao, numero_mesario)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_section_metadata_pk ON section_metadata(pk);
CREATE INDEX IF NOT EXISTS idx_mesarios_pk ON mesarios(pk);
CREATE INDEX IF NOT EXISTS idx_mesarios_numero ON mesarios(numero_mesario);
CREATE INDEX IF NOT EXISTS idx_log_patterns_uf ON log_patterns(uf);
CREATE INDEX IF NOT EXISTS idx_temporal_metrics_uf ON temporal_metrics(uf);

-- Adicionar colunas novas se tabela já existir (migrations)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='section_metadata' AND column_name='pk') THEN
        ALTER TABLE section_metadata ADD COLUMN pk VARCHAR(30);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='section_metadata' AND column_name='eleitores_sem_biometria') THEN
        ALTER TABLE section_metadata ADD COLUMN eleitores_sem_biometria INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='section_metadata' AND column_name='biometria_analysis') THEN
        ALTER TABLE section_metadata ADD COLUMN biometria_analysis JSONB;
    END IF;
END $$;

-- Tabela de Exceções e Anomalias Brutas (Armazena a linha original, não o pattern_id)
CREATE TABLE IF NOT EXISTS log_exceptions (
    id SERIAL PRIMARY KEY,
    uf VARCHAR(2) NOT NULL,
    turno INTEGER NOT NULL,
    municipio_codigo VARCHAR(10),
    zona VARCHAR(10),
    secao VARCHAR(10),
    sec_pk VARCHAR(30), -- Vinculo forte com a URNA
    timestamp TIMESTAMP,
    severidade VARCHAR(20),
    aplicativo VARCHAR(50),
    mensagem_bruta TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def create_tables():
    """Cria ou atualiza as tabelas necessárias."""
    try:
        conn = engine.connect()
        conn.execute(text(SQL_CREATE_TABLES))
        conn.commit()
        conn.close()
        print("✅ Tabelas criadas/atualizadas com sucesso")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")

# =============================================================================
# Funções de salvamento
# =============================================================================

def save_log_patterns(patterns_df: pd.DataFrame, uf: str, turno: int):
    if patterns_df.empty: return
    patterns_df['uf'] = uf.upper()
    patterns_df['turno'] = turno
    try:
        conn = engine.connect()
        for _, row in patterns_df.iterrows():
            conn.execute(text("""
                INSERT INTO log_patterns (uf, turno, aplicativo, severidade, mensagem_padrao, mensagem_exemplo, ocorrencias, primeira_ocorrencia, ultima_ocorrencia)
                VALUES (:uf, :turno, :aplicativo, :severidade, :mensagem_padrao, :mensagem_exemplo, :ocorrencias, :primeira_ocorrencia, :ultima_ocorrencia)
                ON CONFLICT (uf, turno, aplicativo, severidade, mensagem_padrao)
                DO UPDATE SET ocorrencias = log_patterns.ocorrencias + EXCLUDED.ocorrencias, primeira_ocorrencia = LEAST(log_patterns.primeira_ocorrencia, EXCLUDED.primeira_ocorrencia), ultima_ocorrencia = GREATEST(log_patterns.ultima_ocorrencia, EXCLUDED.ultima_ocorrencia), mensagem_exemplo = EXCLUDED.mensagem_exemplo
            """), row.to_dict())
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao salvar padrões: {e}")

def save_temporal_metrics(temporal_df: pd.DataFrame, uf: str, turno: int):
    if temporal_df.empty: return
    temporal_df['uf'] = uf.upper()
    temporal_df['turno'] = turno
    try:
        conn = engine.connect()
        for _, row in temporal_df.iterrows():
            conn.execute(text("""
                INSERT INTO temporal_metrics (uf, turno, data, hora, aplicativo, severidade, quantidade)
                VALUES (:uf, :turno, :data, :hora, :aplicativo, :severidade, :quantidade)
                ON CONFLICT (uf, turno, data, hora, aplicativo, severidade)
                DO UPDATE SET quantidade = temporal_metrics.quantidade + EXCLUDED.quantidade
            """), row.to_dict())
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao salvar métricas temporais: {e}")

def save_log_exceptions_batch(df: pd.DataFrame):
    """Save raw exception strings mapped to their forensic keys."""
    if df.empty: return
    with engine.begin() as conn:
        df.to_sql('log_exceptions', conn, if_exists='append', index=False,
                  method='multi', chunksize=1000)

def _save_mesarios(conn, mesarios, uf, turno, municipio_codigo, zona, secao, pk):
    for m in mesarios:
        evs = json.dumps(m.get('eventos', []), default=str)
        conn.execute(text("""
            INSERT INTO mesarios (uf, turno, municipio_codigo, zona, secao, pk, numero_mesario, eleitor_secao, arquivo_biometria, eventos, primeiro_evento, ultimo_evento)
            VALUES (:uf, :turno, :municipio_codigo, :zona, :secao, :pk, :numero_mesario, :eleitor_secao, :arquivo_biometria, :eventos, :primeiro_evento, :ultimo_evento)
            ON CONFLICT (uf, turno, municipio_codigo, zona, secao, numero_mesario)
            DO UPDATE SET eleitor_secao = COALESCE(EXCLUDED.eleitor_secao, mesarios.eleitor_secao), arquivo_biometria = COALESCE(EXCLUDED.arquivo_biometria, mesarios.arquivo_biometria), eventos = EXCLUDED.eventos
        """), {
            'uf': uf, 'turno': turno, 'municipio_codigo': municipio_codigo, 'zona': zona, 'secao': secao, 'pk': pk,
            'numero_mesario': m.get('numero'), 'eleitor_secao': m.get('eleitor_secao'), 'arquivo_biometria': m.get('arquivo_biometria'),
            'eventos': evs, 'primeiro_evento': None, 'ultimo_evento': None # Simplified
        })

def save_section_metadata_batch(metadata_list: List[dict]):
    if not metadata_list: return
    try:
        conn = engine.connect()
        for m in metadata_list:
            sev_json = json.dumps(m.get('severidades', {}))
            bio_json = json.dumps(m.get('biometria_analysis', {}))
            conn.execute(text("""
                INSERT INTO section_metadata (uf, turno, municipio_codigo, zona, secao, pk, total_eventos, periodo_inicio, periodo_fim, duracao_segundos, aplicativos_usados, severidades, hash_arquivo, modelo_urna, votos_computados, eleitores_habilitados, eleitores_sem_biometria, biometria_analysis)
                VALUES (:uf, :turno, :municipio_codigo, :zona, :secao, :pk, :total_eventos, :periodo_inicio, :periodo_fim, :duracao_segundos, :aplicativos_usados, :severidades, :hash_arquivo, :modelo_urna, :votos_computados, :eleitores_habilitados, :eleitores_sem_biometria, :biometria_analysis)
                ON CONFLICT (uf, turno, municipio_codigo, zona, secao)
                DO UPDATE SET pk = EXCLUDED.pk, total_eventos = EXCLUDED.total_eventos, periodo_inicio = EXCLUDED.periodo_inicio, periodo_fim = EXCLUDED.periodo_fim, duracao_segundos = EXCLUDED.duracao_segundos, aplicativos_usados = EXCLUDED.aplicativos_usados, severidades = EXCLUDED.severidades, hash_arquivo = EXCLUDED.hash_arquivo, modelo_urna = EXCLUDED.modelo_urna, votos_computados = EXCLUDED.votos_computados, eleitores_habilitados = EXCLUDED.eleitores_habilitados, eleitores_sem_biometria = EXCLUDED.eleitores_sem_biometria, biometria_analysis = EXCLUDED.biometria_analysis
            """), {
                'uf': m.get('uf'), 'turno': m.get('turno'), 'municipio_codigo': m.get('municipio_codigo'), 'zona': m.get('zona'), 'secao': m.get('secao'), 'pk': m.get('pk'),
                'total_eventos': m.get('total_eventos'), 'periodo_inicio': m.get('periodo_inicio'), 'periodo_fim': m.get('periodo_fim'), 'duracao_segundos': m.get('duracao_segundos'),
                'aplicativos_usados': m.get('aplicativos_usados', []), 'severidades': sev_json, 'hash_arquivo': m.get('hash_arquivo'), 'modelo_urna': m.get('modelo_urna'),
                'votos_computados': m.get('votos_computados', 0), 'eleitores_habilitados': m.get('eleitores_habilitados', 0), 'eleitores_sem_biometria': m.get('eleitores_sem_biometria', 0), 'biometria_analysis': bio_json
            })
            _save_mesarios(conn, m.get('mesarios', []), m.get('uf'), m.get('turno'), m.get('municipio_codigo'), m.get('zona'), m.get('secao'), m.get('pk'))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao salvar metadados: {e}")

def save_parsed_logs(df: pd.DataFrame, uf: str, turno: int):
    print("⚠️  AVISO: save_parsed_logs() está deprecated.")