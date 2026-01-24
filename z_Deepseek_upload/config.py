import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

@dataclass
class ProjectConfig:
    """Configuracoes do projeto"""
    
    # Diretórios
    PROJECT_ROOT: Path = Path(r"C:\Users\marco\OneDrive\Projetos\brurna-analytics")
    TEMP_DIR: Path = Path(r"C:\Users\marco\Downloads\TSE")
    DATA_DIR: Path = TEMP_DIR / "data"
    
    # Subdiretórios
    RAW_LOGS_DIR: Path = DATA_DIR / "raw_logs"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    OUTPUT_DIR: Path = DATA_DIR / "output"
    
    # Database
    USE_POSTGRES: bool = True
    #POSTGRES_CONN: str = "postgresql://brurna_user:Brurna2022Tse@147.93.187.149:5433/brurna_db?sslmode=disable"
    POSTGRES_CONN: str = "postgresql://brurna_user:Brurna2022Tse2026@147.93.187.149:5433/brurna_db?sslmode=disable"
    DUCKDB_PATH: Path = PROCESSED_DIR / "cache.duckdb"
    
    # URLs TSE
    TSE_BASE_URL: str = "https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/407"
    
    # Lista de UFs - usando default_factory porque listas sao mutaveis
    UFS: List[str] = field(default_factory=lambda: [
        'ac', 'al', 'ap', 'am', 'ba', 'ce', 'df', 'es', 'zz', 'go', 
        'ma', 'mt', 'ms', 'mg', 'pr', 'pb', 'pa', 'pe', 'pi', 'rj', 
        'rn', 'rs', 'ro', 'rr', 'sc', 'se', 'sp', 'to'
    ])
    
    # Configuracoes de processamento
    BATCH_SIZE: int = 1000
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 60  # segundos
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = PROJECT_ROOT / "logs" / "processing.log"
    
    def setup_directories(self):
        """Cria todos os diretorios necessarios"""
        directories = [
            self.RAW_LOGS_DIR,
            self.PROCESSED_DIR / "parquet",
            self.PROCESSED_DIR / "csv",
            self.PROCESSED_DIR / "json",
            self.OUTPUT_DIR / "reports",
            self.OUTPUT_DIR / "charts",
            self.OUTPUT_DIR / "exports",
            self.PROJECT_ROOT / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Cria pastas para cada UF
        for uf in self.UFS:
            (self.RAW_LOGS_DIR / uf).mkdir(exist_ok=True)
    
    @property
    def metadata_file(self) -> Path:
        return self.PROCESSED_DIR / "metadata.parquet"

config = ProjectConfig()
config.setup_directories()
