@echo off
title EvidencIA - Frontend (Flutter Web)
echo ====================================================
echo        EvidencIA - Cliente Flutter Web
echo ====================================================
echo.
cd /d "%~dp0frontend"
echo Iniciando Flutter Web en Chrome...
echo (Asegurate de que el backend ya este corriendo)
echo.
flutter run -d chrome
pause
