@echo off
title EvidencIA - Lanzador Completo
echo ====================================================
echo        Lanzador Completo - EvidencIA
echo ====================================================
echo.
echo 1. Levantando Backend FastAPI en una ventana independiente...
start "EvidencIA Backend (Puerto 8000)" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --port 8000"

echo 2. Esperando 3 segundos a que el backend inicialice...
timeout /t 3 /nobreak >nul

echo 3. Levantando Frontend Flutter Web en Chrome...
start "EvidencIA Frontend (Flutter)" cmd /k "cd /d %~dp0frontend && flutter run -d chrome"

echo.
echo ====================================================
echo  Ambos servicios se han iniciado en ventanas separadas.
echo  Podes cerrar esta ventana cuando desees.
echo ====================================================
timeout /t 5
