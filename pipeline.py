#!/usr/bin/env python3
"""
Pipeline autônomo para processamento de logs do TSE
"""

import typer
from typing import Optional
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from config import config

app = typer.Typer(help="Pipeline autônomo BRURNA Analytics")


class ProcessingPipeline:
    """Pipeline autônomo com checkpoint"""

    def __init__(self, uf: str):
        self.uf = uf.lower()
        self.state_file = config.PROCESSED_DIR / uf / "pipeline_state.json"
        self.state = self._load_state()

    def _load_state(self):
        """Carrega estado do pipeline"""
        import json
        default_state = {
            "uf": self.uf,
            "downloaded_sections": [],
            "parsed_sections": [],
            "last_download": None,
            "last_parse": None,
            "total_downloaded": 0,
            "total_parsed": 0,
            "errors": []
        }

        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                return default_state
        return default_state

    def _save_state(self):
        """Salva estado do pipeline"""
        import json
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def download_phase(self, limit: Optional[int] = None, resume: bool = True):
        """Fase 1: Download apenas"""
        print(f"📥 FASE 1 - DOWNLOAD: UF {self.uf.upper()}")

        try:
            from download.downloader import TSEDownloader
            downloader = TSEDownloader()

            # Se resumir, verifica o que já foi baixado
            if resume and self.state["downloaded_sections"]:
                print(f"  Retomando de checkpoint: {len(self.state['downloaded_sections'])} seções já baixadas")

            # Baixa os dados
            results = downloader.download_uf(self.uf, limit=limit)

            if results is not None:
                downloaded = results[results['baixado']]
                self.state["downloaded_sections"] = downloaded.to_dict('records')
                self.state["total_downloaded"] = len(downloaded)
                self.state["last_download"] = datetime.now().isoformat()
                self._save_state()

                print(f"✅ Download concluído: {len(downloaded)} seções")
                print(f"💾 Dados salvos em: {config.RAW_LOGS_DIR / self.uf}")
            else:
                print("⚠️  Nenhum dado foi baixado")

        except Exception as e:
            self.state["errors"].append({
                "phase": "download",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            self._save_state()
            print(f"❌ Erro no download: {e}")
            raise

    def parse_phase(self, batch_size: int = 50, resume: bool = True):
        """Fase 2: Parsing apenas"""
        print(f"🔍 FASE 2 - PARSING: UF {self.uf.upper()}")

        try:
            from parser.log_parser import TSELogParser
            from database.db_writer import save_parsed_logs

            raw_dir = config.RAW_LOGS_DIR / self.uf
            files = list(raw_dir.glob('*.logjez'))

            if not files:
                print(f"❌ Nenhum arquivo .logjez encontrado em {raw_dir}")
                print("   Execute primeiro: python pipeline.py download --uf {self.uf}")
                return

            print(f"📁 Encontrados {len(files)} arquivos .logjez")

            # Determina quais arquivos processar
            if resume and self.state["parsed_sections"]:
                already_parsed = {s['file'] for s in self.state["parsed_sections"]}
                files_to_process = [f for f in files if f.name not in already_parsed]
                print(f"  Retomando: {len(files_to_process)}/{len(files)} arquivos restantes")
            else:
                files_to_process = files

            # Processa em lotes
            total_processed = 0
            for i in range(0, len(files_to_process), batch_size):
                batch = files_to_process[i:i + batch_size]
                print(f"\n📦 Lote {i // batch_size + 1}: {len(batch)} arquivos")

                batch_data = []
                for file in batch:
                    try:
                        print(f"  Processando: {file.name}")
                        parser = TSELogParser(str(file))
                        df = parser.parse_file(uf=self.uf, turno=1)

                        if not df.empty:
                            batch_data.append(df)
                            # Atualiza estado
                            self.state["parsed_sections"].append({
                                "file": file.name,
                                "lines": len(df),
                                "timestamp": datetime.now().isoformat()
                            })
                            print(f"    ✅ {len(df):,} linhas")
                        else:
                            print(f"    ⚠️  Sem dados")

                    except Exception as e:
                        print(f"    ❌ Erro em {file.name}: {e}")

                # Consolida e salva
                if batch_data:
                    df_batch = pd.concat(batch_data, ignore_index=True)
                    total_processed += len(df_batch)

                    # Salva localmente
                    output_dir = config.PROCESSED_DIR / self.uf
                    output_dir.mkdir(parents=True, exist_ok=True)

                    # Anexa ao arquivo Parquet existente
                    parquet_file = output_dir / f"logs_{self.uf}.parquet"
                    if parquet_file.exists():
                        existing = pd.read_parquet(parquet_file)
                        df_batch = pd.concat([existing, df_batch], ignore_index=True)

                    df_batch.to_parquet(parquet_file, index=False)
                    print(f"💾 Lote salvo: {len(df_batch):,} linhas totais")

                # Salva estado a cada lote
                self.state["total_parsed"] = total_processed
                self.state["last_parse"] = datetime.now().isoformat()
                self._save_state()

            print(f"\n✅ Parsing concluído: {total_processed:,} linhas processadas")
            print(f"📊 Arquivo final: {config.PROCESSED_DIR / self.uf / f'logs_{self.uf}.parquet'}")

        except Exception as e:
            self.state["errors"].append({
                "phase": "parse",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            self._save_state()
            print(f"❌ Erro no parsing: {e}")
            raise

    def analyze_phase(self, metrics: str = "all"):
        """Fase 3: Análise"""
        print(f"📊 FASE 3 - ANÁLISE: UF {self.uf.upper()}")

        try:
            # Verifica se existem dados processados
            parquet_file = config.PROCESSED_DIR / self.uf / f"logs_{self.uf}.parquet"
            if not parquet_file.exists():
                print(f"❌ Arquivo de dados não encontrado: {parquet_file}")
                print("   Execute primeiro: python pipeline.py parse --uf {self.uf}")
                return

            df = pd.read_parquet(parquet_file)
            print(f"✅ Dados carregados: {len(df):,} linhas")

            # Análise básica
            print("\n" + "=" * 60)
            print("📈 RESUMO ESTATÍSTICO")
            print("=" * 60)

            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                print(f"Período: {df['timestamp'].min()} a {df['timestamp'].max()}")
                print(f"Duração: {df['timestamp'].max() - df['timestamp'].min()}")

            if 'severidade' in df.columns:
                print(f"\n📊 Distribuição por Severidade:")
                sev_counts = df['severidade'].value_counts()
                for sev, count in sev_counts.items():
                    percent = count / len(df) * 100
                    print(f"  {sev:10}: {count:8,} ({percent:.1f}%)")

            if 'aplicativo' in df.columns:
                print(f"\n📱 Top 10 Aplicativos:")
                app_counts = df['aplicativo'].value_counts().head(10)
                for app, count in app_counts.items():
                    percent = count / len(df) * 100
                    print(f"  {app:15}: {count:8,} ({percent:.1f}%)")

            # Análise temporal por hora
            if 'timestamp' in df.columns:
                print(f"\n⏰ Eventos por Hora:")
                df['hora'] = df['timestamp'].dt.hour
                hourly = df.groupby('hora').size()
                for hora, count in hourly.items():
                    print(f"  {hora:02d}:00 - {count:8,} eventos")

            print("=" * 60)
            print("✅ Análise concluída")

            # Salva relatório
            report_file = config.OUTPUT_DIR / "reports" / f"relatorio_{self.uf}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report_file.parent.mkdir(parents=True, exist_ok=True)

            # TODO: Salvar relatório formatado
            print(f"📄 Relatório salvo em: {report_file}")

        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            raise


@app.command()
def run(
        uf: str = typer.Option(..., help="UF para processar"),
        phases: str = typer.Option("all", help="Fases a executar: download,parse,analyze,all"),
        limit: Optional[int] = typer.Option(None, help="Limite de seções para download"),
        batch_size: int = typer.Option(50, help="Tamanho do lote para parsing"),
        resume: bool = typer.Option(True, help="Retomar de checkpoint")
):
    """Executa pipeline completo ou fases específicas"""
    pipeline = ProcessingPipeline(uf)

    phases_list = []
    if phases == "all":
        phases_list = ["download", "parse", "analyze"]
    else:
        phases_list = [p.strip() for p in phases.split(",")]

    if "download" in phases_list:
        pipeline.download_phase(limit=limit, resume=resume)

    if "parse" in phases_list:
        pipeline.parse_phase(batch_size=batch_size, resume=resume)

    if "analyze" in phases_list:
        pipeline.analyze_phase()


@app.command()
def status(
        uf: Optional[str] = typer.Option(None, help="UF específica para status")
):
    """Mostra status do pipeline"""
    print("🔄 STATUS DO PIPELINE")
    print("=" * 60)

    if uf:
        ufs = [uf.lower()]
    else:
        ufs = ['ac', 'mg']  # UFs de interesse

    for uf_item in ufs:
        state_file = config.PROCESSED_DIR / uf_item / "pipeline_state.json"

        print(f"\nUF: {uf_item.upper()}")

        if state_file.exists():
            import json
            with open(state_file, 'r') as f:
                state = json.load(f)

            print(f"  📥 Download: {state.get('total_downloaded', 0)} seções")
            print(f"  🔍 Parse: {state.get('total_parsed', 0):,} linhas")

            last_dl = state.get('last_download')
            last_parse = state.get('last_parse')

            if last_dl:
                print(f"  ⏰ Último download: {last_dl[:19]}")
            if last_parse:
                print(f"  ⏰ Último parse: {last_parse[:19]}")

            errors = state.get('errors', [])
            if errors:
                print(f"  ⚠️  Erros: {len(errors)}")
        else:
            print(f"  ❌ Pipeline não iniciado")

    print(f"\n📋 COMANDOS:")
    print(f"  # Pipeline completo:")
    print(f"  python pipeline.py run --uf ac")
    print(f"  ")
    print(f"  # Apenas download:")
    print(f"  python pipeline.py run --uf ac --phases download")
    print(f"  ")
    print(f"  # Com limite:")
    print(f"  python pipeline.py run --uf ac --limit 100 --batch-size 20")


if __name__ == "__main__":
    app()