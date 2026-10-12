@echo off
chcp 65001 >nul
rem === Instalacja zaleznosci dla narzedzia GPKG -> DXF ===
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo [BLAD] Nie znaleziono Pythona. Zainstaluj Python 3.10+ z python.org
        pause
        exit /b 1
    )
)

echo Uzywam: %PY%
%PY% --version

echo.
echo Tworzenie srodowiska wirtualnego .venv ...
%PY% -m venv .venv
if errorlevel 1 (
    echo [BLAD] Nie udalo sie utworzyc .venv
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Aktualizacja pip / setuptools / wheel ...
python -m pip install --upgrade pip setuptools wheel
echo Instalacja pakietow z requirements.txt ...
rem --prefer-binary wymusza gotowe wheele (np. pyogrio z wbudowanym GDAL),
rem dzieki czemu nie jest potrzebny systemowy GDAL ani kompilator.
python -m pip install --prefer-binary -r requirements.txt
if errorlevel 1 (
    echo.
    echo [BLAD] Instalacja zaleznosci nie powiodla sie.
    echo   Upewnij sie, ze masz Python 3.10-3.12 (64-bit) i aktualny pip.
    pause
    exit /b 1
)

echo.
echo === Gotowe. ===
echo   pulpit.bat   - aplikacja desktopowa (okno z mapa)
echo   uruchom.bat  - wersja web (http://127.0.0.1:5000)
pause
