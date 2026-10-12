# GPKG → DXF — konwerter z podglądem na mapie

Narzędzie, które eksportuje dane z pliku **GeoPackage (`.gpkg`)** do **DXF**,
z przyjaznym interfejsem webowym i podglądem lokalizacji obiektów na mapie
**OpenStreetMap**.

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

- Python 3.10+ (działa na 3.10–3.14)
- Pakiety z `requirements.txt`: Flask, Fiona, Shapely, pyproj, ezdxf

## Szybki start (Windows)

```bat
setup.bat        :: tworzy .venv i instaluje zaleznosci
uruchom.bat      :: startuje serwer i otwiera http://127.0.0.1:5000
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
python app.py        # otwórz http://127.0.0.1:5000
```

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
app.py                 — serwer Flask (upload / podgląd / eksport)
cli.py                 — konwerter z linii poleceń
gpkg2dxf/
  core.py              — logika: odczyt GPKG, reprojekcja WGS84, zapis DXF
templates/index.html   — interfejs (Leaflet + OSM, drag&drop, lista warstw)
requirements.txt       — zależności
*.bat                  — skrypty uruchomieniowe dla Windows
```

## Jak to działa (w skrócie)

1. **Odczyt** – `fiona` czyta warstwy GPKG; wewnętrzna tabela stylów QGIS
   `layer_styles` jest pomijana.
2. **Podgląd** – geometrie są reprojektowane do WGS84 (`pyproj`) i serwowane
   jako GeoJSON, który Leaflet rysuje na kafelkach OpenStreetMap.
3. **Eksport** – `ezdxf` tworzy dokument DXF (R2010), jedna warstwa GPKG =
   jedna warstwa DXF, we **współrzędnych oryginalnych** (bez reprojekcji),
   żeby rysunek nadawał się do pracy w CAD.

## Przykładowy plik

`projekt_mrowcza_gruszy_final(1).gpkg` — projekt infrastruktury
światłowodowej (warstwy: `linie`, `slupy`, `studnie`, `etykiety`) w układzie
EPSG:2180, okolice Mrozów (woj. mazowieckie).
