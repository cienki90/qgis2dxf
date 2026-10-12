"""
GPKG -> DXF web tool.

A small Flask application that lets a user:
  1. Upload a .gpkg file.
  2. See its layers and attributes.
  3. Preview all geometry on an OpenStreetMap basemap (Leaflet).
  4. Pick which layers to export and download a .dxf.

Run:
    python app.py
Then open http://127.0.0.1:5000
"""
from __future__ import annotations

import io
import os
import tempfile
import uuid

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)

from gpkg2dxf import (
    AUTO_PL2000,
    export_to_dxf,
    layers_to_geojson_wgs84,
    read_gpkg_layers,
)


def _resolve_target_crs(value):
    """Map a UI/API 'crs' value to the export target_epsg argument."""
    v = str(value or "").strip().lower()
    if v in ("2000", "pl2000", "pl-2000", "auto"):
        return AUTO_PL2000
    if v in ("1992", "pl1992", "pl-1992", "cs92"):
        return 2180
    if v in ("source", "src"):
        return None
    try:
        return int(v)
    except ValueError:
        return AUTO_PL2000

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024 * 1024  # 256 MB upload cap

# Uploaded files are stored in a temp dir keyed by a random token returned to
# the browser. This keeps server state tiny and avoids re-uploading on export.
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "gpkg2dxf_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _stored_path(token: str) -> str:
    # token is a uuid4 hex; reject anything else to avoid path traversal.
    if not token or any(c not in "0123456789abcdef" for c in token):
        raise ValueError("invalid token")
    return os.path.join(UPLOAD_DIR, f"{token}.gpkg")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Nie przesłano pliku."}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Pusta nazwa pliku."}), 400
    if not f.filename.lower().endswith(".gpkg"):
        return jsonify({"error": "Oczekiwano pliku .gpkg."}), 400

    token = uuid.uuid4().hex
    path = _stored_path(token)
    f.save(path)

    try:
        layers = read_gpkg_layers(path)
    except Exception as exc:  # noqa: BLE001
        os.remove(path)
        return jsonify({"error": f"Nie udało się odczytać GPKG: {exc}"}), 400

    geojson = layers_to_geojson_wgs84(layers)
    return jsonify(
        {
            "token": token,
            "filename": f.filename,
            "layers": [lyr.summary() for lyr in layers],
            "geojson": geojson,
        }
    )


@app.route("/api/export", methods=["POST"])
def export():
    data = request.get_json(force=True, silent=True) or {}
    token = data.get("token", "")
    selected = data.get("layers")  # list[str] or None
    include_labels = bool(data.get("include_labels", True))
    target_epsg = _resolve_target_crs(data.get("crs", "2000"))

    try:
        path = _stored_path(token)
    except ValueError:
        return jsonify({"error": "Nieprawidłowy token sesji."}), 400
    if not os.path.exists(path):
        return jsonify({"error": "Plik wygasł, prześlij go ponownie."}), 410

    try:
        layers = read_gpkg_layers(path)
        selected_set = set(selected) if selected else None
        dxf_bytes = export_to_dxf(
            layers,
            selected=selected_set,
            include_point_labels=include_labels,
            target_epsg=target_epsg,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Błąd eksportu: {exc}"}), 500

    out_name = data.get("filename", "export") or "export"
    if out_name.lower().endswith(".gpkg"):
        out_name = out_name[:-5]
    out_name = out_name + ".dxf"

    return send_file(
        io.BytesIO(dxf_bytes),
        mimetype="application/dxf",
        as_attachment=True,
        download_name=out_name,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
