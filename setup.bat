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
echo Aktualizacja pip ...
python -m pip install --upgrade pip
echo Instalacja pakietow z requirements.txt ...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [BLAD] Instalacja zaleznosci nie powiodla sie.
    pause
    exit /b 1
)

echo.
echo === Gotowe. Uruchom aplikacje przez: uruchom.bat ===
pause
