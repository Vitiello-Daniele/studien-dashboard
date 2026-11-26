@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "phase3Python="
py -3 -c "import sys, tkinter; assert sys.version_info >= (3, 13)" >nul 2>&1
if not errorlevel 1 goto launcher
python -c "import sys, tkinter; assert sys.version_info >= (3, 13)" >nul 2>&1
if not errorlevel 1 goto python
for /d %%p in ("%APPDATA%\uv\python\cpython-3.13.*-windows-x86_64-none") do if exist "%%p\python.exe" set "phase3Python=%%p\python.exe"
if not defined phase3Python goto fehlt
"%phase3Python%" -c "import sys, tkinter; assert sys.version_info >= (3, 13)" >nul 2>&1
if errorlevel 1 goto fehlt
"%phase3Python%" -B -X utf8 %*
exit /b %errorlevel%

:launcher
py -3 -B -X utf8 %*
exit /b %errorlevel%

:python
python -B -X utf8 %*
exit /b %errorlevel%

:fehlt
echo [fehler] python 3.13 oder neuer mit tkinter wurde nicht gefunden
echo python von https://www.python.org/downloads/ installieren
echo dabei tkinter und den python-launcher mitinstallieren
exit /b 1
