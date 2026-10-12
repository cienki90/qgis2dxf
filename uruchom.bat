@echo off
chcp 65001 >nul
rem === Uruchomienie aplikacji webowej GPKG -> DXF ===
setlocal

if not exist ".venv\Scripts\activate.bat" (
    echo [BLAD] Brak srodowiska .venv. Uruchom najpierw setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo.
echo Serwer startuje pod adresem:  http://127.0.0.1:5000
echo Otworze przegladarke za chwile. Zatrzymanie: Ctrl+C
echo.

rem Otworz przegladarke po krotkiej pauzie, serwer dziala w tym samym oknie
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:5000"

python app.py

pause
