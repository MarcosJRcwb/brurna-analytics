import tempfile
import sys
from pathlib import Path

# Carrega o arquivo do parser
parser_file = Path("src/parser/log_parser.py")
content = parser_file.read_text(encoding='utf-8')

# Verifica se já temos os imports necessários
if "import tempfile" not in content:
    # Adiciona import tempfile após os outros imports
    import_line = "import hashlib"
    if import_line in content:
        content = content.replace(import_line, f"{import_line}\nimport tempfile")

# Agora vamos modificar o método parse_file para extrair o .logjez
# Vamos encontrar o início do método parse_file
parse_method_start = content.find("def parse_file(self")

if parse_method_start != -1:
    # Encontrar o início do corpo do método
    body_start = content.find("):", parse_method_start) + 2
    # Encontrar a primeira linha com indentação
    lines = content[body_start:].split('\n')
    indent_level = None
    for i, line in enumerate(lines):
        if line.strip() and not line.strip().startswith('#'):
            # Contar espaços iniciais
            indent_level = len(line) - len(line.lstrip())
            break

    if indent_level is not None:
        # Preparar o código para extração
        indent = ' ' * indent_level

        # Código para extrair .logjez
        extraction_code = f'''
{indent}        # Verifica se é arquivo .logjez (compactado)
{indent}        if self.log_file_path.suffix.lower() == '.logjez':
{indent}            with tempfile.TemporaryDirectory() as tmpdir:
{indent}                import py7zr
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
{indent}                
{indent}                # Lê o arquivo extraído
{indent}                lines = None
{indent}                detected_encoding = None
{indent}        else:
{indent}            # Arquivo já é logd.dat
{indent}            dat_file = self.log_file_path
{indent}            lines = None
{indent}            detected_encoding = None
'''

        # Encontrar onde começa a lógica de leitura atual
        # Procura por "encodings = ['utf-8'"
        encodings_start = content.find("encodings = ['utf-8'", body_start)

        if encodings_start != -1:
            # Encontrar a linha "lines = None" antes disso
            lines_none_start = content.rfind("lines = None", body_start, encodings_start)

            if lines_none_start != -1:
                # Encontrar o final da seção de inicialização
                # Procura pela próxima linha com menos indentação ou a linha de encodings
                lines_before = content[lines_none_start:encodings_start].split('\n')
                for i, line in enumerate(lines_before):
                    if "detected_encoding = None" in line:
                        end_of_init = lines_none_start + sum(len(l) + 1 for l in lines_before[:i + 1])
                        break
                else:
                    end_of_init = encodings_start

                # Substituir a seção de inicialização
                content = content[:lines_none_start] + extraction_code + content[end_of_init:]

                # Agora precisamos ajustar o resto do código para usar dat_file em vez de self.log_file_path
                # Encontra todas as ocorrências de "open(self.log_file_path" e substitui por "open(dat_file"
                content = content.replace("open(self.log_file_path, 'r'", "open(dat_file, 'r'")
                content = content.replace("open(self.log_file_path, 'r'", "open(dat_file, 'r'")  # Dupla verificação

                parser_file.write_text(content, encoding='utf-8')
                print("✅ Parser corrigido para extrair arquivos .logjez!")
            else:
                print("❌ Não encontrou a inicialização de 'lines = None'")
        else:
            print("❌ Não encontrou a lista de encodings")
    else:
        print("❌ Não conseguiu determinar o nível de indentação")
else:
    print("❌ Não encontrou o método parse_file")