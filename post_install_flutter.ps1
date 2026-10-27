## Script de post-instalación Flutter
## Ejecutar este script UNA VEZ cuando termine la descarga del ZIP de Flutter

param(
    [string]$ZipPath = "C:\Users\User\Downloads\flutter_windows_3.47.7-stable.zip",
    [string]$DestPath = "C:\Users\User\Downloads"
)

Write-Host "=== EvidencIA - Post-instalación Flutter ===" -ForegroundColor Cyan

# 1. Verificar que el ZIP existe
if (-not (Test-Path $ZipPath)) {
    Write-Error "No se encontró el ZIP: $ZipPath"
    exit 1
}

# 2. Extraer Flutter
Write-Host "Extrayendo Flutter en $DestPath ..." -ForegroundColor Yellow
Expand-Archive -Path $ZipPath -DestinationPath $DestPath -Force
Write-Host "Extracción completada." -ForegroundColor Green

# 3. Verificar flutter.bat
$flutterBat = "$DestPath\flutter\bin\flutter.bat"
if (Test-Path $flutterBat) {
    Write-Host "flutter.bat encontrado." -ForegroundColor Green
} else {
    Write-Error "No se encontró flutter.bat en la ruta esperada."
    exit 1
}

# 4. Habilitar Flutter web
Write-Host "Habilitando soporte web..." -ForegroundColor Yellow
& $flutterBat config --enable-web

# 5. Instalar dependencias del frontend
Write-Host "Instalando dependencias Flutter del frontend..." -ForegroundColor Yellow
Set-Location "c:\Users\User\Desktop\JERONIMO\EvidencIA\frontend"
& $flutterBat pub get

Write-Host ""
Write-Host "=== ¡Listo! ===" -ForegroundColor Green
Write-Host "Para correr la app web:" -ForegroundColor White
Write-Host "  cd c:\Users\User\Desktop\JERONIMO\EvidencIA\frontend" -ForegroundColor Gray
Write-Host "  flutter run -d chrome" -ForegroundColor Gray
Write-Host ""
Write-Host "Para correr el backend:" -ForegroundColor White
Write-Host "  cd c:\Users\User\Desktop\JERONIMO\EvidencIA\backend" -ForegroundColor Gray
Write-Host "  uvicorn main:app --reload --port 8000" -ForegroundColor Gray
