import py7zr
import tempfile
import re
from pathlib import Path
from datetime import datetime
import pandas as pd

# Primeiro, vamos corrigir o parser no arquivo
parser_file = Path("src/parser/log_parser.py")
content = parser_file.read_text(encoding='utf-8')

# Encontrar e substituir a regex corretamente
# A regex atual está errada - precisamos de \\t para representar um caractere de tabulação
# Mas na string raw do Python, \\t é interpretado como um caractere de tabulação
# Então precisamos usar \\\\t para escapar na string raw

# Vamos criar a regex correta
new_regex = '''        self.log_pattern = re.compile(
            r'(\\d{2}/\\d{2}/\\d{4})\\\\s+(\\d{2}:\\d{2}:\\d{2})\\\\t'
            r'([A-Z]+)\\\\t'
            r'(\\d+)\\\\t'
            r'([A-Z]+)\\\\t'
            r'(.+?)\\\\t'
            r'([A-F0-9]{16})\\\\s*$'
        )'''

# Encontrar a posição da regex antiga
start = content.find('self.log_pattern = re.compile(')
if start != -1:
    # Encontrar o fim da regex
    end = content.find(')', start)
    # Procurar pelo fechamento final
    paren_count = 1
    for i in range(start + 1, len(content)):
        if content[i] == '(':
            paren_count += 1
        elif content[i] == ')':
            paren_count -= 1
            if paren_count == 0:
                end = i + 1
                break

    # Substituir
    content = content[:start] + new_regex + content[end:]

    # Salvar
    parser_file.write_text(content, encoding='utf-8')
    print("✅ Regex corrigida no parser!")
else:
    print("❌ Não encontrou a regex no parser!")

# Agora vamos testar com uma abordagem direta
print("\n=== TESTANDO PARSER DIRETAMENTE ===")

# Caminho do arquivo .logjez
logjez_file = Path(r"C:\Users\marco\Downloads\TSE\data\raw_logs\ac\o00407-0106600040077.logjez")

# Extrair o arquivo .logjez
with tempfile.TemporaryDirectory() as tmpdir:
    print(f"Extraindo {logjez_file.name}...")
    with py7zr.SevenZipFile(logjez_file, mode='r') as archive:
        archive.extractall(path=tmpdir)

    # Encontrar o arquivo extraído (logd.dat)
    extracted_files = list(Path(tmpdir).glob('*'))
    if not extracted_files:
        print("❌ Nenhum arquivo extraído!")
    else:
        dat_file = extracted_files[0]
        print(f"Arquivo extraído: {dat_file.name}")

        # Ler o arquivo com encoding latin-1
        with open(dat_file, 'r', encoding='latin-1') as f:
            lines = f.readlines()

        print(f"Total de linhas: {len(lines)}")

        # Regex corrigida
        pattern = re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\t'
            r'([A-Z]+)\t'
            r'(\d+)\t'
            r'([A-Z]+)\t'
            r'(.+?)\t'
            r'([A-F0-9]{16})\s*$'
        )

        # Testar as primeiras 5 linhas
        print("\nTestando as primeiras 5 linhas:")
        for i in range(min(5, len(lines))):
            line = lines[i].strip()
            match = pattern.match(line)
            if match:
                print(f"Linha {i + 1}: ✅ MATCH")
                print(f"  Data: {match.group(1)}, Hora: {match.group(2)}")
                print(f"  Severidade: {match.group(3)}")
                print(f"  ID UE: {match.group(4)}")
                print(f"  Aplicativo: {match.group(5)}")
                print(f"  Mensagem: {match.group(6)[:50]}...")
                print(f"  MAC: {match.group(7)}")
            else:
                print(f"Linha {i + 1}: ❌ NO MATCH")
                print(f"  Conteúdo: {line[:100]}")