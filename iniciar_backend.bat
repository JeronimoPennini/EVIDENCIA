@echo off
title EvidencIA - Backend (FastAPI)
echo ====================================================
echo        EvidencIA - Servidor Backend (FastAPI)
echo ====================================================
echo.
cd /d "%~dp0backend"
echo Iniciando servidor en http://localhost:8000 ...
echo (Para detener el servidor presiona CTRL+C)
echo.
python -m uvicorn main:app --reload --port 8000
pause
