"""
Natywna aplikacja desktopowa (tkinter) do eksportu GPKG -> DXF
z podglądem obiektów na mapie OpenStreetMap (tkintermapview).

Nie wymaga przeglądarki ani serwera — to zwykły program w Pythonie.

Uruchomienie:
    python desktop.py
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import tkintermapview

from gpkg2dxf import (
    export_to_dxf,
    layers_to_map_shapes,
    read_gpkg_layers,
)

# Kolory warstw (hex) — spójne z wersją webową.
COLORS = [
    "#f97316", "#22c55e", "#3b82f6", "#e11d9a", "#eab308",
    "#06b6d4", "#a855f7", "#f43f5e", "#84cc16", "#14b8a6",
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GPKG → DXF — konwerter z podglądem na mapie OSM")
        self.geometry("1200x760")
        self.minsize(980, 600)

        self.gpkg_path: str | None = None
        self.layers = []                 # list[LayerInfo]
        self.shapes: dict[str, dict] = {}  # per-layer WGS84 shapes
        self.layer_vars: dict[str, tk.BooleanVar] = {}
        self.map_objects: dict[str, list] = {}  # drawn map widgets per layer

        self._build_ui()

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        root = ttk.Frame(self, padding=0)
        root.pack(fill="both", expand=True)

        sidebar = ttk.Frame(root, width=330, padding=12)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # 1 - plik
        ttk.Label(sidebar, text="1 · PLIK ŹRÓDŁOWY",
                  font=("", 9, "bold"), foreground="#64748b").pack(anchor="w")
        ttk.Button(sidebar, text="📂  Wybierz plik .gpkg…",
                   command=self.choose_file).pack(fill="x", pady=(6, 4))
        self.file_lbl = ttk.Label(sidebar, text="(nie wybrano)",
                                  foreground="#334155", wraplength=300)
        self.file_lbl.pack(anchor="w")
        self.status_lbl = ttk.Label(sidebar, text="", foreground="#2563eb",
                                    wraplength=300)
        self.status_lbl.pack(anchor="w", pady=(4, 10))

        ttk.Separator(sidebar).pack(fill="x", pady=4)

        # 2 - warstwy
        ttk.Label(sidebar, text="2 · WARSTWY",
                  font=("", 9, "bold"), foreground="#64748b").pack(anchor="w")
        self.layers_frame = ttk.Frame(sidebar)
        self.layers_frame.pack(fill="x", pady=6)
        self.layers_hint = ttk.Label(self.layers_frame,
                                     text="Najpierw wczytaj plik GPKG.",
                                     foreground="#94a3b8")
        self.layers_hint.pack(anchor="w")

        ttk.Separator(sidebar).pack(fill="x", pady=4)

        # 3 - eksport
        ttk.Label(sidebar, text="3 · EKSPORT",
                  font=("", 9, "bold"), foreground="#64748b").pack(anchor="w")
        self.labels_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(sidebar,
                        text="Dodaj etykiety tekstowe (opis/numer)",
                        variable=self.labels_var).pack(anchor="w", pady=(6, 8))
        self.export_btn = ttk.Button(sidebar, text="⬇  Eksportuj do DXF…",
                                     command=self.export, state="disabled")
        self.export_btn.pack(fill="x")
        self.export_lbl = ttk.Label(sidebar, text="", wraplength=300)
        self.export_lbl.pack(anchor="w", pady=(6, 0))

        # mapa
        map_frame = ttk.Frame(root)
        map_frame.pack(side="right", fill="both", expand=True)
        self.map = tkintermapview.TkinterMapView(map_frame, corner_radius=0)
        self.map.pack(fill="both", expand=True)
        self.map.set_tile_server(
            "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=19
        )
        self.map.set_position(52.0, 19.4)  # Polska
        self.map.set_zoom(6)

    # ------------------------------------------------------------- akcje
    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik GeoPackage",
            filetypes=[("GeoPackage", "*.gpkg"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        self.gpkg_path = path
        self.file_lbl.config(text=os.path.basename(path))
        self.status_lbl.config(text="⏳ Wczytywanie i analiza pliku…",
                               foreground="#2563eb")
        self.export_btn.config(state="disabled")
        # Odczyt w wątku, aby GUI nie zamarzło.
        threading.Thread(target=self._load_worker, args=(path,), daemon=True).start()

    def _load_worker(self, path: str):
        try:
            layers = read_gpkg_layers(path)
            shapes = layers_to_map_shapes(layers)
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda: self._load_failed(str(exc)))
            return
        self.after(0, lambda: self._load_done(layers, shapes))

    def _load_failed(self, msg: str):
        self.status_lbl.config(text=f"❌ Błąd: {msg}", foreground="#dc2626")
        messagebox.showerror("Błąd odczytu GPKG", msg)

    def _load_done(self, layers, shapes):
        self.layers = layers
        self.shapes = shapes
        self._render_layer_list()
        self._draw_all()
        self.status_lbl.config(
            text=f"✓ Wczytano {len(layers)} warstw.", foreground="#16a34a"
        )
        self.export_btn.config(state="normal")

    def _render_layer_list(self):
        for w in self.layers_frame.winfo_children():
            w.destroy()
        self.layer_vars.clear()
        if not self.layers:
            ttk.Label(self.layers_frame, text="Brak warstw.",
                      foreground="#94a3b8").pack(anchor="w")
            return
        for i, lyr in enumerate(self.layers):
            var = tk.BooleanVar(value=lyr.feature_count > 0)
            self.layer_vars[lyr.name] = var
            row = ttk.Frame(self.layers_frame)
            row.pack(fill="x", pady=2)
            cb = ttk.Checkbutton(
                row, variable=var,
                command=lambda n=lyr.name: self._toggle_layer(n),
            )
            cb.pack(side="left")
            tk.Canvas(row, width=12, height=12, bg=COLORS[i % len(COLORS)],
                      highlightthickness=0).pack(side="left", padx=(0, 6))
            crs = f"EPSG:{lyr.epsg}" if lyr.epsg else (lyr.crs_name or "brak CRS")
            txt = (f"{lyr.name}\n{lyr.geometry_type or '—'} · "
                   f"{lyr.feature_count} obiekt. · {crs}")
            ttk.Label(row, text=txt, justify="left").pack(side="left", anchor="w")

    # --------------------------------------------------------- rysowanie
    def _draw_all(self):
        self.map.delete_all_marker()
        self.map.delete_all_path()
        self.map.delete_all_polygon()
        self.map_objects.clear()

        all_bbox = None
        for i, lyr in enumerate(self.layers):
            color = COLORS[i % len(COLORS)]
            if self.layer_vars.get(lyr.name) and self.layer_vars[lyr.name].get():
                self._draw_layer(lyr.name, color)
            bbox = self.shapes.get(lyr.name, {}).get("bbox")
            if bbox:
                all_bbox = _merge_bbox(all_bbox, bbox)

        if all_bbox:
            min_lat, min_lon, max_lat, max_lon = all_bbox
            # mały margines
            dlat = (max_lat - min_lat) * 0.1 or 0.001
            dlon = (max_lon - min_lon) * 0.1 or 0.001
            self.map.fit_bounding_box(
                (max_lat + dlat, min_lon - dlon),
                (min_lat - dlat, max_lon + dlon),
            )

    def _draw_layer(self, name: str, color: str):
        data = self.shapes.get(name)
        if not data:
            return
        drawn = []
        for line in data["lines"]:
            drawn.append(self.map.set_path(line, color=color, width=3))
        for poly in data["polygons"]:
            drawn.append(self.map.set_polygon(poly, outline_color=color,
                                              fill_color=None, border_width=2))
        for pt in data["points"]:
            lat, lon = pt["pos"]
            drawn.append(self.map.set_marker(
                lat, lon, text=pt["label"] or "",
                marker_color_circle=color, marker_color_outside="#0f172a",
            ))
        self.map_objects[name] = drawn

    def _toggle_layer(self, name: str):
        on = self.layer_vars[name].get()
        if on:
            idx = next(i for i, l in enumerate(self.layers) if l.name == name)
            self._draw_layer(name, COLORS[idx % len(COLORS)])
        else:
            for obj in self.map_objects.get(name, []):
                try:
                    obj.delete()
                except Exception:
                    pass
            self.map_objects[name] = []

    # ----------------------------------------------------------- eksport
    def export(self):
        selected = {n for n, v in self.layer_vars.items() if v.get()}
        if not selected:
            messagebox.showwarning("Eksport", "Zaznacz co najmniej jedną warstwę.")
            return
        default = "export.dxf"
        if self.gpkg_path:
            base = os.path.splitext(os.path.basename(self.gpkg_path))[0]
            default = base + ".dxf"
        out = filedialog.asksaveasfilename(
            title="Zapisz jako DXF", defaultextension=".dxf",
            initialfile=default, filetypes=[("DXF", "*.dxf")],
        )
        if not out:
            return
        try:
            data = export_to_dxf(
                self.layers,
                selected=selected,
                include_point_labels=self.labels_var.get(),
            )
            with open(out, "wb") as fh:
                fh.write(data)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Błąd eksportu", str(exc))
            self.export_lbl.config(text=f"❌ {exc}", foreground="#dc2626")
            return
        self.export_lbl.config(text=f"✓ Zapisano: {os.path.basename(out)}",
                               foreground="#16a34a")
        messagebox.showinfo("Eksport", f"Zapisano plik:\n{out}")


def _merge_bbox(a, b):
    if a is None:
        return b
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


if __name__ == "__main__":
    App().mainloop()
