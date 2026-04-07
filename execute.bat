@echo off
REM ====================================================================
REM LANZADOR INTERACTIVO PARA EXTRACTOR DE FACTURAS VTEX
REM Solicita Año y Mes al usuario antes de iniciar.
REM ====================================================================

SET SCRIPT_DIR=%~dp0
SET POWERSHELL_SCRIPT="%SCRIPT_DIR%run-billing.ps1"

echo.
echo ====================================================================
echo        CONFIGURACION DE EXTRACCION
echo ====================================================================
echo.

REM 1. Solicitamos el AÑO. El bucle :ASK_YEAR evita que lo dejen vacio.
:ASK_YEAR
set /p "YearInput=Por favor, introduce el ANO (ej. 2025): "
if "%YearInput%"=="" goto ASK_YEAR

echo.

REM 2. Solicitamos el MES INICIAL.
:ASK_MSTART
set /p "MonthStartInput=Por favor, introduce el MES INICIAL (1-12): "
if "%MonthStartInput%"=="" goto ASK_MSTART

echo.

REM 3. Solicitamos el MES FINAL.
:ASK_MEND
set /p "MonthEndInput=Por favor, introduce el MES FINAL (1-12): "
if "%MonthEndInput%"=="" goto ASK_MEND

echo.
echo ====================================================================
echo Iniciando proceso para: Ano %YearInput% - Meses %MonthStartInput% a %MonthEndInput%
echo ====================================================================
echo.

REM 4. Llamamos al script de PowerShell.
REM    Se usan 0/1 para booleanos para evitar errores de conversion desde CMD.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File %POWERSHELL_SCRIPT% ^
    -Year %YearInput% ^
    -MonthStart %MonthStartInput% ^
    -MonthEnd %MonthEndInput% ^
    -Account "tottoco" ^
    -Email "prac_desarrollo@totto.com" ^
    -Headless 0 ^
    -Debug 1 ^
    -UseSavedSession 1 ^
    -ForceRelogin 0

echo.
echo ====================================================================
echo Proceso finalizado.
echo ====================================================================
pause
