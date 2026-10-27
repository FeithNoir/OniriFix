@echo off
chcp 65001 >nul
title OniriFix
set "ONIRIFIX_HOME=%USERPROFILE%\OniriFix"
if not exist "%ONIRIFIX_HOME%" mkdir "%ONIRIFIX_HOME%"
if not exist "%ONIRIFIX_HOME%\config" mkdir "%ONIRIFIX_HOME%\config"
if not exist "%ONIRIFIX_HOME%\config\reglas.yaml" copy /y "%~dp0config\reglas.yaml" "%ONIRIFIX_HOME%\config\reglas.yaml" >nul
if not exist "%ONIRIFIX_HOME%\examples" xcopy "%~dp0examples" "%ONIRIFIX_HOME%\examples" /e /i /q >nul
set "PATH=%~dp0;%PATH%"
cd /d "%ONIRIFIX_HOME%"
echo.
echo   OniriFix 0.1.0 - corrector editorial offline
echo   Carpeta de trabajo: %ONIRIFIX_HOME%
echo.
echo   Ejemplos:      %ONIRIFIX_HOME%\examples
echo   Documentacion: %~dp0docs
echo.
echo   Primer paso:   onirifix init
echo   Ayuda:         onirifix --help
echo.
"%ComSpec%" /k
