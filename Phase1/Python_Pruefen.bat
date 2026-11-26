@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title Phase 1 - Python-Prüfung
pushd "%~dp0"
if errorlevel 1 goto ordner_fehler
if not exist "%~dp0..\Phase3\Python_Ausfuehren.bat" goto python_fehler

:pruefen
echo(
echo ============================================================
echo   MEIN STUDIEN-DASHBOARD - PYTHON-PRÜFUNG
echo ============================================================
echo(
call "%~dp0..\Phase3\Python_Ausfuehren.bat" --version
if errorlevel 1 goto fehlgeschlagen
echo(
echo [1/2] Speichern und Wiedereinlesen der Studiendaten
echo ------------------------------------------------------------
call "%~dp0..\Phase3\Python_Ausfuehren.bat" "machbarkeit\probe_speicherung.py"
if errorlevel 1 goto fehlgeschlagen
echo [OK] Speichertest bestanden. Die Quelldatei ist unverändert.
echo(
echo [2/2] Automatische Tests für Berechnungen und Oberfläche
echo ------------------------------------------------------------
call "%~dp0..\Phase3\Python_Ausfuehren.bat" "machbarkeit\test_machbarkeit.py" -q
if errorlevel 1 goto fehlgeschlagen
echo(
echo ============================================================
echo   ERGEBNIS: ALLE PRÜFUNGEN BESTANDEN
echo ============================================================
if /i "%~1"=="--ohne-pause" goto ende

:menue
echo(
echo [1] Dashboard zum eigenen Ausprobieren öffnen
echo [2] Alle Prüfungen wiederholen
echo [0] Beenden
choice /c 120 /n /m "Auswahl [1/2/0]: "
if errorlevel 255 goto fehlgeschlagen
if errorlevel 3 goto ende
if errorlevel 2 goto pruefen
if errorlevel 1 goto dashboard
goto ende

:dashboard
echo(
echo Das Dashboard wird geöffnet. Zum Menü zurück: Fenster schließen.
echo Für den Vergleich mit dem Konzept den Stichtag 2026-10-09 verwenden.
call "%~dp0..\Phase3\Python_Ausfuehren.bat" "machbarkeit\probe_gui.py"
if errorlevel 1 goto fehlgeschlagen
echo [OK] Dashboard beendet.
goto menue

:python_fehler
echo(
echo [FEHLER] Die gemeinsame Python-Startdatei in Phase3 fehlt.
echo Bitte das gesamte Projekt entpacken und die Ordnerstruktur beibehalten.
goto fehler_ende

:fehlgeschlagen
set "phase1Fehler=%errorlevel%"
echo(
echo ============================================================
echo   FEHLER - DIE PRÜFUNG WAR NICHT ERFOLGREICH
echo ============================================================
echo Fehlercode: %phase1Fehler%
echo Die genaue Meldung steht oberhalb. Bei Bedarf den Text kopieren.

:fehler_ende
echo(
echo Zum Schließen eine Taste drücken.
if /i not "%~1"=="--ohne-pause" pause >nul
popd
exit /b 1

:ordner_fehler
echo [FEHLER] Der Ordner der Startdatei konnte nicht geöffnet werden.
if /i not "%~1"=="--ohne-pause" pause
exit /b 1

:ende
popd
exit /b 0
