@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title phase 2: python-prüfung
set "phase2Python=%APPDATA%\uv\python\cpython-3.13.14-windows-x86_64-none\python.exe"
set "phase2Ergebnis=0"
pushd "%~dp0"
if errorlevel 1 goto ordner_fehler
if not exist "%phase2Python%" goto python_fehler
if /i "%~1"=="--ohne-pause" goto alle

:menue
cls
echo(
echo ============================================================
echo   phase 2: testübersicht
echo ============================================================
echo(
echo [0] alles testen
echo(
echo [1] arbeitspaket 1: prüfungsleistung und leistungsstatus
echo     [test] neue leistung ohne erfundene note
echo     [test] abschluss anhand des leistungsstatus
echo     [test] anerkennung ohne note
echo     [test] gültige noten und grenzwerte
echo     [test] ungültige noten zurückweisen
echo     [test] ungültige namen zurückweisen
echo     [test] ungültige statuswerte zurückweisen
echo     [test] leistung ändern und abschluss neu bestimmen
echo     [test] bisherigen stand bei fehlern erhalten
echo     [test] direkten schreibzugriff auf properties verhindern
echo     [test] getrennte zustände verschiedener instanzen
echo     [test] vorhandene studiendaten unverändert übernehmen
echo(
echo [2] arbeitspaket 2: objektbeziehungen
echo     [test] modul mit vorhandener leistung und optionalen ects
echo     [test] ungültige modulangaben zurückweisen
echo     [test] mehrere leistungen als eigene objekte erhalten
echo     [test] leistung genau einem modul zuordnen
echo     [test] semesternummer prüfen
echo     [test] optionalen studiengangsnamen prüfen
echo     [test] sammlungen verschiedener instanzen trennen
echo     [test] dasselbe modul über beide zugriffswege erreichen
echo     [test] doppelte semesterzuordnung verhindern
echo     [test] doppelte modulzuordnung verhindern
echo     [test] aufnahme mit fremdem semester zurückweisen
echo     [test] modul und leistung beim semesterwechsel erhalten
echo     [test] zuordnung bei fehlerhaftem wechsel erhalten
echo     [test] semester erst nach dem umordnen entfernen
echo     [test] fremde semester nicht entfernen
echo     [test] öffentliche zugriffe auf zuordnungen schützen
echo     [test] lebensdauer bei vorhandener referenz prüfen
echo     [test] semesterzuordnung der studiendaten übernehmen
echo(
echo [q] beenden
echo(
choice /c 012q /n /m "welche tests möchtest du ausführen [0-2, q]? "
if errorlevel 255 goto auswahl_fehler
if errorlevel 4 goto ende
if errorlevel 3 goto arbeitspaket_2
if errorlevel 2 goto arbeitspaket_1
if errorlevel 1 goto alle
goto ende

:alle
set "phase2Auswahl=alle vorhandenen phase-2-tests"
set "phase2Muster=test_*.py"
goto testen

:arbeitspaket_1
set "phase2Auswahl=arbeitspaket 1: prüfungsleistung und leistungsstatus"
set "phase2Muster=test_pruefungsleistung.py"
goto testen

:arbeitspaket_2
set "phase2Auswahl=arbeitspaket 2: objektbeziehungen"
set "phase2Muster=test_objektbeziehungen.py"

:testen
echo(
echo ============================================================
echo   testlauf: %phase2Auswahl%
echo ============================================================
"%phase2Python%" --version
echo(
if not exist "erprobung\%phase2Muster%" goto tests_fehlen
"%phase2Python%" -B -X utf8 -m unittest discover -s erprobung -p "%phase2Muster%" -q
set "phase2Ergebnis=%errorlevel%"
goto ergebnis

:tests_fehlen
echo [fehler] für diese auswahl wurden keine testdateien gefunden
set "phase2Ergebnis=1"

:ergebnis
echo(
if "%phase2Ergebnis%"=="0" (
    echo [ok] alle ausgewählten tests bestanden
) else (
    echo [fehler] der testlauf war nicht erfolgreich
    echo die genaue fehlermeldung steht oberhalb
)
echo ============================================================
if /i "%~1"=="--ohne-pause" goto ende
echo(
echo beliebige taste drücken, um zur testübersicht zurückzukehren
pause >nul
goto menue

:auswahl_fehler
echo [fehler] die auswahl konnte nicht gelesen werden
set "phase2Ergebnis=1"
goto ende

:ende
popd
exit /b %phase2Ergebnis%

:python_fehler
echo [fehler] python wurde nicht gefunden: %phase2Python%
popd
if /i not "%~1"=="--ohne-pause" pause
exit /b 1

:ordner_fehler
echo [fehler] der ordner der startdatei konnte nicht geöffnet werden
if /i not "%~1"=="--ohne-pause" pause
exit /b 1
