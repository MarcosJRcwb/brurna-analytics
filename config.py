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


# Adicionar ao config.py existente
@dataclass
class ParallelConfig:
    """Configurações de paralelismo"""
    # Download
    MAX_DOWNLOAD_WORKERS: int = 10
    MAX_DOWNLOAD_RETRIES: int = 3
    DOWNLOAD_TIMEOUT: int = 30

    # Parsing
    MAX_PARSE_WORKERS: int = 4
    PARSE_BATCH_SIZE: int = 1000

    # Database
    DB_BATCH_SIZE: int = 1000
    DB_MAX_CONNECTIONS: int = 20

    # Monitoramento
    PROGRESS_REFRESH: int = 1  # segundos
    LOG_INTERVAL: int = 1000  # linhas


# Adicionar ao final do config.py existente
parallel_config = ParallelConfig()