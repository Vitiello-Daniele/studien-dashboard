@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title studien-dashboard
pushd "%~dp0"
if errorlevel 1 exit /b 1
call "%~dp0Python_Ausfuehren.bat" start.py
set "phase3Ergebnis=%errorlevel%"
if not "%phase3Ergebnis%"=="0" (
    echo [fehler] das dashboard konnte nicht gestartet werden
    pause
)
popd
exit /b %phase3Ergebnis%
