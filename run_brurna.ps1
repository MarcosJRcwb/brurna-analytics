Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "🗳️ BRURNA ANALYTICS - INICIALIZADOR MASTER" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "`n[1/4] 🛑 Parando processos anteriores..." -ForegroundColor Yellow
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

Write-Host "`n[2/4] 🧹 Limpando Banco de Dados (Nuclear Wipe)..." -ForegroundColor Yellow
python full_wipe.py

Write-Host "`n[3/4] 📊 Iniciando Dashboard Streamlit em Background..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath "streamlit" -ArgumentList "run src\dashboard\app.py --server.port 8501 --server.address 0.0.0.0"
Start-Sleep -Seconds 3

Write-Host "`n[4/4] 🚀 Iniciando Orquestrador de Ingestão em Massa Non-Stop..." -ForegroundColor Green
python mass_ingest.py

Write-Host "`n✅ Pipeline finalizado." -ForegroundColor Green
