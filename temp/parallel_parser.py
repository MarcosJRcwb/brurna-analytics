#!/usr/bin/env python3
"""
Worker para parsing paralelo usando multiprocessing
"""

from multiprocessing import Pool, cpu_count
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import sys

# Adiciona src ao path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

from parser.log_parser import TSELogParser
from database.db_writer import save_parsed_logs


def parse_single_file(args):
    """Função para parsing de um único arquivo (usada em Pool)"""
    file_path, uf, turno = args

    try:
        parser = TSELogParser(str(file_path))
        df = parser.parse_file(uf=uf, turno=turno)

        if not df.empty:
            return {
                'file': file_path.name,
                'uf': uf,
                'turno': turno,
                'dataframe': df,
                'success': True,
                'rows': len(df),
                'error': None
            }
        else:
            return {
                'file': file_path.name,
                'uf': uf,
                'turno': turno,
                'dataframe': None,
                'success': False,
                'rows': 0,
                'error': 'DataFrame vazio'
            }

    except Exception as e:
        return {
            'file': file_path.name,
            'uf': uf,
            'turno': turno,
            'dataframe': None,
            'success': False,
            'rows': 0,
            'error': str(e)
        }


class ParallelParser:
    """Parser paralelo usando multiprocessing"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or cpu_count() - 1

    def parse_directory(self, uf: str, turno: int = 1,
                        batch_size: int = 1000) -> Dict:
        """Parseia todos os arquivos de um diretório em paralelo"""
        from config import config

        raw_dir = config.RAW_LOGS_DIR / uf
        files = list(raw_dir.glob('*.logjez'))

        if not files:
            return {'total': 0, 'success': 0, 'failed': 0, 'total_rows': 0}

        print(f"🔍 Iniciando parsing paralelo: {len(files)} arquivos")
        print(f"👷 Workers: {self.max_workers}")

        # Preparar argumentos
        args = [(f, uf, turno) for f in files]

        results = []
        total_rows = 0

        # Processar em lotes para evitar sobrecarga de memória
        for i in range(0, len(args), batch_size):
            batch = args[i:i + batch_size]

            with Pool(processes=self.max_workers) as pool:
                with tqdm(total=len(batch), desc=f"Lote {i // batch_size + 1}") as pbar:
                    for result in pool.imap_unordered(parse_single_file, batch):
                        results.append(result)

                        if result['success'] and result['dataframe'] is not None:
                            # Salvar no banco imediatamente
                            try:
                                save_parsed_logs(
                                    result['dataframe'],
                                    uf=result['uf'],
                                    turno=result['turno']
                                )
                                total_rows += result['rows']
                            except Exception as e:
                                result['success'] = False
                                result['error'] = str(e)

                        pbar.update(1)
                        pbar.set_postfix_str(f"Total: {total_rows:,} linhas")

            # Liberar memória
            for result in results:
                if 'dataframe' in result:
                    del result['dataframe']

        # Estatísticas
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful

        return {
            'total': len(results),
            'success': successful,
            'failed': failed,
            'total_rows': total_rows,
            'results': results
        }


def main():
    """Função principal para execução direta"""
    import typer

    app = typer.Typer()

    @app.command()
    def parse(
            uf: str = typer.Option(..., help="UF para processar"),
            turno: int = typer.Option(1, help="Número do turno"),
            workers: int = typer.Option(None, help="Número de workers"),
            batch_size: int = typer.Option(1000, help="Tamanho do lote")
    ):
        """Parseia arquivos em paralelo"""
        parser = ParallelParser(max_workers=workers)
        result = parser.parse_directory(uf, turno, batch_size)

        print(f"\n{'=' * 60}")
        print(f"📊 RESUMO DO PARSING - UF {uf.upper()}")
        print(f"{'=' * 60}")
        print(f"Arquivos processados: {result['total']}")
        print(f"Arquivos com sucesso: {result['success']}")
        print(f"Arquivos com falha: {result['failed']}")
        print(f"Total de linhas processadas: {result['total_rows']:,}")

        if result['failed'] > 0:
            print(f"\n⚠️  Arquivos com erro:")
            for r in result['results'][:5]:
                if not r['success']:
                    print(f"  • {r['file']}: {r['error']}")

    app()


if __name__ == "__main__":
    main()