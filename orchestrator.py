#!/usr/bin/env python3
"""
Orquestrador Paralelo do BRURNA Analytics
Gerencia download, parsing e inserção no banco de forma paralela
"""

import typer
from typing import Optional
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
import sys
from tqdm import tqdm
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Adiciona src ao path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

from config import config

app = typer.Typer(help="Orquestrador Paralelo BRURNA Analytics")


class ProcessStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PARSING = "parsing"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SectionTask:
    """Tarefa para processamento de uma seção"""
    uf: str
    municipio_codigo: str
    municipio_nome: str
    zona: str
    secao: str
    turno: int = 1
    status: ProcessStatus = ProcessStatus.PENDING
    download_path: Optional[Path] = None
    parsed_data: Optional[pd.DataFrame] = None
    error: Optional[str] = None


class ParallelProcessor:
    """Processador paralelo com checkpoint"""

    def __init__(self, max_download_workers: int = 5, max_parse_workers: int = 3):
        self.max_download_workers = max_download_workers
        self.max_parse_workers = max_parse_workers
        self.state_file = config.PROCESSED_DIR / "parallel_state.json"

    async def download_section_async(self, downloader, task: SectionTask) -> SectionTask:
        """Download assíncrono de uma seção"""
        try:
            task.status = ProcessStatus.DOWNLOADING

            # Cria caminho do arquivo
            filename = f"o00407-{task.municipio_codigo}{task.zona}{task.secao}.logjez"
            task.download_path = config.RAW_LOGS_DIR / task.uf / filename

            # Verifica se já existe
            if task.download_path.exists():
                task.status = ProcessStatus.COMPLETED
                return task

            # Baixa a seção
            success = downloader.download_section(
                task.uf, task.municipio_codigo, task.municipio_nome,
                task.zona, task.secao
            )

            if success:
                task.status = ProcessStatus.COMPLETED
            else:
                task.status = ProcessStatus.FAILED
                task.error = "Download failed"

        except Exception as e:
            task.status = ProcessStatus.FAILED
            task.error = str(e)

        return task

    def parse_section(self, task: SectionTask) -> SectionTask:
        """Parsing de uma seção (pode ser em processo separado)"""
        try:
            task.status = ProcessStatus.PARSING

            from parser.log_parser import TSELogParser

            if not task.download_path or not task.download_path.exists():
                task.status = ProcessStatus.FAILED
                task.error = "Arquivo não encontrado"
                return task

            # Parse do arquivo
            parser = TSELogParser(str(task.download_path))
            df = parser.parse_file(uf=task.uf, turno=task.turno)

            if df.empty:
                task.status = ProcessStatus.FAILED
                task.error = "Nenhum dado extraído"
                return task

            task.parsed_data = df
            task.status = ProcessStatus.SAVING

        except Exception as e:
            task.status = ProcessStatus.FAILED
            task.error = str(e)

        return task

    def save_to_database(self, task: SectionTask) -> SectionTask:
        """Salva dados no banco"""
        try:
            from database.db_writer import save_parsed_logs

            if task.parsed_data is not None and not task.parsed_data.empty:
                save_parsed_logs(task.parsed_data, uf=task.uf, turno=task.turno)
                task.status = ProcessStatus.COMPLETED
            else:
                task.status = ProcessStatus.FAILED
                task.error = "Sem dados para salvar"

        except Exception as e:
            task.status = ProcessStatus.FAILED
            task.error = str(e)

        return task

    async def process_uf_parallel(self, uf: str, limit: int = None,
                                  batch_size: int = 100):
        """Processa uma UF de forma paralela"""
        print(f"🚀 Iniciando processamento paralelo da UF {uf.upper()}")

        try:
            from download.downloader import TSEDownloader
            downloader = TSEDownloader()

            # 1. Obter lista de seções
            print(f"📋 Obtendo metadados da UF {uf}...")
            metadata_url = f"{config.TSE_BASE_URL}/config/{uf}/{uf}-p000407-cs.json"

            import requests
            response = requests.get(metadata_url, headers=downloader.headers)
            config_data = response.json()

            # Criar tarefas
            tasks = []
            for municipio in config_data['abr'][0]['mu'][:limit]:
                for zonas in municipio['zon']:
                    for sec in zonas['sec']:
                        task = SectionTask(
                            uf=uf,
                            municipio_codigo=municipio['cd'],
                            municipio_nome=municipio['nm'],
                            zona=zonas['cd'],
                            secao=sec['ns']
                        )
                        tasks.append(task)

            print(f"🎯 Total de tarefas: {len(tasks)}")

            # 2. Processamento paralelo com TQDM
            total = len(tasks)

            with tqdm(total=total, desc="Download") as pbar_download, \
                    tqdm(total=total, desc="Parsing") as pbar_parse, \
                    tqdm(total=total, desc="Database") as pbar_db:

                # Fase 1: Download paralelo
                print("\n📥 FASE 1 - Download Paralelo")
                download_semaphore = asyncio.Semaphore(self.max_download_workers)

                async def limited_download(task):
                    async with download_semaphore:
                        result = await self.download_section_async(downloader, task)
                        pbar_download.update(1)
                        return result

                download_tasks = [limited_download(task) for task in tasks]
                download_results = await asyncio.gather(*download_tasks)

                # Filtrar apenas downloads bem-sucedidos
                to_parse = [t for t in download_results
                            if t.status == ProcessStatus.COMPLETED]
                print(f"✅ Downloads completos: {len(to_parse)}/{total}")

                # Fase 2: Parsing paralelo (usando ProcessPool para CPU-bound)
                print("\n🔍 FASE 2 - Parsing Paralelo")
                with ProcessPoolExecutor(max_workers=self.max_parse_workers) as executor:
                    parse_futures = []

                    for task in to_parse:
                        future = executor.submit(self.parse_section, task)
                        future.add_done_callback(lambda _: pbar_parse.update(1))
                        parse_futures.append(future)

                    parse_results = [f.result() for f in parse_futures]

                # Filtrar apenas parsings bem-sucedidos
                to_save = [t for t in parse_results
                           if t.status == ProcessStatus.SAVING]
                print(f"✅ Parsing completos: {len(to_save)}/{len(to_parse)}")

                # Fase 3: Salvamento no banco
                print("\n💾 FASE 3 - Salvamento no Banco")
                for task in to_save:
                    self.save_to_database(task)
                    pbar_db.update(1)

                print(f"✅ Salvamento completos: {len(to_save)}/{len(to_parse)}")

            # Estatísticas finais
            completed = sum(1 for t in tasks if t.status == ProcessStatus.COMPLETED)
            failed = sum(1 for t in tasks if t.status == ProcessStatus.FAILED)

            print(f"\n{'=' * 60}")
            print(f"📊 RESUMO FINAL - UF {uf.upper()}")
            print(f"{'=' * 60}")
            print(f"Total de tarefas: {total}")
            print(f"Completadas com sucesso: {completed}")
            print(f"Falhas: {failed}")
            print(f"Taxa de sucesso: {(completed / total) * 100:.1f}%")

            if failed > 0:
                print("\n⚠️  Tarefas com erro:")
                for task in [t for t in tasks if t.status == ProcessStatus.FAILED][:5]:
                    print(f"  • {task.municipio_nome} - Z{task.zona}-S{task.secao}: {task.error}")

        except Exception as e:
            print(f"❌ Erro no processamento: {e}")
            import traceback
            traceback.print_exc()


@app.command()
def run(
        uf: str = typer.Option(..., help="UF para processar"),
        limit: int = typer.Option(100, help="Número máximo de seções"),
        download_workers: int = typer.Option(5, help="Número de workers para download"),
        parse_workers: int = typer.Option(3, help="Número de workers para parsing"),
        resume: bool = typer.Option(True, help="Retomar de checkpoint")
):
    """Executa pipeline paralelo completo"""
    print(f"⚡ Pipeline Paralelo - UF: {uf.upper()}")

    processor = ParallelProcessor(
        max_download_workers=download_workers,
        max_parse_workers=parse_workers
    )

    # Executa de forma assíncrona
    asyncio.run(processor.process_uf_parallel(uf, limit))


@app.command()
def monitor(
        uf: str = typer.Option(..., help="UF para monitorar"),
        refresh: int = typer.Option(5, help="Segundos entre atualizações")
):
    """Monitora o progresso do processamento"""
    import time
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live

    console = Console()

    with Live(console=console, refresh_per_second=4) as live:
        while True:
            # TODO: Implementar monitoramento em tempo real
            table = Table(title=f"Monitoramento - UF {uf.upper()}")
            table.add_column("Município")
            table.add_column("Zona")
            table.add_column("Seção")
            table.add_column("Status")
            table.add_column("Progresso")

            # Exemplo de dados (substituir por dados reais)
            table.add_row("Rio Branco", "0001", "0001", "✅ Concluído", "100%")
            table.add_row("Rio Branco", "0001", "0002", "🔄 Processando", "75%")
            table.add_row("Rio Branco", "0001", "0003", "⏳ Aguardando", "0%")

            live.update(table)
            time.sleep(refresh)


@app.command()
def stats(
        uf: str = typer.Option(None, help="UF específica para estatísticas")
):
    """Mostra estatísticas do processamento"""
    from database.db_writer import engine

    try:
        with engine.connect() as conn:
            if uf:
                query = """
                        SELECT COUNT(*)                         as total_linhas, \
                               COUNT(DISTINCT municipio_codigo) as total_municipios, \
                               COUNT(DISTINCT zona)             as total_zonas, \
                               COUNT(DISTINCT secao)            as total_secoes, \
                               MIN(timestamp)                   as inicio, \
                               MAX(timestamp)                   as fim
                        FROM logs
                        WHERE uf = %s \
                        """
                result = conn.execute(query, (uf.upper(),))
            else:
                query = """
                        SELECT COUNT(*)                         as total_linhas, \
                               COUNT(DISTINCT uf)               as total_ufs, \
                               COUNT(DISTINCT municipio_codigo) as total_municipios, \
                               MIN(timestamp)                   as inicio, \
                               MAX(timestamp)                   as fim
                        FROM logs \
                        """
                result = conn.execute(query)

            row = result.fetchone()

            print(f"{'=' * 60}")
            print(f"📊 ESTATÍSTICAS DO BANCO")
            print(f"{'=' * 60}")

            if uf:
                print(f"UF: {uf.upper()}")
                print(f"Total de linhas: {row[0]:,}")
                print(f"Total de municípios: {row[1]}")
                print(f"Total de zonas: {row[2]}")
                print(f"Total de seções: {row[3]}")
                print(f"Período: {row[4]} a {row[5]}")
            else:
                print(f"Total de linhas: {row[0]:,}")
                print(f"Total de UFs: {row[1]}")
                print(f"Total de municípios: {row[2]}")
                print(f"Período: {row[3]} a {row[4]}")

    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")


if __name__ == "__main__":
    app()