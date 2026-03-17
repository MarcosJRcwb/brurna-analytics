import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ProjectConfig:
    """Configuracoes do projeto"""
    
    # Diretórios
    PROJECT_ROOT: Path = Path(__file__).parent.absolute()
    TEMP_DIR: Path = Path(r"C:\Users\marco\Downloads\TSE")
    DATA_DIR: Path = TEMP_DIR / "data"
    
    # Subdiretórios
    RAW_LOGS_DIR: Path = DATA_DIR / "raw_logs"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    OUTPUT_DIR: Path = DATA_DIR / "output"
    
    # Database
    USE_POSTGRES: bool = True
    POSTGRES_CONN: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    REMOTE_POSTGRES_CONN: str = os.getenv("REMOTE_DATABASE_URL", POSTGRES_CONN)
    LOCAL_POSTGRES_CONN: str = os.getenv("LOCAL_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/brurna_db")

    DUCKDB_PATH: Path = PROCESSED_DIR / "cache.duckdb"
    
    # URLs TSE (407 = 1º Turno, 408 = 2º Turno)
    TSE_BASE_URL_TEMPLATE: str = "https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/{code}"
    TSE_BASE_URL: str = "https://resultados.tse.jus.br/oficial/ele2022/arquivo-urna/407"
    
    # Lista de UFs
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

@dataclass
class ParallelConfig:
    """Configurações de paralelismo"""
    MAX_DOWNLOAD_WORKERS: int = 25
    MAX_DOWNLOAD_RETRIES: int = 3
    DOWNLOAD_TIMEOUT: int = 30
    MAX_PARSE_WORKERS: int = 4
    PARSE_BATCH_SIZE: int = 1000
    DB_BATCH_SIZE: int = 1000
    DB_MAX_CONNECTIONS: int = 20
    PROGRESS_REFRESH: int = 1  # segundos
    LOG_INTERVAL: int = 1000  # linhas

parallel_config = ParallelConfig()