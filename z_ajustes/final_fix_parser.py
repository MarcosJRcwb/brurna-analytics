from pathlib import Path
import re

# Ler o arquivo do parser
parser_file = Path("src/parser/log_parser.py")
content = parser_file.read_text(encoding='utf-8')

print("=== CORRIGINDO O PARSER ===")

# 1. Verificar e adicionar import py7zr se necessário
if "import py7zr" not in content:
    # Adicionar após os outros imports
    import_line = "import hashlib"
    if import_line in content:
        content = content.replace(import_line, f"{import_line}\nimport py7zr")
        print("✅ Adicionado import py7zr")
    else:
        print("⚠️  Não encontrou 'import hashlib' para adicionar py7zr")

# 2. Encontrar o método parse_file
method_start = content.find("def parse_file(self")

if method_start != -1:
    # Encontrar o corpo do método
    lines = content[method_start:].split('\n')
    new_method_lines = []
    i = 0
    in_method = False
    indent_level = 0

    while i < len(lines):
        line = lines[i]

        if "def parse_file" in line and not in_method:
            in_method = True
            new_method_lines.append(line)
            i += 1
            continue

        if in_method:
            # Verificar se é o início de outro método
            if line.strip() and line.startswith("def ") and not line.startswith("        "):
                break

            # Encontrar a linha que começa a lógica de leitura
            if "encodings = ['utf-8'" in line:
                # Inserir código de extração antes desta linha
                indent = line[:len(line) - len(line.lstrip())]

                extraction_code = f'''{indent}        # Verifica se é arquivo .logjez (compactado)
{indent}        if str(self.log_file_path).lower().endswith('.logjez'):
{indent}            import tempfile
{indent}            with tempfile.TemporaryDirectory() as tmpdir:
{indent}                print(f"Extraindo arquivo compactado: {{self.log_file_path.name}}")
{indent}                with py7zr.SevenZipFile(self.log_file_path, mode='r') as archive:
{indent}                    archive.extractall(path=tmpdir)
{indent}                
{indent}                # Encontra o arquivo extraído (logd.dat)
{indent}                extracted_files = list(Path(tmpdir).glob('*'))
{indent}                if not extracted_files:
{indent}                    raise FileNotFoundError(f"Nenhum arquivo extraído de {{self.log_file_path}}")
{indent}                
{indent}                # Usa o primeiro arquivo extraído
{indent}                dat_file = extracted_files[0]
{indent}                print(f"Arquivo extraído: {{dat_file.name}}")
{indent}                file_to_read = dat_file
{indent}        else:
{indent}            file_to_read = self.log_file_path
'''

                new_method_lines.append(extraction_code)
                # Substituir self.log_file_path por file_to_read nas próximas linhas
                # Continuar processando as linhas restantes
                for j in range(i, len(lines)):
                    old_line = lines[j]
                    # Substituir ocorrências de open(self.log_file_path, por open(file_to_read,
                    new_line = old_line.replace("open(self.log_file_path, 'r'", "open(file_to_read, 'r'")
                    new_line = new_line.replace("f\"Encoding detectado para {self.log_file_path.name}:",
                                                "f\"Encoding detectado para {file_to_read.name}:")
                    new_method_lines.append(new_line)

                # Pular o resto das linhas originais
                break
            else:
                new_method_lines.append(line)

        i += 1

    # Juntar as linhas do método modificado
    new_method_content = '\n'.join(new_method_lines)

    # Substituir o método antigo pelo novo
    # Encontrar o final do método antigo
    end_pos = method_start
    brace_count = 0
    in_def = False

    for k in range(method_start, len(content)):
        if content[k:k + 4] == "def " and k != method_start:
            # Início de outra função
            break
        if content[k] == '\n' and k + 1 < len(content) and content[k + 1] != ' ' and content[k + 1] != '\t':
            # Linha vazia seguida de não-indentação pode ser o fim
            pass

        end_pos = k

    # Substituir
    new_content = content[:method_start] + new_method_content + content[end_pos + 1:]

    # 3. Corrigir a regex para usar \\t
    # Encontrar a regex
    regex_pattern = r"self\.log_pattern = re\.compile\([\s\S]*?\)"
    match = re.search(regex_pattern, new_content)

    if match:
        old_regex = match.group(0)
        # Verificar se já tem \\t
        if r"\\t" not in old_regex:
            # Corrigir a regex
            new_regex = '''        self.log_pattern = re.compile(
            r'(\\d{2}/\\d{2}/\\d{4})\\\\s+(\\d{2}:\\d{2}:\\d{2})\\\\t'
            r'([A-Z]+)\\\\t'
            r'(\\d+)\\\\t'
            r'([A-Z]+)\\\\t'
            r'(.+?)\\\\t'
            r'([A-F0-9]{16})\\\\s*$'
        )'''

            new_content = new_content.replace(old_regex, new_regex)
            print("✅ Regex corrigida para usar \\\\t")

    # Salvar o arquivo
    parser_file.write_text(new_content, encoding='utf-8')
    print("✅ Parser corrigido com extração de .logjez!")

else:
    print("❌ Não encontrou o método parse_file")