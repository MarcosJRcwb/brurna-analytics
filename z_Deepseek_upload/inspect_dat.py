import py7zr
import json
from pathlib import Path
import sys

log_file = Path(r"C:\Users\marco\Downloads\TSE\data\raw_logs\ac\o00407-0106600040077.logjez")
extract_dir = Path(r"C:\Users\marco\Downloads\TSE\data\raw_logs\ac\temp_inspect")
extract_dir.mkdir(exist_ok=True, parents=True)

print(f"Extraindo: {log_file.name}")

try:
    with py7zr.SevenZipFile(log_file, mode='r') as archive:
        archive.extractall(path=extract_dir)
        print("✅ Extração concluída")
        
        # Listar arquivos extraídos
        extracted_files = list(extract_dir.glob('*'))
        for f in extracted_files:
            print(f"\nArquivo: {f.name} ({f.stat().st_size} bytes)")
            
            # Verificar tipo de arquivo pelos primeiros bytes
            with open(f, 'rb') as file:
                header = file.read(100)  # Ler primeiros 100 bytes
                print(f"Primeiros 100 bytes (hex): {header.hex()[:200]}...")

            # Tentar ler como texto com vários encodings
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16', 'utf-32']
            text_lines = None
            used_encoding = None

            for enc in encodings:
                try:
                    with open(f, 'r', encoding=enc) as file:
                        text_lines = [file.readline().strip() for _ in range(5)]
                    used_encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"  Erro ao tentar encoding {enc}: {str(e)}")
                    continue

            if text_lines is not None:
                print(f"Primeiras 5 linhas (como texto - encoding detectado: {used_encoding}):")
                for i, line in enumerate(text_lines, 1):
                    if line:
                        print(f"  {i}: {line[:100]}{'...' if len(line) > 100 else ''}")
            else:
                print(
                    "  ❌ Não foi possível ler como texto em nenhum encoding testado (utf-8, latin-1, iso-8859-1, cp1252, utf-16, utf-32)")

            # Tentar ler como JSON (usando o encoding que funcionou para texto, ou utf-8 fallback)
            if used_encoding is not None:
                try:
                    with open(f, 'r', encoding=used_encoding) as file:
                        content = file.read()
                        json_data = json.loads(content)
                    print(f"  ✅ É JSON válido! Chaves: {list(json_data.keys())[:10]}")
                except json.JSONDecodeError:
                    print("  ❌ Não é JSON válido")
                except Exception as e:
                    print(f"  Erro ao tentar JSON com encoding {used_encoding}: {str(e)}")
            else:
                # Fallback para utf-8 se nenhum encoding de texto funcionou
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        content = file.read()
                        json_data = json.loads(content)
                    print("  ✅ É JSON válido! Chaves: {list(json_data.keys())[:10]} (usando utf-8 fallback)")
                except json.JSONDecodeError:
                    print("  ❌ Não é JSON válido")
                except Exception as e:
                    print(f"  ❌ Erro ao tentar JSON: {str(e)}")
                
except Exception as e:
    print(f"❌ Erro: {e}")

finally:
    # Não limpar o diretório para podermos inspecionar depois
    print(f"\nArquivos extraídos em: {extract_dir}")
