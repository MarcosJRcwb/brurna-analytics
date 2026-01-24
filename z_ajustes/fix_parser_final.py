from pathlib import Path
import re

# Ler o arquivo do parser
parser_file = Path("src/parser/log_parser.py")
content = parser_file.read_text(encoding='utf-8')

print("=== CORRIGINDO O PARSER DE UMA VEZ ===")

# 1. Primeiro, corrigir a regex
# Encontrar a regex atual
regex_pattern = r"self\.log_pattern = re\.compile\([\s\S]*?\)"
match = re.search(regex_pattern, content)

if match:
    old_regex = match.group(0)
    # Nova regex correta
    new_regex = '''        self.log_pattern = re.compile(
            r'(\\d{2}/\\d{2}/\\d{4})\\\\s+(\\d{2}:\\d{2}:\\d{2})\\\\t'
            r'([A-Z]+)\\\\t'
            r'(\\d+)\\\\t'
            r'([A-Z]+)\\\\t'
            r'(.+?)\\\\t'
            r'([A-F0-9]{16})\\\\s*$'
        )'''

    content = content.replace(old_regex, new_regex)
    print("✅ Regex corrigida")
else:
    print("❌ Não encontrou a regex")

# 2. Adicionar import py7zr se não existir
if "import py7zr" not in content:
    # Adicionar após outros imports
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if line.strip() == "import hashlib":
            new_lines.append("import py7zr")

    content = '\n'.join(new_lines)
    print("✅ Import py7zr adicionado")

# 3. Modificar o método parse_file
# Encontrar o método
method_start = content.find("def parse_file(self")
if method_start != -1:
    # Procurar pelo início do corpo (após os docstrings)
    lines = content[method_start:].split('\n')

    # Reconstruir o método
    new_method = []
    i = 0

    # Adicionar a assinatura do método
    new_method.append(lines[i])
    i += 1

    # Adicionar docstring
    while i < len(lines) and (
            lines[i].strip().startswith('"""') or lines[i].strip().startswith("'''") or lines[i].strip() == ''):
        new_method.append(lines[i])
        i += 1

    # Adicionar código de extração
    new_method.append(
        '        print(f"Parseando arquivo: {self.log_file_path.name} ({self.log_file_path.stat().st_size:,} bytes)")')
    new_method.append('')
    new_method.append('        # Verifica se é arquivo .logjez (compactado)')
    new_method.append('        if str(self.log_file_path).lower().endswith(\'.logjez\'):')
    new_method.append('            import tempfile')
    new_method.append('            with tempfile.TemporaryDirectory() as tmpdir:')
    new_method.append('                print(f"Extraindo arquivo compactado: {self.log_file_path.name}")')
    new_method.append('                with py7zr.SevenZipFile(self.log_file_path, mode=\'r\') as archive:')
    new_method.append('                    archive.extractall(path=tmpdir)')
    new_method.append('                ')
    new_method.append('                # Encontra o arquivo extraído')
    new_method.append('                extracted_files = list(Path(tmpdir).glob(\'*\'))')
    new_method.append('                if not extracted_files:')
    new_method.append('                    raise FileNotFoundError(f"Nenhum arquivo extraído de {self.log_file_path}")')
    new_method.append('                ')
    new_method.append('                # Usa o primeiro arquivo extraído')
    new_method.append('                dat_file = extracted_files[0]')
    new_method.append('                print(f"Arquivo extraído: {dat_file.name}")')
    new_method.append('                file_to_read = dat_file')
    new_method.append('        else:')
    new_method.append('            file_to_read = self.log_file_path')
    new_method.append('')

    # Continuar copiando o resto do método, substituindo self.log_file_path por file_to_read
    while i < len(lines):
        line = lines[i]
        # Substituir referências ao arquivo
        line = line.replace("open(self.log_file_path, 'r'", "open(file_to_read, 'r'")
        line = line.replace("f'Encoding detectado para {self.log_file_path.name}:",
                            "f'Encoding detectado para {file_to_read.name}:")
        new_method.append(line)
        i += 1

    # Substituir o método antigo pelo novo
    # Encontrar o final do método atual
    end_of_method = method_start
    brace_count = 0
    in_method = False

    # Esta lógica é complexa, então vamos usar uma abordagem diferente
    # Vamos reescrever todo o arquivo com o método substituído

    # Dividir o conteúdo em antes e depois do método
    before_method = content[:method_start]

    # Encontrar onde termina o método atual (próxima definição de função)
    remaining = content[method_start:]
    # Procurar pela próxima definição de função que não está indentada
    next_method_match = re.search(r'\n\s*def\s+\w+\(', remaining)
    if next_method_match:
        end_pos = method_start + next_method_match.start()
        after_method = content[end_pos:]
    else:
        after_method = ""
        end_pos = len(content)

    # Juntar tudo
    new_content = before_method + '\n'.join(new_method) + after_method

    parser_file.write_text(new_content, encoding='utf-8')
    print("✅ Método parse_file corrigido para extrair .logjez")
else:
    print("❌ Não encontrou o método parse_file")

print("\n✅ Parser corrigido com sucesso!")