@echo off
title EvidencIA - Compilar Web + PWA
setlocal

REM ============================================================
REM  Compila el frontend Flutter Web apuntando a un backend.
REM
REM  Uso:
REM    build_web.bat                                  -> localhost:8000 (probar local)
REM    build_web.bat https://mi-api.onrender.com      -> version publica
REM
REM  El resultado queda en frontend\build\web : se sube tal cual
REM  a GitHub Pages / Cloudflare Pages / Netlify.
REM ============================================================

set API_URL=%1

if "%API_URL%"=="" (
  echo Sin URL de API: se compila con el default http://localhost:8000
  echo Para la version publica:  build_web.bat https://TU-BACKEND.onrender.com
  echo.
)

cd /d "%~dp0frontend"

if "%API_URL%"=="" (
  flutter build web --release
) else (
  echo Compilando para API publica: %API_URL%
  flutter build web --release --dart-define=API_BASE_URL=%API_URL%
)

if errorlevel 1 (
  echo.
  echo Fallo la compilacion.
  exit /b 1
)

echo.
echo ============================================================
echo  Listo:  %cd%\build\web
echo ============================================================
echo.
echo  Probar localmente como sitio:
echo      cd build\web ^&^& python -m http.server 8080
echo      (abrir http://localhost:8080)
echo.
echo  Publicar como PWA instalable: suba esa carpeta a un hosting
echo  estatico con HTTPS (GitHub Pages, Cloudflare Pages, Netlify).
echo  Sin HTTPS el navegador no ofrece "Instalar aplicacion".
echo.
pause
