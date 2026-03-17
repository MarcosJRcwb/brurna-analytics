
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from typing import List, Dict

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from config import config
from analytics.aggregator import aggregate_logs
from database.db_writer import save_log_patterns, save_temporal_metrics, save_section_metadata_batch, save_log_exceptions_batch

def worker_init(db_url):
    global engine_worker
    engine_worker = create_engine(db_url)

def process_section_worker(args):
    """Worker function for parallel processing of a single section."""
    source_file, uf, turno = args
    try:
        with engine_worker.connect() as conn:
            query = text("SELECT timestamp, level as severidade, code, message as mensagem, source_file, original_line FROM log_eventos WHERE source_file = :sf")
            df = pd.read_sql(query, conn, params={"sf": source_file})
            
            if df.empty:
                return None
            
            df['aplicativo'] = 'GAP' # Default se não houver parse fino
            
            # --- 🛡️ AXIOM: Extracao de Excecoes Brutas ---
            # Separamos as anomalias para manter a raw string antes de amassar tudo no aggregador.
            suspect_mask = df['severidade'].isin(['ERRO', 'CRITICO', 'FATAL', 'ERROR', 'WARN', 'ATENCAO']) | df['mensagem'].str.contains('N3api', na=False, case=False)
            exceptions_df = df[suspect_mask].copy()
            
            if not exceptions_df.empty:
                exceptions_df['uf'] = uf.upper()
                exceptions_df['turno'] = turno
                # Extract basic section IDs directly from source_file if possible, or wait till metadata assigns pk
                exceptions_df['municipio_codigo'] = None
                exceptions_df['zona'] = None
                exceptions_df['secao'] = None
                exceptions_df['sec_pk'] = None
                exceptions_df['mensagem_bruta'] = exceptions_df['original_line']
                # Drop cols not in schema
                exceptions_df = exceptions_df[['uf', 'turno', 'municipio_codigo', 'zona', 'secao', 'sec_pk', 'timestamp', 'severidade', 'aplicativo', 'mensagem_bruta']]
            else:
                exceptions_df = pd.DataFrame()
            
            # Agora gera a telemetria normal (que reduzirá gigabytes pra megabytes)
            patterns, temporal, metadata = aggregate_logs(df, uf=uf, turno=turno)
            
            # Corrige a PK das exceptions se encontramos metadata vinculada
            if not exceptions_df.empty and metadata and metadata.get('pk'):
                exceptions_df['municipio_codigo'] = metadata.get('municipio_codigo')
                exceptions_df['zona'] = metadata.get('zona')
                exceptions_df['secao'] = metadata.get('secao')
                exceptions_df['sec_pk'] = metadata.get('pk')
            
            return {
                'patterns': patterns,
                'temporal': temporal,
                'metadata': metadata,
                'exceptions': exceptions_df
            }
    except Exception as e:
        # print(f"Erro processando {source_file}: {e}")
        return None

def process_uf_batch(uf: str, turno: int = 1, db_url: str = None):
    """Processa todos os logs de uma UF no banco de dados em paralelo."""
    if not db_url:
        db_url = config.LOCAL_POSTGRES_CONN
        
    engine = create_engine(db_url)
    print(f"\n>>> AGREGADOR PARALELO: {uf.upper()} ({db_url})")
    
    with engine.connect() as conn:
        query = text("SELECT DISTINCT source_file FROM log_eventos WHERE source_file LIKE :pattern")
        res = conn.execute(query, {"pattern": f"{uf.lower()}/%"}).fetchall()
        source_files = [r[0] for r in res]
        
    total_sections = len(source_files)
    if total_sections == 0:
        print(f"Nenhuma seção encontrada para {uf}")
        return

    # Use max 30 workers as requested for Ryzen 9
    num_workers = min(30, cpu_count())
    print(f"Lançando {num_workers} workers para agregação...")
    
    # Task list for workers
    tasks = [(sf, uf, turno) for sf in source_files]
    
    results_metadata = []
    pbar = tqdm(total=total_sections, desc=f"Agregando {uf.upper()} ({num_workers} cores)")
    
    # Process in chunks to manage memory and DB I/O
    chunk_size = 300
    with Pool(processes=num_workers, initializer=worker_init, initargs=(db_url,)) as pool:
        for i in range(0, total_sections, chunk_size):
            chunk_tasks = tasks[i:i+chunk_size]
            results = pool.map(process_section_worker, chunk_tasks)
            
            # Save results from this chunk
            valid_results = [r for r in results if r]
            
            all_patterns = []
            all_temporal = []
            all_exceptions = []
            
            for res in valid_results:
                if not res: continue
                if not res['patterns'].empty: all_patterns.append(res['patterns'])
                if not res['temporal'].empty: all_temporal.append(res['temporal'])
                if 'exceptions' in res and not res['exceptions'].empty: all_exceptions.append(res['exceptions'])
                results_metadata.append(res['metadata'])
            
            # Aggregated Pattern Save
            if all_patterns:
                chunk_p = pd.concat(all_patterns)
                chunk_p = chunk_p.groupby(['aplicativo', 'severidade', 'mensagem_padrao']).agg({
                    'ocorrencias': 'sum',
                    'primeira_ocorrencia': 'min',
                    'ultima_ocorrencia': 'max',
                    'mensagem_exemplo': 'first'
                }).reset_index()
                save_log_patterns(chunk_p, uf, turno)
            
            # Aggregated Temporal Save
            if all_temporal:
                chunk_t = pd.concat(all_temporal)
                chunk_t = chunk_t.groupby(['data', 'hora', 'aplicativo', 'severidade']).agg({
                    'quantidade': 'sum'
                }).reset_index()
                save_temporal_metrics(chunk_t, uf, turno)
            
            # Batch save metadata (includes mesários)
            if results_metadata:
                save_section_metadata_batch(results_metadata)
                results_metadata = []
                
            # Batch save raw exceptions
            if all_exceptions:
                chunk_exc = pd.concat(all_exceptions)
                save_log_exceptions_batch(chunk_exc)
                

            pbar.update(len(chunk_tasks))
            
    pbar.close()
    print(f"✅ UF {uf.upper()} agregada com sucesso.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--uf", required=True)
    args = parser.parse_args()
    process_uf_batch(args.uf)
