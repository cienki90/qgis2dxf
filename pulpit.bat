@echo off
chcp 65001 >nul
rem === Uruchomienie natywnej aplikacji desktopowej GPKG -> DXF (tkinter + mapa OSM) ===
setlocal

if not exist ".venv\Scripts\activate.bat" (
    echo [BLAD] Brak srodowiska .venv. Uruchom najpierw setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo Uruchamiam aplikacje desktopowa (okno z mapa OpenStreetMap)...
python desktop.py
if errorlevel 1 (
    echo [BLAD] Aplikacja zakonczyla sie bledem.
    pause
    exit /b 1
)
