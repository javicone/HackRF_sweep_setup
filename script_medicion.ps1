# --- CONFIGURACIÓN ---
$RutaHackRF = "C:\Users\javiv\Desktop\TFG LORA\MEDIDAS HACKRF\codigo_pruebas\hackrf-tools-windows\hackrf_sweep.exe" 
$FreqMin = 863
$FreqMax = 870
$BinWidth = 100000 
$LnaGain = 32
$VgaGain = 20
$DuracionSegundos = 60
$OutputFile = "C:\Users\javiv\Desktop\TFG LORA\MEDIDAS HACKRF\codigo_pruebas\captura_universidad.csv"

Write-Host "--- VERIFICANDO HARDWARE ---" -ForegroundColor Yellow
if (-not (Test-Path $RutaHackRF)) {
    Write-Host "ERROR: Ruta incorrecta: $RutaHackRF" -ForegroundColor Red
    return
}

Write-Host "--- INICIANDO CAPTURA DE RANGO COMPLETO ---" -ForegroundColor Cyan
Write-Host "Rango: $FreqMin MHz a $FreqMax MHz"

# DEFINICIÓN DE ARGUMENTOS ROBUSTA (ARRAY)
# Esto evita que PowerShell rompa la cadena en los dos puntos
$Argumentos = @(
    "-f", "${FreqMin}:${FreqMax}",
    "-w", "$BinWidth",
    "-l", "$LnaGain",
    "-g", "$VgaGain"
)

# EJECUCIÓN
$Proceso = Start-Process -FilePath $RutaHackRF `
                         -ArgumentList $Argumentos `
                         -RedirectStandardOutput $OutputFile `
                         -PassThru

# ESPERA
Start-Sleep -Seconds $DuracionSegundos

# CIERRE
if (-not $Proceso.HasExited) {
    Stop-Process -InputObject $Proceso
}

Write-Host "--- CAPTURA FINALIZADA ---" -ForegroundColor Green
Write-Host "Verifica en Python que ahora el eje X llega hasta 871 MHz." -ForegroundColor Yellow