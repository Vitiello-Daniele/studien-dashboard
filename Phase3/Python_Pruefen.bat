@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title phase 3: python-prüfung
set "phase3Ergebnis=0"
pushd "%~dp0"
if errorlevel 1 exit /b 1
if /i "%~1"=="--ohne-pause" goto alle

:menue
cls
echo(
echo ============================================================
echo   phase 3: testübersicht
echo ============================================================
echo(
echo [0] alles testen
echo(
echo [1] fachklassen und zuordnungen
echo     [test] noten, status und doppelte leistungen
echo     [test] semesterwechsel und gültige planungsangaben
echo     [test] monatsenden und schaltjahr
echo(
echo [2] kennzahlen und zeitplanung
echo     [test] referenzwerte aus phase 1
echo     [test] teilzeit, vollzeit, wechsel und zeitstatus
echo     [test] fehlende werte und ects ohne doppelzählung
echo(
echo [3] dateien laden und speichern
echo     [test] unveränderte fachwerte und modulreferenzen
echo     [test] ungültige json-dateien
echo     [test] schreibfehler und gesperrte dateien
echo(
echo [4] eingaben und abläufe
echo     [test] leistungen ergänzen und ändern
echo     [test] eindeutige zielpositionen und unveränderbare anzeigedaten
echo     [test] studienmodell und planung übernehmen
echo     [test] änderungen bis zum speichern erhalten
echo(
echo [5] bedienoberfläche
echo     [test] semesterfilter und leistungsdialog
echo     [test] zusätzliche leistung im gefilterten semester bearbeiten
echo     [test] einstellungen und fehlermeldungen
echo     [test] ungespeicherte änderungen beim schließen
echo(
echo [q] beenden
echo(
choice /c 012345q /n /m "welche tests möchtest du ausführen [0-5, q]? "
if errorlevel 255 goto auswahl_fehler
if errorlevel 7 goto ende
if errorlevel 6 goto oberflaeche
if errorlevel 5 goto controller
if errorlevel 4 goto repository
if errorlevel 3 goto kennzahlen
if errorlevel 2 goto fachklassen
if errorlevel 1 goto alle
goto ende

:fachklassen
set "phase3Muster=test_fachklassen.py"
goto testen
:kennzahlen
set "phase3Muster=test_kennzahlen.py"
goto testen
:repository
set "phase3Muster=test_repository.py"
goto testen
:controller
set "phase3Muster=test_controller.py"
goto testen
:oberflaeche
set "phase3Muster=test_oberflaeche.py"
goto testen
:alle
set "phase3Muster=test_*.py"

:testen
echo(
echo ============================================================
echo   testlauf: %phase3Muster%
echo ============================================================
if not exist "tests\%phase3Muster%" goto tests_fehlen
call "%~dp0Python_Ausfuehren.bat" -m unittest discover -s tests -p "%phase3Muster%" -v
set "phase3Ergebnis=%errorlevel%"
goto ergebnis

:tests_fehlen
echo [fehler] keine testdateien für die auswahl gefunden
set "phase3Ergebnis=1"

:ergebnis
echo(
if "%phase3Ergebnis%"=="0" (
    echo [ok] alle ausgewählten tests bestanden
) else (
    echo [fehler] der testlauf war nicht erfolgreich
    echo die genaue fehlermeldung steht oberhalb
)
echo ============================================================
if /i "%~1"=="--ohne-pause" goto ende
pause
goto menue

:auswahl_fehler
set "phase3Ergebnis=1"
:ende
popd
exit /b %phase3Ergebnis%
