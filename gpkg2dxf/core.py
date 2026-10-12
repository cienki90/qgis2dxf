"""
Core logic for reading GeoPackage (GPKG) files and exporting their contents
to DXF, plus helpers for building an OSM/Leaflet preview (GeoJSON in WGS84).

Design notes
------------
* A GPKG is read with ``pyogrio`` (GDAL/OGR bindings that ship as prebuilt
  wheels with a bundled GDAL — so ``pip install`` needs no system GDAL, unlike
  Fiona which otherwise tries to compile against ``gdal-config``). The QGIS
  internal style table ``layer_styles`` is skipped because it has no geometry.
* The DXF is written with ezdxf. Each GPKG layer becomes one DXF layer. The
  original projected coordinates (e.g. EPSG:2180) are preserved in the DXF so
  the drawing stays geo-correct for CAD/surveying use.
* For the map preview we reproject every geometry to EPSG:4326 (WGS84) so it
  can be drawn on an OpenStreetMap basemap with Leaflet.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

import ezdxf
from pyogrio import list_layers
from pyogrio.raw import read as _ogr_read
from pyproj import CRS, Transformer
from shapely import wkb as _wkb
from shapely.geometry import mapping, shape
from shapely.ops import transform as shp_transform

# QGIS stores symbology in this non-spatial table; it is not a real layer.
SKIP_LAYERS = {"layer_styles"}

# A readable palette of ACI (AutoCAD Color Index) colors assigned to layers
# in order, so the exported DXF is not all one color.
ACI_PALETTE = [1, 3, 5, 6, 2, 4, 30, 40, 150, 8]  # red, green, blue, magenta...


@dataclass
class LayerInfo:
    """Metadata and content for a single GPKG layer."""

    name: str
    geometry_type: str | None
    feature_count: int
    fields: list[str] = field(default_factory=list)
    epsg: int | None = None
    crs_name: str | None = None
    features: list[dict] = field(default_factory=list)  # fiona-style records

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "geometry_type": self.geometry_type,
            "feature_count": self.feature_count,
            "fields": self.fields,
            "epsg": self.epsg,
            "crs_name": self.crs_name,
        }


def _resolve_crs(crs_str: str | None) -> tuple[int | None, str | None]:
    """Return (epsg, human_name) from pyogrio's CRS string (e.g. 'EPSG:2180')."""
    if not crs_str:
        return None, None
    try:
        crs = CRS.from_user_input(crs_str)
    except Exception:
        return None, None
    epsg = crs.to_epsg()
    if epsg is None:
        # Polish national grids sometimes fail strict EPSG matching; loosen it.
        epsg = crs.to_epsg(min_confidence=20)
    return epsg, crs.name


def _to_native(value):
    """Convert numpy scalars / NaT / NaN to plain Python for JSON + DXF text."""
    if value is None:
        return None
    # numpy scalar -> python scalar
    item = getattr(value, "item", None)
    if callable(item):
        try:
            value = value.item()
        except Exception:
            pass
    # NaN -> None
    try:
        if isinstance(value, float) and value != value:
            return None
    except Exception:
        pass
    return value


def read_gpkg_layers(path: str) -> list[LayerInfo]:
    """Read every spatial layer from a GPKG into LayerInfo objects.

    Uses pyogrio's raw reader, which returns, per layer:
        (meta, fids, geometries_as_wkb, field_data_columns)
    Geometries (WKB) are decoded with shapely and stored as GeoJSON-style
    dicts so the rest of the pipeline stays format-agnostic.

    Features are materialised into memory. GPKG files handled by this tool are
    survey/infrastructure projects (hundreds to low-thousands of features), so
    this is fine; for very large datasets a streaming approach would be needed.
    """
    result: list[LayerInfo] = []
    layer_table = list_layers(path)  # ndarray of [name, geometry_type]
    for row in layer_table:
        layer_name = row[0]
        if layer_name in SKIP_LAYERS:
            continue

        meta, _fids, geometries, field_data = _ogr_read(path, layer=layer_name)
        field_names = list(meta.get("fields", []))
        epsg, crs_name = _resolve_crs(meta.get("crs"))

        n = len(geometries) if geometries is not None else 0
        features: list[dict] = []
        for i in range(n):
            geom_dict = None
            wkb_bytes = geometries[i] if geometries is not None else None
            if wkb_bytes is not None:
                try:
                    geom_dict = mapping(_wkb.loads(bytes(wkb_bytes)))
                except Exception:
                    geom_dict = None
            props = {
                field_names[c]: _to_native(field_data[c][i])
                for c in range(len(field_names))
            }
            features.append({"geometry": geom_dict, "properties": props})

        info = LayerInfo(
            name=layer_name,
            geometry_type=meta.get("geometry_type"),
            feature_count=len(features),
            fields=field_names,
            epsg=epsg,
            crs_name=crs_name,
            features=features,
        )
        result.append(info)
    return result


def layers_to_geojson_wgs84(layers: list[LayerInfo]) -> dict[str, Any]:
    """Build a FeatureCollection reprojected to WGS84 for the Leaflet preview.

    A ``layer`` property is injected on every feature so the frontend can style
    and toggle layers independently.
    """
    transformers: dict[int, Transformer] = {}

    def get_transformer(epsg: int) -> Transformer | None:
        if epsg == 4326:
            return None
        if epsg not in transformers:
            transformers[epsg] = Transformer.from_crs(epsg, 4326, always_xy=True)
        return transformers[epsg]

    out_features: list[dict] = []
    for layer in layers:
        if not layer.epsg:
            # Unknown CRS -> cannot place on an OSM basemap reliably; skip in
            # preview but it will still export to DXF with raw coordinates.
            continue
        tr = get_transformer(layer.epsg)
        for feat in layer.features:
            geom = feat["geometry"]
            if not geom:
                continue
            geom_obj = shape(geom)
            if tr is not None:
                geom_obj = shp_transform(
                    lambda x, y, z=None: tr.transform(x, y), geom_obj
                )
            props = dict(feat["properties"])
            props["__layer__"] = layer.name
            out_features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(geom_obj),
                    "properties": props,
                }
            )
    return {"type": "FeatureCollection", "features": out_features}


def layers_to_map_shapes(layers: list[LayerInfo]) -> dict[str, dict]:
    """Reproject geometries to WGS84 grouped per layer for a native map widget.

    Returns ``{layer_name: {"points": [...], "lines": [...], "polygons": [...],
    "labels": [...], "bbox": (min_lat, min_lon, max_lat, max_lon) | None}}``.

    Coordinates use ``(lat, lon)`` ordering, which is what tkintermapview
    (set_marker / set_path / set_polygon) expects.
    """
    transformers: dict[int, Transformer] = {}

    def get_transformer(epsg: int) -> Transformer | None:
        if epsg == 4326:
            return None
        if epsg not in transformers:
            transformers[epsg] = Transformer.from_crs(epsg, 4326, always_xy=True)
        return transformers[epsg]

    def to_latlon(geom_obj, tr):
        if tr is not None:
            geom_obj = shp_transform(lambda x, y, z=None: tr.transform(x, y), geom_obj)
        return geom_obj

    result: dict[str, dict] = {}
    for layer in layers:
        entry = {"points": [], "lines": [], "polygons": [], "labels": [], "bbox": None}
        result[layer.name] = entry
        if not layer.epsg:
            continue
        tr = get_transformer(layer.epsg)
        label_field = _default_label_field(layer.fields)

        min_lat = min_lon = float("inf")
        max_lat = max_lon = float("-inf")

        def track(lat, lon):
            nonlocal min_lat, min_lon, max_lat, max_lon
            min_lat, max_lat = min(min_lat, lat), max(max_lat, lat)
            min_lon, max_lon = min(min_lon, lon), max(max_lon, lon)

        for feat in layer.features:
            geom = feat["geometry"]
            if not geom:
                continue
            g = to_latlon(shape(geom), tr)
            gtype = g.geom_type
            label = feat["properties"].get(label_field) if label_field else None
            label = None if label in (None, "") else str(label)

            def line_coords(ls):
                return [(y, x) for (x, y) in ls.coords]

            if gtype == "Point":
                lat, lon = g.y, g.x
                entry["points"].append({"pos": (lat, lon), "label": label})
                track(lat, lon)
            elif gtype == "MultiPoint":
                for p in g.geoms:
                    entry["points"].append({"pos": (p.y, p.x), "label": label})
                    track(p.y, p.x)
            elif gtype == "LineString":
                coords = line_coords(g)
                entry["lines"].append(coords)
                for lat, lon in coords:
                    track(lat, lon)
            elif gtype == "MultiLineString":
                for part in g.geoms:
                    coords = line_coords(part)
                    entry["lines"].append(coords)
                    for lat, lon in coords:
                        track(lat, lon)
            elif gtype == "Polygon":
                coords = line_coords(g.exterior)
                entry["polygons"].append(coords)
                for lat, lon in coords:
                    track(lat, lon)
            elif gtype == "MultiPolygon":
                for poly in g.geoms:
                    coords = line_coords(poly.exterior)
                    entry["polygons"].append(coords)
                    for lat, lon in coords:
                        track(lat, lon)

        if min_lat != float("inf"):
            entry["bbox"] = (min_lat, min_lon, max_lat, max_lon)
    return result


def _add_label(msp, layer_name: str, x: float, y: float, text: str, height: float):
    """Add a single-line TEXT entity anchored at (x, y)."""
    txt = msp.add_text(
        str(text),
        dxfattribs={"layer": layer_name, "height": height},
    )
    # ezdxf 1.x API: set placement after creation
    txt.set_placement((x, y))


def _geom_bbox_diagonal(layers: list[LayerInfo]) -> float:
    """Rough drawing extent, used to scale text height sensibly."""
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for layer in layers:
        for feat in layer.features:
            geom = feat["geometry"]
            if not geom:
                continue
            try:
                b = shape(geom).bounds
            except Exception:
                continue
            minx, miny = min(minx, b[0]), min(miny, b[1])
            maxx, maxy = max(maxx, b[2]), max(maxy, b[3])
    if minx == float("inf"):
        return 100.0
    diag = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
    return diag or 100.0


def export_to_dxf(
    layers: list[LayerInfo],
    selected: set[str] | None = None,
    label_field_by_layer: dict[str, str] | None = None,
    include_point_labels: bool = True,
) -> bytes:
    """Convert the given layers to a DXF document and return it as bytes.

    Parameters
    ----------
    layers:
        Layers read from the GPKG.
    selected:
        Names of layers to export. ``None`` exports all.
    label_field_by_layer:
        Optional map ``{layer_name: field_name}`` picking which attribute to
        render as TEXT. If a layer is absent, a sensible default is chosen.
    include_point_labels:
        When True, point layers get a TEXT label next to each point.
    """
    label_field_by_layer = label_field_by_layer or {}
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 6  # meters
    msp = doc.modelspace()

    diag = _geom_bbox_diagonal(layers)
    text_height = max(diag * 0.004, 0.5)
    marker = max(diag * 0.0025, 0.3)

    color_idx = 0
    for layer in layers:
        if selected is not None and layer.name not in selected:
            continue

        dxf_layer_name = _sanitize_layer_name(layer.name)
        aci = ACI_PALETTE[color_idx % len(ACI_PALETTE)]
        color_idx += 1
        if dxf_layer_name not in doc.layers:
            doc.layers.add(name=dxf_layer_name, color=aci)

        # Choose a label field: explicit > first string-ish attribute.
        label_field = label_field_by_layer.get(layer.name)
        if label_field is None:
            label_field = _default_label_field(layer.fields)

        for feat in layer.features:
            geom = feat["geometry"]
            props = feat["properties"]
            if geom:
                _draw_geometry(msp, dxf_layer_name, geom, marker)

            if (
                include_point_labels
                and label_field
                and props.get(label_field) not in (None, "")
                and geom
                and geom.get("type") in ("Point", "MultiPoint")
            ):
                pt = _first_point(geom)
                if pt:
                    _add_label(
                        msp,
                        dxf_layer_name,
                        pt[0] + marker,
                        pt[1] + marker,
                        props.get(label_field),
                        text_height,
                    )

    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode("utf-8")


def _sanitize_layer_name(name: str) -> str:
    # DXF layer names cannot contain < > / \ " : ; ? * | = `
    bad = '<>/\\":;?*|=`'
    return "".join("_" if c in bad else c for c in name) or "layer"


def _default_label_field(fields: list[str]) -> str | None:
    preferred = ["opis", "numer", "nazwa", "name", "label", "id"]
    lower = {f.lower(): f for f in fields}
    for p in preferred:
        if p in lower:
            return lower[p]
    return fields[0] if fields else None


def _first_point(geom: dict):
    gtype = geom["type"]
    coords = geom["coordinates"]
    if gtype == "Point":
        return coords
    if gtype == "MultiPoint" and coords:
        return coords[0]
    return None


def _draw_geometry(msp, layer_name: str, geom: dict, marker: float):
    gtype = geom["type"]
    coords = geom["coordinates"]
    attribs = {"layer": layer_name}

    if gtype == "Point":
        _draw_point(msp, layer_name, coords, marker)
    elif gtype == "MultiPoint":
        for c in coords:
            _draw_point(msp, layer_name, c, marker)
    elif gtype == "LineString":
        msp.add_lwpolyline([(c[0], c[1]) for c in coords], dxfattribs=attribs)
    elif gtype == "MultiLineString":
        for part in coords:
            msp.add_lwpolyline([(c[0], c[1]) for c in part], dxfattribs=attribs)
    elif gtype == "Polygon":
        _draw_polygon(msp, layer_name, coords)
    elif gtype == "MultiPolygon":
        for poly in coords:
            _draw_polygon(msp, layer_name, poly)


def _draw_point(msp, layer_name: str, c, marker: float):
    x, y = c[0], c[1]
    # A real POINT plus a small cross marker so it is visible in any viewer.
    msp.add_point((x, y), dxfattribs={"layer": layer_name})
    msp.add_line((x - marker, y), (x + marker, y), dxfattribs={"layer": layer_name})
    msp.add_line((x, y - marker), (x, y + marker), dxfattribs={"layer": layer_name})


def _draw_polygon(msp, layer_name: str, rings):
    for ring in rings:
        msp.add_lwpolyline(
            [(c[0], c[1]) for c in ring],
            dxfattribs={"layer": layer_name},
            close=True,
        )
