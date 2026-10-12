# GPKG → DXF — konwerter z podglądem na mapie

Narzędzie, które eksportuje dane z pliku **GeoPackage (`.gpkg`)** do **DXF**,
z przyjaznym interfejsem i podglądem lokalizacji obiektów na mapie
**OpenStreetMap**. Dostępne w dwóch wariantach — oba w czystym Pythonie:

- 🖥️ **Desktop** (`desktop.py`) — natywne okno **tkinter + tkintermapview**,
  bez przeglądarki i bez serwera. Odpalasz jeden plik `.py`.
- 🌐 **Web** (`app.py`) — serwer **Flask** + mapa **Leaflet** w przeglądarce.
- ⌨️ **CLI** (`cli.py`) — konwersja z linii poleceń.

![flow](https://img.shields.io/badge/GPKG-%E2%86%92%20DXF-f97316)

## Co potrafi

- 📂 Wczytuje dowolny plik `.gpkg` (przeciągnij-i-upuść lub wybierz).
- 🗺️ Pokazuje wszystkie warstwy na interaktywnej mapie OSM (Leaflet) —
  linie, punkty, poligony. Reprojekcja do WGS84 następuje automatycznie
  (np. z układu krajowego **ETRF2000-PL / CS92, EPSG:2180**).
- 🧷 Klikasz obiekt → popup z jego atrybutami. Warstwy można włączać/wyłączać.
- 💾 Wybierasz warstwy i pobierasz plik `.dxf`:
  - każda warstwa GPKG → osobna warstwa DXF (z kolorem),
  - oryginalne współrzędne (np. EPSG:2180) są zachowane — rysunek pozostaje
    geo-poprawny dla CAD / geodezji,
  - punkty mają marker (krzyżyk) + opcjonalną etykietę tekstową
    (`opis` / `numer` / `nazwa`).

## Wymagania

- Python 3.10–3.12 (64-bit zalecany)
- Pakiety z `requirements.txt`: Flask, **pyogrio**, Shapely, pyproj, ezdxf,
  tkintermapview

> **Dlaczego pyogrio, a nie Fiona?** `pyogrio` dostarcza gotowe pakiety
> (*wheele*) z **wbudowanym GDAL**, więc `pip install` działa od ręki na
> Windows/macOS/Linux — bez instalowania GDAL w systemie i bez kompilacji.

## Szybki start (Windows)

```bat
setup.bat        :: tworzy .venv i instaluje zaleznosci
pulpit.bat       :: aplikacja DESKTOPOWA (okno z mapa OSM) — zalecane
uruchom.bat      :: wersja WEB — startuje serwer i otwiera http://127.0.0.1:5000
```

Dodatkowo:

```bat
sprawdz.bat                 :: walidacja instalacji + testowa konwersja
konwertuj.bat plik.gpkg     :: szybka konwersja z CLI (lub przeciagnij plik na .bat)
```

## Szybki start (Linux / macOS)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python desktop.py    # natywne okno z mapą (desktop)
# albo
python app.py        # wersja web — otwórz http://127.0.0.1:5000
```

> Wersja desktopowa wymaga działającego środowiska graficznego (na Linuksie
> także pakietu `python3-tk`). Na Windows i macOS tkinter jest wbudowany.

## Użycie z linii poleceń (bez przeglądarki)

```bash
python cli.py plik.gpkg                       # eksport wszystkich warstw
python cli.py plik.gpkg -o wynik.dxf          # własna nazwa wyjścia
python cli.py plik.gpkg --layers linie studnie # tylko wybrane warstwy
python cli.py plik.gpkg --no-labels           # bez etykiet tekstowych
python cli.py plik.gpkg --list                # tylko wypisz warstwy i CRS
```

## Struktura projektu

```
desktop.py             — aplikacja desktopowa (tkinter + tkintermapview, mapa OSM)
app.py                 — serwer Flask (upload / podgląd / eksport) — wersja web
cli.py                 — konwerter z linii poleceń
gpkg2dxf/
  core.py              — logika: odczyt GPKG, reprojekcja WGS84, zapis DXF
templates/index.html   — interfejs web (Leaflet + OSM, drag&drop, lista warstw)
requirements.txt       — zależności
*.bat                  — skrypty uruchomieniowe dla Windows
```

## Jak to działa (w skrócie)

1. **Odczyt** – `pyogrio` (GDAL/OGR) czyta warstwy GPKG; wewnętrzna tabela
   stylów QGIS `layer_styles` jest pomijana. Geometrie wczytywane są jako WKB
   i dekodowane przez Shapely.
2. **Podgląd** – geometrie są reprojektowane do WGS84 (`pyproj`) i serwowane
   jako GeoJSON, który Leaflet rysuje na kafelkach OpenStreetMap.
3. **Eksport** – `ezdxf` tworzy dokument DXF (R2010), jedna warstwa GPKG =
   jedna warstwa DXF, we **współrzędnych oryginalnych** (bez reprojekcji),
   żeby rysunek nadawał się do pracy w CAD.

## Przykładowy plik

`projekt_mrowcza_gruszy_final(1).gpkg` — projekt infrastruktury
światłowodowej (warstwy: `linie`, `slupy`, `studnie`, `etykiety`) w układzie
EPSG:2180, okolice Mrozów (woj. mazowieckie).

## Rozwiązywanie problemów

**`A GDAL API version must be specified ... gdal-config` przy instalacji Fiony**
Ten projekt **nie używa już Fiony** — zależnością jest `pyogrio` (gotowe wheele
z wbudowanym GDAL). Jeśli widzisz ten błąd, masz stary `requirements.txt`
albo środowisko z zainstalowaną Fioną. Zrób świeżą instalację:

```bat
rmdir /s /q .venv
setup.bat
```

lub ręcznie:

```bash
pip install --upgrade pip
pip install --prefer-binary -r requirements.txt
```

**Brak okna / błąd `tkinter` w wersji desktopowej (Linux)**
Zainstaluj systemowy pakiet Tk: `sudo apt install python3-tk`. Na Windows i
macOS tkinter jest wbudowany w Pythona.
