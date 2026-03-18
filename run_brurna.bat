@echo off
color 0B
echo =========================================
echo  BRURNA ANALYTICS - INICIALIZADOR MASTER
echo =========================================
echo.

echo [1/4] Parando processos anteriores...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 1 >nul

echo [2/4] Limpando Banco de Dados (Nuclear Wipe)...
python full_wipe.py

echo [3/4] Iniciando Dashboard Streamlit em Background...
start "" /B streamlit run src\dashboard\app.py --server.port 8501 --server.address 0.0.0.0
timeout /t 3 >nul

echo [4/4] Iniciando Orquestrador de Ingestao em Massa Non-Stop...
color 0A
python mass_ingest.py

echo.
echo Pipeline finalizado.
pause
