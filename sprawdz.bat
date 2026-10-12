@echo off
chcp 65001 >nul
rem === Walidacja instalacji i testowa konwersja przykladowego pliku ===
setlocal

if not exist ".venv\Scripts\activate.bat" (
    echo [BLAD] Brak srodowiska .venv. Uruchom najpierw setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo === Sprawdzanie zaleznosci ===
python -c "import flask, fiona, shapely, pyproj, ezdxf; print('OK - wszystkie pakiety dostepne')"
if errorlevel 1 (
    echo [BLAD] Brakuje zaleznosci. Uruchom setup.bat
    pause
    exit /b 1
)

echo.
echo === Lista warstw w przykladowym pliku ===
python cli.py "projekt_mrowcza_gruszy_final(1).gpkg" --list

echo.
echo === Testowa konwersja do _test_wynik.dxf ===
python cli.py "projekt_mrowcza_gruszy_final(1).gpkg" -o "_test_wynik.dxf"
if exist "_test_wynik.dxf" (
    echo [OK] Plik _test_wynik.dxf zostal utworzony.
) else (
    echo [BLAD] Nie utworzono pliku DXF.
)
pause
