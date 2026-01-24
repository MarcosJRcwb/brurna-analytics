"""
Módulo para download e integração com dados públicos do TSE.
Baixa resultados eleitorais, votação por seção e cruza com logs das urnas.
"""

import requests
import zipfile
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import io
from config import config


class TSEDataDownloader:
    """Download de dados públicos do TSE"""
    
    BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele"
    
    DATASETS = {
        'votacao_candidato_munzona': 'votacao_candidato_munzona/votacao_candidato_munzona_{year}.zip',
        'votacao_partido_munzona': 'votacao_partido_munzona/votacao_partido_munzona_{year}.zip',
        'detalhe_votacao_munzona': 'detalhe_votacao_munzona/detalhe_votacao_munzona_{year}.zip',
        'detalhe_votacao_secao': 'detalhe_votacao_secao/detalhe_votacao_secao_{year}.zip',
        'relatorio_totalizacao': 'relatorio_resultado_totalizacao/Relatorio_Resultado_Totalizacao_{year}_{uf}.zip',
        'votacao_secao': 'votacao_secao/votacao_secao_{year}_{uf}.zip'
    }
    
    def __init__(self, year: int = 2022):
        self.year = year
        self.data_dir = config.DATA_DIR / "tse_public_data" / str(year)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def download_dataset(self, dataset_name: str, uf: str = None) -> Path:
        """
        Baixa um dataset específico do TSE.
        
        Args:
            dataset_name: Nome do dataset (chave em DATASETS)
            uf: UF (necessário para alguns datasets)
            
        Returns:
            Path para o arquivo baixado
        """
        if dataset_name not in self.DATASETS:
            raise ValueError(f"Dataset desconhecido: {dataset_name}")
        
        # Monta URL
        url_template = self.DATASETS[dataset_name]
        url = f"{self.BASE_URL}/{url_template.format(year=self.year, uf=uf.upper() if uf else '')}"
        
        # Nome do arquivo local
        filename = url.split('/')[-1]
        local_path = self.data_dir / filename
        
        # Se já existe, não baixa novamente
        if local_path.exists():
            print(f"✅ Arquivo já existe: {local_path}")
            return local_path
        
        # Download com barra de progresso
        print(f"📥 Baixando: {filename}")
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(local_path, 'wb') as f, tqdm(
                desc=filename,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))
            
            print(f"✅ Download concluído: {local_path}")
            return local_path
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao baixar {url}: {e}")
            return None
    
    def extract_zip(self, zip_path: Path) -> Path:
        """
        Extrai arquivo ZIP.
        
        Args:
            zip_path: Caminho para o arquivo ZIP
            
        Returns:
            Path para o diretório extraído
        """
        extract_dir = zip_path.parent / zip_path.stem
        
        if extract_dir.exists():
            print(f"✅ Já extraído: {extract_dir}")
            return extract_dir
        
        print(f"📦 Extraindo: {zip_path.name}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        print(f"✅ Extraído em: {extract_dir}")
        return extract_dir
    
    def load_votacao_secao(self, uf: str) -> pd.DataFrame:
        """
        Carrega dados de votação por seção.
        
        Args:
            uf: Unidade Federativa
            
        Returns:
            DataFrame com votação por seção
        """
        # Download
        zip_path = self.download_dataset('votacao_secao', uf=uf)
        if not zip_path:
            return pd.DataFrame()
        
        # Extrai
        extract_dir = self.extract_zip(zip_path)
        
        # Encontra CSV
        csv_files = list(extract_dir.glob('*.csv'))
        if not csv_files:
            print(f"❌ Nenhum CSV encontrado em: {extract_dir}")
            return pd.DataFrame()
        
        csv_file = csv_files[0]
        
        print(f"📊 Carregando: {csv_file.name}")
        
        # Carrega CSV (pode ser grande)
        try:
            # Lê em chunks para economizar memória
            chunks = []
            for chunk in tqdm(
                pd.read_csv(csv_file, sep=';', encoding='latin-1', chunksize=100000),
                desc="Carregando CSV"
            ):
                chunks.append(chunk)
            
            df = pd.concat(chunks, ignore_index=True)
            print(f"✅ Carregado: {len(df):,} linhas")
            
            return df
            
        except Exception as e:
            print(f"❌ Erro ao carregar CSV: {e}")
            return pd.DataFrame()
    
    def load_detalhe_votacao_secao(self) -> pd.DataFrame:
        """
        Carrega detalhes de votação por seção (nacional).
        
        ATENÇÃO: Arquivo muito grande (>1GB)
        
        Returns:
            DataFrame com detalhes por seção
        """
        # Download
        zip_path = self.download_dataset('detalhe_votacao_secao')
        if not zip_path:
            return pd.DataFrame()
        
        # Extrai
        extract_dir = self.extract_zip(zip_path)
        
        # Encontra CSV
        csv_files = list(extract_dir.glob('*.csv'))
        if not csv_files:
            return pd.DataFrame()
        
        csv_file = csv_files[0]
        
        print(f"⚠️  ATENÇÃO: Arquivo grande ({csv_file.stat().st_size / (1024**3):.2f} GB)")
        print(f"📊 Carregando em chunks...")
        
        # Carrega apenas colunas relevantes
        colunas_relevantes = [
            'SG_UF', 'CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO',
            'NR_TURNO', 'DS_MODELO_URNA', 'QT_APTOS',
            'QT_COMPARECIMENTO', 'QT_ABSTENCOES'
        ]
        
        try:
            chunks = []
            for chunk in tqdm(
                pd.read_csv(
                    csv_file,
                    sep=';',
                    encoding='latin-1',
                    usecols=colunas_relevantes,
                    chunksize=100000
                ),
                desc="Carregando detalhes"
            ):
                chunks.append(chunk)
            
            df = pd.concat(chunks, ignore_index=True)
            print(f"✅ Carregado: {len(df):,} linhas")
            
            return df
            
        except Exception as e:
            print(f"❌ Erro ao carregar: {e}")
            return pd.DataFrame()


class TSEDataIntegrator:
    """Integra dados do TSE com logs das urnas"""
    
    def __init__(self, year: int = 2022):
        self.downloader = TSEDataDownloader(year=year)
        from sqlalchemy import create_engine
        self.engine = create_engine(config.POSTGRES_CONN)
    
    def get_section_logs(self, uf: str) -> pd.DataFrame:
        """
        Obtém metadados de seções dos logs.
        
        Args:
            uf: Unidade Federativa
            
        Returns:
            DataFrame com metadados das seções
        """
        query = f"""
            SELECT 
                uf,
                municipio_codigo,
                zona,
                secao,
                total_eventos,
                duracao_segundos,
                severidades
            FROM section_metadata
            WHERE uf = '{uf.upper()}'
        """
        
        return pd.read_sql(query, self.engine)
    
    def merge_with_tse_data(self, uf: str) -> pd.DataFrame:
        """
        Cruza logs das urnas com dados públicos do TSE.
        
        Args:
            uf: Unidade Federativa
            
        Returns:
            DataFrame com dados integrados
        """
        print("=" * 80)
        print(f"INTEGRAÇÃO: Logs × Dados TSE - {uf.upper()}")
        print("=" * 80)
        
        # Carrega logs
        print("\n1. Carregando logs das urnas...")
        logs_df = self.get_section_logs(uf)
        print(f"   ✅ {len(logs_df)} seções com logs")
        
        # Carrega dados TSE
        print("\n2. Baixando dados do TSE...")
        tse_df = self.downloader.load_votacao_secao(uf)
        
        if tse_df.empty:
            print("   ❌ Falha ao carregar dados do TSE")
            return pd.DataFrame()
        
        # Padroniza colunas para merge
        print("\n3. Preparando dados para merge...")
        
        # Logs: municipio_codigo, zona, secao
        logs_df['municipio_codigo'] = logs_df['municipio_codigo'].astype(str).str.zfill(5)
        logs_df['zona'] = logs_df['zona'].astype(str).str.zfill(4)
        logs_df['secao'] = logs_df['secao'].astype(str).str.zfill(4)
        
        # TSE: CD_MUNICIPIO, NR_ZONA, NR_SECAO
        if 'CD_MUNICIPIO' in tse_df.columns:
            tse_df['municipio_codigo'] = tse_df['CD_MUNICIPIO'].astype(str).str.zfill(5)
        if 'NR_ZONA' in tse_df.columns:
            tse_df['zona'] = tse_df['NR_ZONA'].astype(str).str.zfill(4)
        if 'NR_SECAO' in tse_df.columns:
            tse_df['secao'] = tse_df['NR_SECAO'].astype(str).str.zfill(4)
        
        # Merge
        print("\n4. Cruzando dados...")
        merged_df = logs_df.merge(
            tse_df,
            on=['municipio_codigo', 'zona', 'secao'],
            how='inner'
        )
        
        print(f"   ✅ {len(merged_df)} seções com dados integrados")
        print(f"   ⚠️  {len(logs_df) - len(merged_df)} seções sem match")
        
        return merged_df
    
    def analyze_by_urna_model(self, uf: str) -> pd.DataFrame:
        """
        Analisa anomalias por modelo de urna.
        
        Args:
            uf: Unidade Federativa
            
        Returns:
            DataFrame com estatísticas por modelo
        """
        # Carrega detalhes (inclui modelo de urna)
        print("\n📥 Baixando detalhes de votação (inclui modelo de urna)...")
        detalhes_df = self.downloader.load_detalhe_votacao_secao()
        
        if detalhes_df.empty:
            print("❌ Não foi possível carregar detalhes")
            return pd.DataFrame()
        
        # Filtra por UF
        detalhes_df = detalhes_df[detalhes_df['SG_UF'] == uf.upper()]
        
        # Carrega logs
        logs_df = self.get_section_logs(uf)
        
        # Prepara para merge
        detalhes_df['municipio_codigo'] = detalhes_df['CD_MUNICIPIO'].astype(str).str.zfill(5)
        detalhes_df['zona'] = detalhes_df['NR_ZONA'].astype(str).str.zfill(4)
        detalhes_df['secao'] = detalhes_df['NR_SECAO'].astype(str).str.zfill(4)
        
        logs_df['municipio_codigo'] = logs_df['municipio_codigo'].astype(str).str.zfill(5)
        logs_df['zona'] = logs_df['zona'].astype(str).str.zfill(4)
        logs_df['secao'] = logs_df['secao'].astype(str).str.zfill(4)
        
        # Merge
        merged = logs_df.merge(
            detalhes_df[['municipio_codigo', 'zona', 'secao', 'DS_MODELO_URNA', 'QT_APTOS', 'QT_COMPARECIMENTO']],
            on=['municipio_codigo', 'zona', 'secao'],
            how='inner'
        )
        
        # Agrupa por modelo de urna
        stats_by_model = merged.groupby('DS_MODELO_URNA').agg({
            'total_eventos': ['mean', 'std', 'min', 'max', 'count'],
            'duracao_segundos': ['mean', 'std'],
            'QT_COMPARECIMENTO': ['mean', 'sum']
        }).round(2)
        
        print("\n" + "=" * 80)
        print("ESTATÍSTICAS POR MODELO DE URNA")
        print("=" * 80)
        print(stats_by_model)
        
        return stats_by_model


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download e integração de dados TSE")
    parser.add_argument("--uf", required=True, help="UF para análise")
    parser.add_argument("--year", type=int, default=2022, help="Ano da eleição")
    parser.add_argument("--analyze-urna", action="store_true", help="Analisar por modelo de urna")
    
    args = parser.parse_args()
    
    integrator = TSEDataIntegrator(year=args.year)
    
    if args.analyze_urna:
        integrator.analyze_by_urna_model(args.uf)
    else:
        merged = integrator.merge_with_tse_data(args.uf)
        
        if not merged.empty:
            output_file = f"integrated_data_{args.uf}_{args.year}.csv"
            merged.to_csv(output_file, index=False)
            print(f"\n✅ Dados integrados salvos em: {output_file}")
