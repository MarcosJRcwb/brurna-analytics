from pathlib import Path
import os

base_dir = Path(r"C:\Users\marco\Downloads\TSE\data\raw_logs")
estados = ['ac', 'ap', 'rr', 'to', 'se']

print("=" * 60)
print("ANÁLISE DE ARQUIVOS .logjez POR ESTADO")
print("=" * 60)

total_files_disk = 0
for uf in estados:
    state_dir = base_dir / uf
    if state_dir.exists():
        files = list(state_dir.glob('**/*.logjez'))
        print(f"\n{uf.upper()}:")
        print(f"  Total no disco: {len(files)} arquivos")
        print(f"  Limite processado: 200 arquivos")
        print(f"  Restante: {max(0, len(files) - 200)} arquivos")
        total_files_disk += len(files)
    else:
        print(f"\n{uf.upper()}: Diretório não encontrado em {state_dir}")

print("\n" + "=" * 60)
print(f"TOTAL NO DISCO: {total_files_disk} arquivos")
print(f"TOTAL PROCESSADO (banco): 999 arquivos")
print(f"TOTAL ESPERADO: {min(total_files_disk, 200 * 5)} arquivos (limite 200/estado)")
print(f"FALTANDO: {min(total_files_disk, 200 * 5) - 999} arquivos")
print("=" * 60)
