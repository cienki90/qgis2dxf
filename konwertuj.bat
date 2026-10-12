@echo off
chcp 65001 >nul
rem === Szybka konwersja z linii polecen: przeciagnij plik .gpkg na ten plik .bat ===
setlocal

if not exist ".venv\Scripts\activate.bat" (
    echo [BLAD] Brak srodowiska .venv. Uruchom najpierw setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

if "%~1"=="" (
    echo Uzycie: przeciagnij plik .gpkg na ten plik, lub:
    echo    konwertuj.bat sciezka\do\pliku.gpkg
    pause
    exit /b 1
)

echo Konwertuje: %~1
python cli.py "%~1"
if errorlevel 1 (
    echo [BLAD] Konwersja nie powiodla sie.
    pause
    exit /b 1
)

echo.
echo === Gotowe. Plik .dxf zapisany obok pliku zrodlowego. ===
pause
