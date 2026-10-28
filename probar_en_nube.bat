@echo off
title EvidencIA - Probar en Chrome (contra el backend de Render)
setlocal

REM ============================================================
REM  Abre la app en Chrome en modo desarrollo SIN necesitar el
REM  backend local: llama directo a https://evidencia-pljv.onrender.com
REM
REM  Uso:
REM    probar_en_nube.bat                      -> backend publico de Render
REM    probar_en_nube.bat http://localhost:8000 -> backend local
REM
REM  Si usas el backend local, levantalo antes con iniciar_backend.bat
REM ============================================================

set API_URL=%1
if "%API_URL%"=="" set API_URL=https://evidencia-pljv.onrender.com

cd /d "%~dp0frontend"

echo ============================================================
echo   EvidencIA - frontend en Chrome
echo   API: %API_URL%
echo ============================================================
echo.
echo   La primera compilacion tarda entre 40 y 90 segundos.
echo   Chrome se abre solo. No cierres esta ventana.
echo   Para detener: Ctrl+C aqui, o cierra la pestana de Chrome.
echo.

flutter run -d chrome --web-port 8080 --dart-define=API_BASE_URL=%API_URL%

pause
