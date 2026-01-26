from pathlib import Path
from sqlalchemy import create_engine, text
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from config import config

# Conectar ao banco
engine = create_engine(config.POSTGRES_CONN)

# Buscar arquivos processados
with engine.connect() as conn:
    result = conn.execute(text("SELECT DISTINCT source_file FROM log_eventos ORDER BY source_file"))
    processed_files = {row[0] for row in result}

print(f"Total de arquivos no banco: {len(processed_files)}")

# Buscar arquivos no disco
base_dir = Path(r"C:\Users\marco\Downloads\TSE\data\raw_logs")
estados = ['ac', 'ap', 'rr', 'to', 'se']

all_disk_files = []
for uf in estados:
    state_dir = base_dir / uf
    if state_dir.exists():
        files = list(state_dir.glob('**/*.logjez'))[:200]  # Limite de 200
        all_disk_files.extend([str(f) for f in files])

print(f"Total de arquivos no disco (limite 200/estado): {len(all_disk_files)}")

# Encontrar arquivos faltantes
missing_files = []
for disk_file in all_disk_files:
    # Normalizar path para comparação
    normalized = disk_file.replace('\\', '/')
    if not any(normalized in pf or pf in normalized for pf in processed_files):
        missing_files.append(disk_file)

print(f"\nArquivos faltantes: {len(missing_files)}")
if missing_files:
    print("\nPrimeiros 5 arquivos faltantes:")
    for f in missing_files[:5]:
        print(f"  - {Path(f).name}")
