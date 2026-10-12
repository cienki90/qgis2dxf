"""
Command-line GPKG -> DXF converter (no web UI needed).

Examples
--------
    python cli.py input.gpkg
    python cli.py input.gpkg -o out.dxf
    python cli.py input.gpkg --layers linie studnie --no-labels
    python cli.py input.gpkg --list      # just list layers and exit
"""
from __future__ import annotations

import argparse
import sys

from gpkg2dxf import export_to_dxf, read_gpkg_layers


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Konwerter GeoPackage (.gpkg) do DXF.")
    ap.add_argument("input", help="Ścieżka do pliku .gpkg")
    ap.add_argument("-o", "--output", help="Plik wyjściowy .dxf (domyślnie obok wejścia)")
    ap.add_argument("--layers", nargs="*", help="Nazwy warstw do eksportu (domyślnie wszystkie)")
    ap.add_argument("--no-labels", action="store_true", help="Nie dodawaj etykiet tekstowych")
    ap.add_argument("--list", action="store_true", help="Wypisz warstwy i zakończ")
    args = ap.parse_args(argv)

    layers = read_gpkg_layers(args.input)

    if args.list:
        for lyr in layers:
            crs = f"EPSG:{lyr.epsg}" if lyr.epsg else (lyr.crs_name or "brak CRS")
            print(f"{lyr.name:20s} {str(lyr.geometry_type):12s} "
                  f"{lyr.feature_count:5d} obiekt.  {crs}")
            print(f"    pola: {', '.join(lyr.fields) or '—'}")
        return 0

    selected = set(args.layers) if args.layers else None
    if selected:
        known = {l.name for l in layers}
        missing = selected - known
        if missing:
            print(f"Nieznane warstwy: {', '.join(sorted(missing))}", file=sys.stderr)
            print(f"Dostępne: {', '.join(sorted(known))}", file=sys.stderr)
            return 2

    dxf_bytes = export_to_dxf(
        layers,
        selected=selected,
        include_point_labels=not args.no_labels,
    )

    out = args.output
    if not out:
        out = args.input.rsplit(".", 1)[0] + ".dxf"
    with open(out, "wb") as fh:
        fh.write(dxf_bytes)

    n = len(selected) if selected else len(layers)
    print(f"Zapisano {out}  ({n} warstw).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
