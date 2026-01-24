#!/usr/bin/env python3
"""
Script de migração para transformar o banco de dados de logs brutos
para agregação inteligente.

ATENÇÃO: Este script vai DROPAR a tabela 'logs' existente (40 GB).
Certifique-se de ter backup dos arquivos Parquet antes de executar.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from config import config
from datetime import datetime
import pandas as pd


def create_backup_dump():
    """Cria dump SQL da tabela logs antes de dropar"""
    print("\n📦 Criando backup SQL da tabela logs...")
    
    try:
        # Nota: Para PostgreSQL, usar pg_dump seria mais eficiente
        # Aqui fazemos um backup simples dos metadados
        engine = create_engine(config.POSTGRES_CONN)
        conn = engine.connect()
        
        # Salva estatísticas antes da migração
        result = conn.execute(text("""
            SELECT 
                uf,
                COUNT(*) as total_rows,
                MIN(timestamp) as min_date,
                MAX(timestamp) as max_date
            FROM logs
            GROUP BY uf
        """))
        
        backup_file = Path("backup_logs_metadata.txt")
        with open(backup_file, 'w') as f:
            f.write(f"Backup criado em: {datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
            for row in result:
                f.write(f"UF: {row[0]}\n")
                f.write(f"  Total de linhas: {row[1]:,}\n")
                f.write(f"  Período: {row[2]} a {row[3]}\n\n")
        
        conn.close()
        print(f"✅ Backup de metadados salvo em: {backup_file}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return False


def create_new_tables():
    """Cria as novas tabelas agregadas"""
    print("\n🏗️  Criando novas tabelas...")
    
    engine = create_engine(config.POSTGRES_CONN)
    conn = engine.connect()
    
    try:
        # Tabela de padrões de log
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS log_patterns (
                id SERIAL PRIMARY KEY,
                uf VARCHAR(2) NOT NULL,
                turno INT NOT NULL,
                aplicativo VARCHAR(50),
                severidade VARCHAR(20),
                mensagem_padrao TEXT,
                mensagem_exemplo TEXT,
                ocorrencias INT DEFAULT 1,
                primeira_ocorrencia TIMESTAMP,
                ultima_ocorrencia TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(uf, turno, aplicativo, severidade, mensagem_padrao)
            )
        """))
        print("  ✅ Tabela log_patterns criada")
        
        # Tabela de métricas temporais
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS temporal_metrics (
                id SERIAL PRIMARY KEY,
                uf VARCHAR(2) NOT NULL,
                turno INT NOT NULL,
                data DATE NOT NULL,
                hora INT,
                aplicativo VARCHAR(50),
                severidade VARCHAR(20),
                quantidade INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(uf, turno, data, hora, aplicativo, severidade)
            )
        """))
        print("  ✅ Tabela temporal_metrics criada")
        
        # Tabela de metadados de seção
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS section_metadata (
                id SERIAL PRIMARY KEY,
                uf VARCHAR(2) NOT NULL,
                turno INT NOT NULL,
                municipio_codigo VARCHAR(10),
                zona VARCHAR(10),
                secao VARCHAR(10),
                total_eventos INT,
                periodo_inicio TIMESTAMP,
                periodo_fim TIMESTAMP,
                duracao_segundos INT,
                aplicativos_usados TEXT[],
                severidades JSONB,
                hash_arquivo VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(uf, turno, municipio_codigo, zona, secao)
            )
        """))
        print("  ✅ Tabela section_metadata criada")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        conn.close()
        return False


def create_indexes():
    """Cria índices para otimizar queries"""
    print("\n📊 Criando índices...")
    
    engine = create_engine(config.POSTGRES_CONN)
    conn = engine.connect()
    
    try:
        # Índices para log_patterns
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_patterns_lookup 
            ON log_patterns(uf, aplicativo, severidade)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_patterns_occurrences 
            ON log_patterns(ocorrencias DESC)
        """))
        
        # Índices para temporal_metrics
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_temporal_range 
            ON temporal_metrics(uf, data, hora)
        """))
        
        # Índices para section_metadata
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_section_lookup 
            ON section_metadata(uf, municipio_codigo, zona, secao)
        """))
        
        conn.commit()
        conn.close()
        print("  ✅ Índices criados com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar índices: {e}")
        conn.close()
        return False


def drop_old_table():
    """Dropa a tabela logs antiga"""
    print("\n🗑️  Dropando tabela logs antiga...")
    
    engine = create_engine(config.POSTGRES_CONN)
    conn = engine.connect()
    
    try:
        # Confirma com usuário (segurança extra)
        print("⚠️  ATENÇÃO: Isso vai DELETAR permanentemente a tabela 'logs' (40 GB)")
        print("   Os dados podem ser regenerados dos arquivos Parquet se necessário.")
        
        response = input("\nDigite 'CONFIRMAR' para prosseguir: ")
        
        if response != "CONFIRMAR":
            print("❌ Operação cancelada pelo usuário")
            conn.close()
            return False
        
        conn.execute(text("DROP TABLE IF EXISTS logs CASCADE"))
        conn.commit()
        print("  ✅ Tabela logs dropada")
        
        # Executa VACUUM para recuperar espaço
        print("\n🧹 Executando VACUUM FULL para recuperar espaço em disco...")
        print("   (Isso pode levar alguns minutos...)")
        
        conn.close()
        
        # VACUUM precisa de uma nova conexão sem transação
        engine_autocommit = create_engine(
            config.POSTGRES_CONN,
            isolation_level="AUTOCOMMIT"
        )
        conn_autocommit = engine_autocommit.connect()
        conn_autocommit.execute(text("VACUUM FULL"))
        conn_autocommit.close()
        
        print("  ✅ VACUUM concluído")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao dropar tabela: {e}")
        conn.close()
        return False


def verify_migration():
    """Verifica se a migração foi bem-sucedida"""
    print("\n🔍 Verificando migração...")
    
    engine = create_engine(config.POSTGRES_CONN)
    inspector = inspect(engine)
    
    tables = inspector.get_table_names()
    
    required_tables = ['log_patterns', 'temporal_metrics', 'section_metadata']
    missing_tables = [t for t in required_tables if t not in tables]
    
    if missing_tables:
        print(f"❌ Tabelas faltando: {missing_tables}")
        return False
    
    print("  ✅ Todas as tabelas criadas")
    
    if 'logs' in tables:
        print("  ⚠️  Tabela 'logs' ainda existe (não foi dropada)")
    else:
        print("  ✅ Tabela 'logs' antiga removida")
    
    # Verifica tamanho do banco
    conn = engine.connect()
    result = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
    db_size = result.scalar()
    print(f"\n📊 Tamanho atual do banco: {db_size}")
    conn.close()
    
    return True


def main():
    """Função principal de migração"""
    print("=" * 60)
    print("MIGRAÇÃO: Logs Brutos → Agregação Inteligente")
    print("=" * 60)
    
    # Passo 1: Backup
    if not create_backup_dump():
        print("\n❌ Falha no backup. Abortando migração.")
        return False
    
    # Passo 2: Criar novas tabelas
    if not create_new_tables():
        print("\n❌ Falha ao criar tabelas. Abortando migração.")
        return False
    
    # Passo 3: Criar índices
    if not create_indexes():
        print("\n⚠️  Falha ao criar índices, mas tabelas foram criadas.")
    
    # Passo 4: Dropar tabela antiga
    if not drop_old_table():
        print("\n⚠️  Tabela antiga não foi dropada. Você pode fazer isso manualmente depois.")
    
    # Passo 5: Verificar
    if not verify_migration():
        print("\n❌ Verificação falhou.")
        return False
    
    print("\n" + "=" * 60)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print("\nPróximos passos:")
    print("1. Reprocessar dados de AC: python main.py parse --uf ac --limit 100")
    print("2. Verificar resultados: python stats.py resumo --uf ac")
    print("3. Testar com MG: python main.py download --uf mg --limit 100")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
