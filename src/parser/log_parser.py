"""
Parser para arquivos logd.dat do sistema eletrônico de votação do TSE
Baseado na documentação oficial: formato-arquivos-log.pdf
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import hashlib
import py7zr


class TSELogParser:
    """Parser para logs do sistema de votação eletrônica do TSE"""

    def __init__(self, log_file_path: str):
        """
        Inicializa o parser com o caminho do arquivo logd.dat

        Args:
            log_file_path: Caminho para o arquivo logd.dat ou .logjez
        """
        self.log_file_path = Path(log_file_path)
        self.parsed_data = []
        self.metadata = {}
        self.validation_results = {}

        # Expressão regular para parsing (corrigida para formato real com TABs)
        self.log_pattern = re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\t'
            r'([A-Z]+)\t'
            r'(\d+)\t'
            r'([A-Z]+)\t'
            r'(.+?)\t'
            r'([A-F0-9]{16})\s*$'
        )

    def _extract_section_info_from_filename(self) -> dict:
        """
        Extrai informações da seção do nome do arquivo.
        
        Exemplo: o00407-0106600040077.logjez
        - municipio_codigo: 01066
        - zona: 0004
        - secao: 0077
        
        Returns:
            Dicionário com municipio_codigo, zona, secao, hash_arquivo
        """
        nome_base = self.log_file_path.stem  # Remove extensão
        
        # Calcula hash do arquivo
        hash_arquivo = None
        try:
            sha256 = hashlib.sha256()
            with open(self.log_file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            hash_arquivo = sha256.hexdigest()
        except:
            pass
        
        # Tenta extrair informações do nome
        if '-' in nome_base:
            partes = nome_base.split('-')
            if len(partes) > 1:
                codigo_secao = partes[1]
                if len(codigo_secao) >= 13:
                    return {
                        'municipio_codigo': codigo_secao[:5],
                        'zona': codigo_secao[5:9],
                        'secao': codigo_secao[9:13],
                        'hash_arquivo': hash_arquivo
                    }
        
        return {'hash_arquivo': hash_arquivo}

    def parse_file(self) -> pd.DataFrame:
        """
        Parseia o arquivo logd.dat (ou extrai de .logjez)

        Returns:
            DataFrame com todas as linhas parseadas
        """
        if str(self.log_file_path).lower().endswith('.logjez'):
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                with py7zr.SevenZipFile(self.log_file_path, mode='r') as archive:
                    archive.extractall(path=tmpdir)

                extracted_files = list(Path(tmpdir).glob('*'))
                if not extracted_files:
                    raise FileNotFoundError(f"Nenhum arquivo extraído de {self.log_file_path}")

                dat_file = extracted_files[0]
                return self._read_dat_file(dat_file)
        else:
            return self._read_dat_file(self.log_file_path)

    def _read_dat_file(self, file_path: Path) -> pd.DataFrame:
        """Lê o arquivo .dat e parseia o conteúdo"""
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        lines = None
        detected_encoding = None

        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    lines = f.readlines()
                detected_encoding = enc
                break
            except (UnicodeDecodeError, Exception):
                continue

        if lines is None:
            raise Exception(f"Não foi possível ler o arquivo em nenhum encoding: {encodings}")

        parsed_lines = []
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line: continue

            match = self.log_pattern.match(line)
            if match:
                data, hora, severidade, id_ue, aplicativo, mensagem, mac = match.groups()
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

        self.parsed_data = pd.DataFrame(parsed_lines)
        self._extract_metadata()
        return self.parsed_data

    def _extract_metadata(self):
        """Extrai metadados do log parseado"""
        if self.parsed_data.empty: return
        
        valid_df = self.parsed_data[self.parsed_data['severidade'] != 'INVALID']
        
        # Extrai modelo de urna via regex (geralmente nas primeiras mensagens)
        modelo_urna = None
        # Busca no DataFrame completo, pois a mensagem de solução pode estar no início
        # Usamos uma busca otimizada nas primeiras 500 linhas que é onde o boot acontece
        sample = self.parsed_data['mensagem'].head(500).tolist()
        for msg in sample:
            match = re.search(r'(UE\d{4})', msg, re.IGNORECASE)
            if match:
                modelo_urna = match.group(1).upper()
                break

        if not valid_df.empty:
            self.metadata = {
                'total_linhas': len(self.parsed_data),
                'linhas_validas': len(valid_df),
                'periodo_inicio': valid_df['timestamp'].min(),
                'periodo_fim': valid_df['timestamp'].max(),
                'id_ue': valid_df['id_ue'].iloc[0] if 'id_ue' in valid_df.columns else None,
                'modelo_urna': modelo_urna
            }
