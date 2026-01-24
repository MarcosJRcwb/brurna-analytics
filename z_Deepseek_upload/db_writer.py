from sqlalchemy import create_engine, text
import pandas as pd
from sqlalchemy.orm import sessionmaker
from config import config

# Cria engine de conexão
engine = create_engine(config.POSTGRES_CONN, pool_pre_ping=True, pool_recycle=3600)
Session = sessionmaker(bind=engine)

def clean_dataframe(df):
    """Remove caracteres NUL e outros problemas de strings"""
    if df.empty:
        return df
    
    # Para cada coluna do tipo string, remove caracteres NUL
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(
            lambda x: x.replace('\x00', '').replace('\0', '') 
            if isinstance(x, str) else x
        )
    
    # Converte strings vazias para None
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: None if x == '' else x)
    
    return df

def convert_date_format(date_str):
    """Converte data de DD/MM/YYYY para YYYY-MM-DD"""
    if pd.isna(date_str) or date_str is None:
        return None
    try:
        # Tenta converter de DD/MM/YYYY para YYYY-MM-DD
        from datetime import datetime
        dt = datetime.strptime(date_str, '%d/%m/%Y')
        return dt.strftime('%Y-%m-%d')
    except:
        # Se falhar, retorna None
        return None

def save_parsed_logs(df: pd.DataFrame, uf: str, turno: int):
    """Salva dados parseados no banco de dados"""
    if df.empty:
        print("DataFrame vazio, nada a salvar.")
        return
    
    # Limpa os dados
    df = clean_dataframe(df.copy())
    
    # Adiciona colunas de contexto
    df['uf'] = uf.upper()
    df['turno'] = turno
    
    # Converte timestamp se necessário
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Converte a coluna 'data' para o formato do PostgreSQL (YYYY-MM-DD)
    if 'data' in df.columns:
        df['data'] = df['data'].apply(convert_date_format)
    
    try:
        # Salva em lotes para melhor performance
        batch_size = 1000
        total_rows = len(df)
        
        for i in range(0, total_rows, batch_size):
            batch = df.iloc[i:i+batch_size]
            batch.to_sql('logs', engine, if_exists='append', index=False, method='multi')
            
            if (i + batch_size) % 10000 == 0 or (i + batch_size) >= total_rows:
                print(f"  Progresso: {min(i+batch_size, total_rows)}/{total_rows} linhas salvas")
        
        print(f"✅ Salvo {total_rows} registros na tabela logs para UF {uf} - Turno {turno}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar logs: {str(e)}")
        # Fallback: salva em arquivo local
        try:
            fallback_path = config.PROCESSED_DIR / uf / f"logs_fallback_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.parquet"
            df.to_parquet(fallback_path, index=False)
            print(f"⚠️  Dados salvos localmente em: {fallback_path}")
        except:
            print("❌ Não foi possível salvar dados localmente")

def mark_section_processed(uf: str, turno: int, municipio_codigo: str, zona: str, secao: str, status: str = 'completed', hash_arquivo: str = None):
    """Marca uma seção como processada no banco de dados"""
    try:
        with Session() as session:
            session.execute(text("""
                INSERT INTO processed_sections (uf, turno, municipio_codigo, zona, secao, status, hash_arquivo)
                VALUES (:uf, :turno, :municipio_codigo, :zona, :secao, :status, :hash_arquivo)
                ON CONFLICT (uf, turno, municipio_codigo, zona, secao) DO UPDATE
                SET status = :status, hash_arquivo = :hash_arquivo, ultima_atualizacao = CURRENT_TIMESTAMP
            """), {
                'uf': uf.upper(), 'turno': turno, 'municipio_codigo': municipio_codigo,
                'zona': zona, 'secao': secao, 'status': status, 'hash_arquivo': hash_arquivo
            })
            session.commit()
            print(f"✅ Seção {uf}-{zona}-{secao} marcada como {status}")
    except Exception as e:
        print(f"❌ Erro ao marcar seção como processada: {e}")

def check_section_processed(uf: str, turno: int, municipio_codigo: str, zona: str, secao: str) -> bool:
    """Verifica se uma seção já foi processada"""
    try:
        with Session() as session:
            result = session.execute(text("""
                SELECT status FROM processed_sections 
                WHERE uf = :uf AND turno = :turno 
                AND municipio_codigo = :municipio_codigo 
                AND zona = :zona AND secao = :secao
            """), {
                'uf': uf.upper(), 'turno': turno, 
                'municipio_codigo': municipio_codigo,
                'zona': zona, 'secao': secao
            })
            row = result.fetchone()
            return row is not None and row[0] == 'completed'
    except Exception as e:
        print(f"⚠️  Erro ao verificar seção processada: {e}")
        return False
