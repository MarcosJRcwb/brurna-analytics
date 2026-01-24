"""
Funções atualizadas para salvar dados agregados no banco de dados.
"""

from sqlalchemy import create_engine, text
import pandas as pd
from sqlalchemy.orm import sessionmaker
from config import config
import json

# Cria engine de conexão
engine = create_engine(config.POSTGRES_CONN, pool_pre_ping=True, pool_recycle=3600)
Session = sessionmaker(bind=engine)


def save_log_patterns(patterns_df: pd.DataFrame, uf: str, turno: int):
    """
    Salva padrões de log agregados no banco.
    
    Usa UPSERT para incrementar contagens de padrões existentes.
    """
    if patterns_df.empty:
        print("DataFrame de padrões vazio, nada a salvar.")
        return
    
    # Adiciona colunas de contexto
    patterns_df['uf'] = uf.upper()
    patterns_df['turno'] = turno
    
    try:
        conn = engine.connect()
        
        for _, row in patterns_df.iterrows():
            conn.execute(text("""
                INSERT INTO log_patterns (
                    uf, turno, aplicativo, severidade, mensagem_padrao,
                    mensagem_exemplo, ocorrencias, primeira_ocorrencia, ultima_ocorrencia
                )
                VALUES (
                    :uf, :turno, :aplicativo, :severidade, :mensagem_padrao,
                    :mensagem_exemplo, :ocorrencias, :primeira_ocorrencia, :ultima_ocorrencia
                )
                ON CONFLICT (uf, turno, aplicativo, severidade, mensagem_padrao)
                DO UPDATE SET
                    ocorrencias = log_patterns.ocorrencias + EXCLUDED.ocorrencias,
                    primeira_ocorrencia = LEAST(log_patterns.primeira_ocorrencia, EXCLUDED.primeira_ocorrencia),
                    ultima_ocorrencia = GREATEST(log_patterns.ultima_ocorrencia, EXCLUDED.ultima_ocorrencia),
                    mensagem_exemplo = EXCLUDED.mensagem_exemplo
            """), {
                'uf': row['uf'],
                'turno': row['turno'],
                'aplicativo': row['aplicativo'],
                'severidade': row['severidade'],
                'mensagem_padrao': row['mensagem_padrao'],
                'mensagem_exemplo': row['mensagem_exemplo'],
                'ocorrencias': int(row['ocorrencias']),
                'primeira_ocorrencia': row['primeira_ocorrencia'],
                'ultima_ocorrencia': row['ultima_ocorrencia']
            })
        
        conn.commit()
        conn.close()
        print(f"✅ Salvos {len(patterns_df)} padrões para UF {uf} - Turno {turno}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar padrões: {e}")
        import traceback
        traceback.print_exc()


def save_temporal_metrics(temporal_df: pd.DataFrame, uf: str, turno: int):
    """
    Salva métricas temporais agregadas no banco.
    """
    if temporal_df.empty:
        print("DataFrame de métricas temporais vazio, nada a salvar.")
        return
    
    # Adiciona colunas de contexto
    temporal_df['uf'] = uf.upper()
    temporal_df['turno'] = turno
    
    try:
        conn = engine.connect()
        
        for _, row in temporal_df.iterrows():
            conn.execute(text("""
                INSERT INTO temporal_metrics (
                    uf, turno, data, hora, aplicativo, severidade, quantidade
                )
                VALUES (
                    :uf, :turno, :data, :hora, :aplicativo, :severidade, :quantidade
                )
                ON CONFLICT (uf, turno, data, hora, aplicativo, severidade)
                DO UPDATE SET
                    quantidade = temporal_metrics.quantidade + EXCLUDED.quantidade
            """), {
                'uf': row['uf'],
                'turno': row['turno'],
                'data': row['data'],
                'hora': int(row['hora']),
                'aplicativo': row['aplicativo'],
                'severidade': row['severidade'],
                'quantidade': int(row['quantidade'])
            })
        
        conn.commit()
        conn.close()
        print(f"✅ Salvas {len(temporal_df)} métricas temporais para UF {uf} - Turno {turno}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar métricas temporais: {e}")
        import traceback
        traceback.print_exc()


def save_section_metadata(metadata: dict):
    """
    Salva metadados de uma seção eleitoral.
    """
    if not metadata:
        print("Metadados vazios, nada a salvar.")
        return
    
    try:
        conn = engine.connect()
        
        # Converte severidades para JSON
        severidades_json = json.dumps(metadata.get('severidades', {}))
        
        conn.execute(text("""
            INSERT INTO section_metadata (
                uf, turno, municipio_codigo, zona, secao,
                total_eventos, periodo_inicio, periodo_fim, duracao_segundos,
                aplicativos_usados, severidades, hash_arquivo
            )
            VALUES (
                :uf, :turno, :municipio_codigo, :zona, :secao,
                :total_eventos, :periodo_inicio, :periodo_fim, :duracao_segundos,
                :aplicativos_usados, :severidades, :hash_arquivo
            )
            ON CONFLICT (uf, turno, municipio_codigo, zona, secao)
            DO UPDATE SET
                total_eventos = EXCLUDED.total_eventos,
                periodo_inicio = EXCLUDED.periodo_inicio,
                periodo_fim = EXCLUDED.periodo_fim,
                duracao_segundos = EXCLUDED.duracao_segundos,
                aplicativos_usados = EXCLUDED.aplicativos_usados,
                severidades = EXCLUDED.severidades,
                hash_arquivo = EXCLUDED.hash_arquivo
        """), {
            'uf': metadata.get('uf'),
            'turno': metadata.get('turno'),
            'municipio_codigo': metadata.get('municipio_codigo'),
            'zona': metadata.get('zona'),
            'secao': metadata.get('secao'),
            'total_eventos': metadata.get('total_eventos'),
            'periodo_inicio': metadata.get('periodo_inicio'),
            'periodo_fim': metadata.get('periodo_fim'),
            'duracao_segundos': metadata.get('duracao_segundos'),
            'aplicativos_usados': metadata.get('aplicativos_usados', []),
            'severidades': severidades_json,
            'hash_arquivo': metadata.get('hash_arquivo')
        })
        
        conn.commit()
        conn.close()
        print(f"✅ Metadados salvos para seção {metadata.get('uf')}-{metadata.get('zona')}-{metadata.get('secao')}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar metadados: {e}")
        import traceback
        traceback.print_exc()


# Mantém funções antigas para compatibilidade (deprecated)
def clean_dataframe(df):
    """DEPRECATED: Mantido para compatibilidade"""
    if df.empty:
        return df
    
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(
            lambda x: x.replace('\x00', '').replace('\0', '') 
            if isinstance(x, str) else x
        )
    
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: None if x == '' else x)
    
    return df


def save_parsed_logs(df: pd.DataFrame, uf: str, turno: int):
    """
    DEPRECATED: Função antiga que salvava logs brutos.
    Mantida apenas para compatibilidade com código legado.
    
    Use save_log_patterns(), save_temporal_metrics() e save_section_metadata() instead.
    """
    print("⚠️  AVISO: save_parsed_logs() está deprecated.")
    print("   Use as novas funções de agregação: save_log_patterns(), save_temporal_metrics(), save_section_metadata()")
