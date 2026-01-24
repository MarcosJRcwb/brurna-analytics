import aiohttp
import asyncio
from tqdm import tqdm
import aiofiles
from pathlib import Path
from typing import List, Dict
import sys

# Adicionar path para importar config
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import config


class AsyncTSEDownloader:
    """Downloader assíncrono com TQDM"""

    def __init__(self, max_concurrent: int = 10):
        self.base_url = config.TSE_BASE_URL
        self.max_concurrent = max_concurrent
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
        }

    async def download_file(self, session: aiohttp.ClientSession,
                            url: str, dest_file: Path, pbar: tqdm) -> bool:
        """Baixa um arquivo individual de forma assíncrona"""
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    # Cria diretório se não existir
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Baixa e salva o arquivo
                    async with aiofiles.open(dest_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                            await f.write(chunk)

                    pbar.update(1)
                    pbar.set_description(f"✅ {dest_file.name[:30]}...")
                    return True
                else:
                    pbar.set_description(f"❌ HTTP {response.status}: {dest_file.name[:30]}...")
                    return False

        except Exception as e:
            pbar.set_description(f"❌ Erro: {dest_file.name[:30]}...")
            return False

    async def download_section_files(self, session: aiohttp.ClientSession,
                                     uf: str, municipio_cod: str, zona: str,
                                     secao: str, pbar: tqdm) -> List[Path]:
        """Baixa todos os arquivos de uma seção"""
        # Obter metadados
        info_url = f'{self.base_url}/dados/{uf}/{municipio_cod}/{zona}/{secao}/p000407-{uf}-m{municipio_cod}-z{zona}-s{secao}-aux.json'

        try:
            async with session.get(info_url, headers=self.headers) as response:
                if response.status != 200:
                    return []

                hash_data = await response.json()
                downloaded_files = []

                # Criar semáforo para limitar concorrência
                semaphore = asyncio.Semaphore(self.max_concurrent)

                async def download_with_semaphore(hashe, nm_file):
                    async with semaphore:
                        cd_hash = hashe.get('hash', '')
                        url = f'{self.base_url}/dados/{uf}/{municipio_cod}/{zona}/{secao}/{cd_hash}/{nm_file}'
                        dest_path = config.RAW_LOGS_DIR / uf / nm_file

                        # Verificar se já existe
                        if dest_path.exists():
                            pbar.update(1)
                            return dest_path

                        if await self.download_file(session, url, dest_path, pbar):
                            return dest_path
                        return None

                # Criar tasks para todos os arquivos
                tasks = []
                for hashe in hash_data.get('hashes', []):
                    for nm_file in hashe.get('nmarq', []):
                        tasks.append(download_with_semaphore(hashe, nm_file))

                # Executar downloads concorrentes
                results = await asyncio.gather(*tasks)
                downloaded_files = [r for r in results if r is not None]

                return downloaded_files

        except Exception as e:
            pbar.set_description(f"❌ Erro na seção: {e}")
            return []

    async def process_section(self, session: aiohttp.ClientSession,
                              section: Dict, pbar: tqdm) -> Dict:
        """Processa uma seção completa"""
        result = section.copy()

        downloaded = await self.download_section_files(
            session,
            section['uf'],
            section['municipio_codigo'],
            section['zona'],
            section['secao'],
            pbar
        )

        result['downloaded_files'] = len(downloaded)
        result['success'] = len(downloaded) > 0

        return result

    async def download_uf(self, uf: str, limit: int = None) -> List[Dict]:
        """Baixa logs de uma UF específica de forma assíncrona"""
        print(f"🌐 Coletando metadados da UF {uf}...")

        config_url = f"{self.base_url}/config/{uf}/{uf}-p000407-cs.json"

        async with aiohttp.ClientSession() as session:
            async with session.get(config_url, headers=self.headers) as response:
                if response.status != 200:
                    print(f"❌ Erro ao obter metadados: HTTP {response.status}")
                    return []

                config_data = await response.json()

                # Coletar seções
                sections = []
                for municipio in config_data['abr'][0]['mu']:
                    for zonas in municipio['zon']:
                        for sec in zonas['sec']:
                            sections.append({
                                'uf': uf,
                                'municipio_codigo': municipio['cd'],
                                'municipio_nome': municipio['nm'],
                                'zona': zonas['cd'],
                                'secao': sec['ns'],
                                'baixado': False
                            })

                if limit:
                    sections = sections[:limit]

                total_sections = len(sections)
                print(f"📊 Total de seções: {total_sections}")

                # Calcular total de arquivos
                total_files = total_sections * 2  # Aproximação

                # Barra de progresso principal
                with tqdm(total=total_files, desc=f"Download {uf.upper()}",
                          unit="arquivo") as pbar:

                    # Processar seções concorrentemente
                    semaphore = asyncio.Semaphore(self.max_concurrent)

                    async def process_with_semaphore(section):
                        async with semaphore:
                            return await self.process_section(session, section, pbar)

                    tasks = [process_with_semaphore(section) for section in sections]
                    results = await asyncio.gather(*tasks)

                    # Estatísticas
                    successful = sum(1 for r in results if r['success'])

                    print(f"\n{'=' * 60}")
                    print(f"📊 RESUMO DO DOWNLOAD - UF {uf.upper()}")
                    print(f"{'=' * 60}")
                    print(f"Seções processadas: {total_sections}")
                    print(f"Seções com sucesso: {successful}")
                    print(f"Taxa de sucesso: {(successful / total_sections) * 100:.1f}%")

                    return results