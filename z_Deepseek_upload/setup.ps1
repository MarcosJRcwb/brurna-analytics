# setup.ps1 - Script de configuração inicial

Write-Host "=== Configurando BRURNA Analytics ===" -ForegroundColor Cyan

# 1. Criar diretórios de dados
$dataPath = "C:\Users\marco\Downloads\TSE\data"
$subdirs = @(
    "raw_logs",
    "processed\parquet", 
    "processed\csv",
    "processed\json",
    "output\reports",
    "output\charts",
    "output\exports"
)

foreach ($dir in $subdirs) {
    $fullPath = Join-Path $dataPath $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force
        Write-Host "  Criado: $fullPath" -ForegroundColor Gray
    }
}

# 2. Criar pastas para cada UF
$ufs = @('ac','al','ap','am','ba','ce','df','es','zz','go','ma','mt','ms','mg',
         'pr','pb','pa','pe','pi','rj','rn','rs','ro','rr','sc','se','sp','to')

foreach ($uf in $ufs) {
    $ufPath = Join-Path "$dataPath\raw_logs" $uf
    if (-not (Test-Path $ufPath)) {
        New-Item -ItemType Directory -Path $ufPath -Force
    }
}

# 3. Atualizar pip e instalar dependências básicas
Write-Host "`nInstalando dependências..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install pandas requests duckdb typer tqdm pyarrow

Write-Host "`n=== Configuração concluída ===" -ForegroundColor Green
Write-Host "Para ativar ambiente virtual: .venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "Para testar: python main.py test" -ForegroundColor Gray
