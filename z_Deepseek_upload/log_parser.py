"""
Parser para arquivos logd.dat do sistema eletrônico de votação do TSE
Baseado na documentação oficial: formato-arquivos-log.pdf
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import hashlib
import tempfile
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

    def parse_file(self, uf: str = None, turno: int = 1) -> pd.DataFrame:
        """
        Parseia o arquivo logd.dat (ou extrai de .logjez)

        Returns:
            DataFrame com todas as linhas parseadas
        """
        print(f"Parseando arquivo: {self.log_file_path.name} ({self.log_file_path.stat().st_size:,} bytes)")

        # Se for arquivo .logjez, extrai primeiro

        if str(self.log_file_path).lower().endswith('.logjez'):
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

    def _extract_metadata(self):
        """Extrai metadados do log parseado"""
        if self.parsed_data.empty:
            return

        df = self.parsed_data

        # Filtra apenas linhas válidas
        valid_df = df[df['severidade'] != 'INVALID']

        if not valid_df.empty:
            self.metadata = {
                'total_linhas': len(df),
                'linhas_validas': len(valid_df),
                'linhas_invalidas': len(df) - len(valid_df),
                'periodo_inicio': valid_df['timestamp'].min(),
                'periodo_fim': valid_df['timestamp'].max(),
                'id_ue': valid_df['id_ue'].iloc[0] if 'id_ue' in valid_df.columns else None,
                'aplicativos': list(valid_df['aplicativo'].unique()),
                'severidades': dict(valid_df['severidade'].value_counts()),
                'duracao_total': valid_df['timestamp'].max() - valid_df['timestamp'].min()
            }

        # Os outros métodos (analyze_temporal_patterns, find_errors_and_alerts, etc.)
        # podem ser mantidos como estão, mas por brevidade vamos só incluir o essencial.

    def analyze_temporal_patterns(self) -> dict:
        """Analisa padrões temporais no log"""
        if self.parsed_data.empty:
            return {}

        df = self.parsed_data

        # Filtra apenas linhas com timestamp válido
        time_df = df[df['timestamp'].notna()].copy()

        if len(time_df) < 2:
            return {}

        # Ordena por timestamp
        time_df = time_df.sort_values('timestamp')

        # Calcula intervalos entre eventos
        time_df['intervalo_segundos'] = time_df['timestamp'].diff().dt.total_seconds()

        # Métricas temporais
        analysis = {
            'eventos_por_hora': time_df.groupby(time_df['timestamp'].dt.hour).size().to_dict(),
            'intervalo_medio': time_df['intervalo_segundos'].mean(),
            'intervalo_mediano': time_df['intervalo_segundos'].median(),
            'intervalo_maximo': time_df['intervalo_segundos'].max(),
            'intervalo_minimo': time_df['intervalo_segundos'].min(),
            'periodos_inatividade': [],  # Lógica para inatividade >5min
            'picos_atividade': []  # Lógica para picos
        }

        # Lógica para periodos de inatividade >5 min
        inatividade = time_df[time_df['intervalo_segundos'] > 300]  # 5 min = 300s
        for idx, row in inatividade.iterrows():
            analysis['periodos_inatividade'].append({
                'inicio': time_df.loc[idx - 1, 'timestamp'],
                'fim': row['timestamp'],
                'duracao_segundos': row['intervalo_segundos']
            })

        # Lógica para picos (ex.: > média + 2 std)
        media = analysis['intervalo_medio']
        std = time_df['intervalo_segundos'].std()
        picos = time_df[time_df['intervalo_segundos'] < media - 2 * std]  # Intervalos curtos = picos de atividade
        for idx, row in picos.iterrows():
            analysis['picos_atividade'].append({
                'timestamp': row['timestamp'],
                'eventos': 1,  # Pode contar eventos próximos
                'intensidade': (media - row['intervalo_segundos']) / std
            })

        return analysis

    def find_errors_and_alerts(self) -> pd.DataFrame:
        """Encontra erros e alertas no log"""
        df = self.parsed_data

        errors = df[df['severidade'].isin(['ERRO', 'ALERTA', 'INVALID'])]

        return errors

    def export_to_csv(self, output_path: str):
        """Exporta dados parseados para CSV"""
        if not self.parsed_data.empty:
            self.parsed_data.to_csv(output_path, index=False, encoding='utf-8')
            print(f"✓ Dados exportados para: {output_path}")

    def generate_report(self) -> str:
        """Gera um relatório textual da análise"""
        report_lines = [
            "=" * 60,
            "RELATÓRIO DE ANÁLISE DE LOG DO TSE",
            "=" * 60,
            f"Arquivo analisado: {self.log_file_path.name}",
            f"Tamanho: {self.log_file_path.stat().st_size:,} bytes",
            f"Data da análise: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ""
        ]

        # Metadados
        if self.metadata:
            report_lines.extend([
                "METADADOS DO LOG:",
                "-" * 40,
                f"Total de linhas: {self.metadata.get('total_linhas', 0):,}",
                f"Linhas válidas: {self.metadata.get('linhas_validas', 0):,}",
                f"Linhas inválidas: {self.metadata.get('linhas_invalidas', 0):,}",
                f"Período: {self.metadata.get('periodo_inicio')} a {self.metadata.get('periodo_fim')}",
                f"Duração total: {self.metadata.get('duracao_total', 'N/A')}",
                f"ID da UE: {self.metadata.get('id_ue', 'N/A')}",
                ""
            ])

        # Resumo por aplicativo
        app_summary = {}
        if not self.parsed_data.empty:
            df = self.parsed_data
            valid_df = df[df['severidade'] != 'INVALID']
            if not valid_df.empty:
                for app in valid_df['aplicativo'].unique():
                    app_df = valid_df[valid_df['aplicativo'] == app]
                    app_summary[app] = {
                        'total_eventos': len(app_df),
                        'periodo_inicio': app_df['timestamp'].min(),
                        'periodo_fim': app_df['timestamp'].max(),
                        'severidades': dict(app_df['severidade'].value_counts())
                    }

        if app_summary:
            report_lines.extend([
                "RESUMO POR APLICATIVO:",
                "-" * 40
            ])

            for app, stats in app_summary.items():
                report_lines.append(f"\n{app}:")
                report_lines.append(f"  Eventos: {stats['total_eventos']:,}")
                report_lines.append(f"  Período: {stats['periodo_inicio']} a {stats['periodo_fim']}")

                if 'severidades' in stats:
                    sev_str = ', '.join([f"{k}: {v}" for k, v in stats['severidades'].items()])
                    report_lines.append(f"  Severidades: {sev_str}")

            report_lines.append("")

        # Análise temporal
        temporal = self.analyze_temporal_patterns()
        if temporal:
            report_lines.extend([
                "ANÁLISE TEMPORAL:",
                "-" * 40,
                f"Intervalo médio entre eventos: {temporal.get('intervalo_medio', 0):.2f} segundos",
                f"Intervalo máximo: {temporal.get('intervalo_maximo', 0):.2f} segundos",
                f"Intervalo mínimo: {temporal.get('intervalo_minimo', 0):.2f} segundos",
                ""
            ])

        # Erros e alertas
        errors = self.find_errors_and_alerts()
        if not errors.empty:
            report_lines.extend([
                "ERROS E ALERTAS DETECTADOS:",
                "-" * 40,
                f"Total: {len(errors)} eventos",
                ""
            ])

            for severity in ['ERRO', 'ALERTA', 'INVALID']:
                severity_df = errors[errors['severidade'] == severity]
                if not severity_df.empty:
                    report_lines.append(f"{severity} ({len(severity_df)}):")
                    for _, row in severity_df.head(5).iterrows():
                        report_lines.append(f"  Linha {row['linha_numero']}: {row['mensagem'][:80]}...")
                    if len(severity_df) > 5:
                        report_lines.append(f"  ... e mais {len(severity_df) - 5} eventos")
                    report_lines.append("")

        # Validação de integridade (simplificada)
        if not self.parsed_data.empty:
            valid_mac = self.parsed_data['mac'].notna().sum()
            total = len(self.parsed_data)
            report_lines.extend([
                "VALIDAÇÃO DE INTEGRIDADE:",
                "-" * 40,
                f"Linhas com MAC válido: {valid_mac:,}",
                f"Linhas sem MAC: {total - valid_mac:,}",
                ""
            ])

        report_lines.append("=" * 60)

        return "\n".join(report_lines)
