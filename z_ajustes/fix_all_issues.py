from pathlib import Path
import re

# 1. Remover BOM do arquivo log_parser.py
parser_file = Path("src/parser/log_parser.py")
content_bytes = parser_file.read_bytes()

# Remover BOM se existir
if content_bytes.startswith(b'\xef\xbb\xbf'):
    content_bytes = content_bytes[3:]
    parser_file.write_bytes(content_bytes)
    print("✅ BOM removido")

# Ler o conteúdo como texto
content = parser_file.read_text(encoding='utf-8')

# 2. Corrigir o problema de escopo do arquivo temporário
# O problema: file_to_read é definido dentro do bloco with, mas quando sai do bloco,
# o diretório temporário é excluído, então o arquivo não existe mais.

# Encontrar a parte onde lê o arquivo após a extração
# Precisamos modificar a lógica para ler o conteúdo DENTRO do bloco with

# Padrão para encontrar a extração e leitura
pattern = r'if str\(self\.log_file_path\)\.lower\(\)\.endswith\(\'\.logjez\'\):(.*?)file_to_read = self\.log_file_path'

# Substituir por uma lógica que lê o conteúdo dentro do bloco with
new_extraction_logic = '''if str(self.log_file_path).lower().endswith('.logjez'):
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                print(f"Extraindo arquivo compactado: {self.log_file_path.name}")
                with py7zr.SevenZipFile(self.log_file_path, mode='r') as archive:
                    archive.extractall(path=tmpdir)

                # Encontra o arquivo extraído (logd.dat)
                extracted_files = list(Path(tmpdir).glob('*'))
                if not extracted_files:
                    raise FileNotFoundError(f"Nenhum arquivo extraído de {self.log_file_path}")

                # Usa o primeiro arquivo extraído
                dat_file = extracted_files[0]
                print(f"Arquivo extraído: {dat_file.name} (existe: {dat_file.exists()})")

                # Lê o conteúdo DENTRO do bloco with para evitar problemas de escopo
                file_to_read = dat_file

                # Agora tenta diferentes encodings
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                lines = None
                detected_encoding = None

                for enc in encodings:
                    try:
                        with open(file_to_read, 'r', encoding=enc) as f:
                            lines = f.readlines()
                        detected_encoding = enc
                        print(f"Encoding detectado para {file_to_read.name}: {detected_encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        print(f"Erro ao tentar encoding {enc}: {str(e)}")
                        continue

                if lines is None:
                    raise Exception(f"Não foi possível ler o arquivo em nenhum encoding testado: {encodings}")

                # Processa as linhas (o resto do código permanece o mesmo)
                parsed_lines = []
                line_count = len(lines)

                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # Tenta parsear com o padrão
                    match = self.log_pattern.match(line)
                    if match:
                        data, hora, severidade, id_ue, aplicativo, mensagem, mac = match.groups()

                        # Cria datetime combinado
                        timestamp = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M:%S")

                        parsed_lines.append({
                            'linha_numero': i,
                            'timestamp': timestamp,
                            'data': data,
                            'hora': hora,
                            'severidade': severidade,
                            'id_ue': int(id_ue),
                            'aplicativo': aplicativo,
                            'mensagem': mensagem.strip(),
                            'mac': mac,
                            'raw_line': line,
                            'encoding_detectado': detected_encoding
                        })
                    else:
                        # Log de linhas que não seguem o padrão
                        parsed_lines.append({
                            'linha_numero': i,
                            'timestamp': None,
                            'data': None,
                            'hora': None,
                            'severidade': 'INVALID',
                            'id_ue': None,
                            'aplicativo': None,
                            'mensagem': line,
                            'mac': None,
                            'raw_line': line,
                            'encoding_detectado': detected_encoding
                        })

                    # Progresso
                    if i % 1000 == 0:
                        print(f"  Processadas {i:,}/{line_count:,} linhas...")

                self.parsed_data = pd.DataFrame(parsed_lines)
                print(f"✓ Parseamento concluído: {len(self.parsed_data):,} linhas processadas")

                # Extrai metadados
                self._extract_metadata()

                # Salvamento no banco (se uf e turno forem informados)
                if uf is not None:
                    try:
                        from src.database.db_writer import save_parsed_logs
                        save_parsed_logs(self.parsed_data, uf=uf, turno=turno)
                    except ImportError:
                        print("Módulo db_writer não encontrado. Salvamento no banco ignorado.")
                    except Exception as e:
                        print(f"Erro ao salvar no banco: {str(e)}")

                return self.parsed_data
        else:
            # Se não for .logjez, continua com a lógica original
            file_to_read = self.log_file_path
'''

# Usar regex para fazer a substituição
content = re.sub(pattern, new_extraction_logic, content, flags=re.DOTALL)

# Remover a parte duplicada (a lógica de leitura que vem depois)
# Encontrar onde começa a lógica duplicada após o else
else_pos = content.find("file_to_read = self.log_file_path")
if else_pos != -1:
    # Encontrar onde termina a lógica de leitura (próximo método ou fim do método)
    # Vamos procurar por "encodings = ['utf-8'" que seria duplicado
    encodings_pos = content.find("encodings = ['utf-8'", else_pos + 50)
    if encodings_pos != -1:
        # Encontrar o final do método parse_file
        # Procurar por "def " ou "    def " após esta posição
        next_def_pos = content.find("\n    def ", encodings_pos)
        if next_def_pos == -1:
            next_def_pos = content.find("\ndef ", encodings_pos)

        if next_def_pos != -1:
            # Remover a lógica duplicada
            content = content[:else_pos] + content[next_def_pos:]
        else:
            # Se não encontrar outro método, remover até o final
            content = content[:else_pos]

# Salvar o arquivo corrigido
parser_file.write_text(content, encoding='utf-8')
print("✅ Lógica de extração corrigida para evitar problema de escopo")

# 3. Testar a sintaxe
import ast

try:
    ast.parse(content)
    print("✅ Sintaxe Python válida")
except SyntaxError as e:
    print(f"❌ Erro de sintaxe: {e}")
    print(f"Linha {e.lineno}: {e.text}")