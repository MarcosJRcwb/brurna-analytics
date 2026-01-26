import requests
import pandas as pd
from time import sleep
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Adicionar path para importar config
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import config, parallel_config

class TSEDownloader:
    def __init__(self, turno: int = 1):
        self.turno = turno
        self.code = "407" if turno == 1 else "408"
        self.base_url = config.TSE_BASE_URL_TEMPLATE.format(code=self.code)
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
        }
    
    def download_file(self, url: str, dest_file: Path):
        """Baixa um arquivo individual"""
        try:
            if dest_file.exists():
                return True # Skip se já existe

            response = requests.get(url, headers=self.headers, stream=True)
            response.raise_for_status()
            
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(dest_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=100000):
                    f.write(chunk)
            return True
        except Exception as e:
            return False
    
    def get_info_files(self, cd_uf, cd_municipio, cd_zona, cd_secao):
        """Obtém metadados da seção"""
        # p000407 para T1, p000408 para T2
        prefix = f"p000{self.code}"
        url = f'{self.base_url}/dados/{cd_uf}/{cd_municipio}/{cd_zona}/{cd_secao}/{prefix}-{cd_uf}-m{cd_municipio}-z{cd_zona}-s{cd_secao}-aux.json'
        try:
            r = requests.get(url=url, headers=self.headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return None
    
    def download_section(self, uf: str, municipio_cod: str, municipio_nome: str, zona: str, secao: str):
        """Baixa todos os arquivos de uma seção"""
        hash_data = self.get_info_files(uf, municipio_cod, zona, secao)
        if not hash_data:
            return False
        
        success = True
        # Baixar cada arquivo
        for hashe in hash_data.get('hashes', []):
            cd_hash = hashe.get('hash', '')
            for nm_file in hashe.get('nmarq', []):
                url = f'{self.base_url}/dados/{uf}/{municipio_cod}/{zona}/{secao}/{cd_hash}/{nm_file}'
                
                # Se for Turno 2, salva em subpasta t2
                uf_path = uf if self.turno == 1 else f"{uf}/t2"
                dest_path = config.RAW_LOGS_DIR / uf_path / nm_file
                
                if not self.download_file(url, dest_path):
                    success = False
        
        return success
    
    def download_uf(self, uf: str, limit: int = None):
        """Baixa logs de uma UF específica em PARALELO"""
        print(f"Coletando metadados da UF {uf} (Turno {self.turno})...")
        
        # URL de configuração da UF (p000407-cs.json ou p000408-cs.json)
        prefix = f"p000{self.code}"
        config_url = f"{self.base_url}/config/{uf}/{uf}-{prefix}-cs.json"
        
        response = requests.get(config_url, headers=self.headers)
        config_data = response.json()
        
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
        
        df = pd.DataFrame(sections)
        
        if limit:
            df = df.head(limit)
            print(f"Limitado às primeiras {limit} seções")
        
        print(f"Total de seções para download: {len(df)}")
        print(f"🚀 Iniciando download PARALELO (Turno {self.turno}) com {parallel_config.MAX_DOWNLOAD_WORKERS} workers...")
        
        success_count = 0
        
        with ThreadPoolExecutor(max_workers=parallel_config.MAX_DOWNLOAD_WORKERS) as executor:
            futures = {
                executor.submit(
                    self.download_section,
                    row['uf'],
                    row['municipio_codigo'],
                    row['municipio_nome'],
                    row['zona'],
                    row['secao']
                ): idx for idx, row in df.iterrows()
            }
            
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"Baixando {uf.upper()} T{self.turno}", unit="seção"):
                idx = futures[future]
                try:
                    baixado = future.result()
                    df.at[idx, 'baixado'] = baixado
                    if baixado:
                        success_count += 1
                except Exception as e:
                    print(f"❌ Erro na tarefa {idx}: {e}")
        
        print(f"\n✅ Download concluído: {success_count}/{len(df)} seções baixadas")
        return df

if __name__ == "__main__":
    # Teste rápido com 5 seções
    downloader = TSEDownloader()
    df = downloader.download_uf("ac", limit=5)
    print(f"\nResumo: {len(df)} seção(s) processada(s)")
