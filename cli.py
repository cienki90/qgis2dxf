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
    ap.add_argument(
        "--crs",
        default="2000",
        help="Układ współrzędnych DXF: '2000' (domyślnie, auto strefa PL-2000 "
             "2176-2179), '1992' (EPSG:2180), 'source' (bez reprojekcji) lub "
             "konkretny kod EPSG, np. 2178.",
    )
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

    target_epsg, crs_label = _resolve_target_crs(args.crs)

    dxf_bytes = export_to_dxf(
        layers,
        selected=selected,
        include_point_labels=not args.no_labels,
        target_epsg=target_epsg,
    )

    out = args.output
    if not out:
        out = args.input.rsplit(".", 1)[0] + ".dxf"
    with open(out, "wb") as fh:
        fh.write(dxf_bytes)

    n = len(selected) if selected else len(layers)
    print(f"Zapisano {out}  ({n} warstw, układ: {crs_label}).")
    return 0


def _resolve_target_crs(value: str):
    """Map the --crs string to (target_epsg_for_export, human_label)."""
    from gpkg2dxf import AUTO_PL2000

    v = (value or "").strip().lower()
    if v in ("2000", "pl2000", "pl-2000", "auto"):
        return AUTO_PL2000, "PL-2000 (auto strefa)"
    if v in ("1992", "pl1992", "pl-1992", "cs92"):
        return 2180, "PL-1992 (EPSG:2180)"
    if v in ("source", "src", "oryginal", "oryginał"):
        return None, "oryginalny (bez reprojekcji)"
    try:
        epsg = int(v)
        return epsg, f"EPSG:{epsg}"
    except ValueError:
        from gpkg2dxf import AUTO_PL2000 as _A
        return _A, "PL-2000 (auto strefa)"


if __name__ == "__main__":
    raise SystemExit(main())
