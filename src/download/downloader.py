import requests
import pandas as pd
from time import sleep
from pathlib import Path
import sys

# Adicionar path para importar config
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import config

class TSEDownloader:
    def __init__(self):
        self.base_url = config.TSE_BASE_URL
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
        }
    
    def download_file(self, url: str, dest_file: Path):
        """Baixa um arquivo individual"""
        print(f"    Baixando: {url}")
        try:
            response = requests.get(url, headers=self.headers, stream=True)
            response.raise_for_status()
            
            # Criar diretório se não existir
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(dest_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=100000):
                    f.write(chunk)
            print(f"    ✅ Salvo em: {dest_file}")
            return True
        except Exception as e:
            print(f"    ❌ Erro ao baixar: {e}")
            return False
    
    def get_info_files(self, cd_uf, cd_municipio, cd_zona, cd_secao):
        """Obtém metadados da seção"""
        url = f'{self.base_url}/dados/{cd_uf}/{cd_municipio}/{cd_zona}/{cd_secao}/p000407-{cd_uf}-m{cd_municipio}-z{cd_zona}-s{cd_secao}-aux.json'
        try:
            r = requests.get(url=url, headers=self.headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"    ❌ Erro ao obter metadados: {e}")
            return None
    
    def download_section(self, uf: str, municipio_cod: str, municipio_nome: str, zona: str, secao: str):
        """Baixa todos os arquivos de uma seção"""
        print(f"  Processando: {municipio_nome} - Zona {zona} - Seção {secao}")
        
        # Obter metadados
        hash_data = self.get_info_files(uf, municipio_cod, zona, secao)
        if not hash_data:
            return False
        
        success = True
        # Baixar cada arquivo
        for hashe in hash_data.get('hashes', []):
            cd_hash = hashe.get('hash', '')
            for nm_file in hashe.get('nmarq', []):
                url = f'{self.base_url}/dados/{uf}/{municipio_cod}/{zona}/{secao}/{cd_hash}/{nm_file}'
                dest_path = config.RAW_LOGS_DIR / uf / nm_file
                
                if not self.download_file(url, dest_path):
                    success = False
        
        return success
    
    def download_uf(self, uf: str, limit: int = None):
        """Baixa logs de uma UF específica"""
        print(f"Coletando metadados da UF {uf}...")
        
        # URL de configuração da UF
        config_url = f"{self.base_url}/config/{uf}/{uf}-p000407-cs.json"
        
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
                        'secao2': sec.get('nsp', ''),
                        'baixado': False
                    })
        
        # Criar DataFrame
        df = pd.DataFrame(sections)
        
        if limit:
            df = df.head(limit)
            print(f"Limitado às primeiras {limit} seções")
        
        print(f"Total de seções para download: {len(df)}")
        
        # Baixar cada seção
        success_count = 0
        for idx, row in df.iterrows():
            print(f"\nSeção {idx+1}/{len(df)}:")
            
            baixado = self.download_section(
                row['uf'],
                row['municipio_codigo'],
                row['municipio_nome'],
                row['zona'],
                row['secao']
            )
            
            df.at[idx, 'baixado'] = baixado
            if baixado:
                success_count += 1
            
            # Pequena pausa
            sleep(1)
        
        print(f"\n✅ Download concluído: {success_count}/{len(df)} seções baixadas")
        return df

if __name__ == "__main__":
    # Teste rápido com 1 seção
    downloader = TSEDownloader()
    df = downloader.download_uf("ac", limit=1)
    print(f"\nResumo: {len(df)} seção(s) processada(s)")
