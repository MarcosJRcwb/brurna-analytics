
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
import pandas as pd
from tqdm import tqdm

# Add src to path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from config import config
from src.parser.log_parser import TSELogParser

engine = create_engine(config.POSTGRES_CONN)

def repair_models():
    print("🛠️  Iniciando reparo de modelos de urna (RR, AP, AC)...")
    
    with engine.connect() as conn:
        # Pega seções sem modelo
        query = "SELECT uf, municipio_codigo, zona, secao, hash_arquivo FROM section_metadata WHERE modelo_urna IS NULL"
        sections = pd.read_sql(query, conn)
        
    print(f"🔍 Encontradas {len(sections)} seções para reparar.")
    
    for _, row in tqdm(sections.iterrows(), total=len(sections), desc="Reparando"):
        uf = row['uf'].lower()
        # Busca o arquivo real
        raw_dir = config.RAW_LOGS_DIR / uf
        # Tenta localizar o arquivo pelo hash ou nome padrão
        # Para simplificar o reparo rápido, vamos buscar pelo padrão de nome se possível
        pattern = f"*-{row['municipio_codigo']}{row['zona']}{row['secao']}.logjez"
        files = list(raw_dir.glob(pattern))
        
        if files:
            try:
                parser = TSELogParser(str(files[0]))
                df = parser.parse_file()
                model = parser.metadata.get('modelo_urna')
                
                if model:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            UPDATE section_metadata 
                            SET modelo_urna = :model 
                            WHERE uf = :uf AND municipio_codigo = :mu AND zona = :zo AND secao = :se
                        """), {
                            'model': model,
                            'uf': row['uf'],
                            'mu': row['municipio_codigo'],
                            'zo': row['zona'],
                            'se': row['secao']
                        })
                        conn.commit()
            except Exception as e:
                pass # Silencioso no reparo

    print("✅ Reparo concluído.")

if __name__ == "__main__":
    repair_models()
