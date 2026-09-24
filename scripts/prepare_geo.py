#!/usr/bin/env python3
"""One-off: build data/geo/opstine.geojson (161 units) from
  - geoBoundaries SRB ADM2 (OSM-derived, ODbL)       data/geo/gb_adm2_simplified.geojson
  - OSM relations for Belgrade's 17 city municipalities  data/geo/bg_<id>.json (Overpass 'out geom')
  - geoBoundaries XKX ADM0 outline (shown grey, no data) data/geo/xkx_adm0.geojson
Boundaries rarely change, so this is not part of the monthly job."""
import json
import sys
import unicodedata
from pathlib import Path

from shapely.geometry import LineString, mapping, shape
from shapely.ops import polygonize, unary_union

sys.path.insert(0, str(Path(__file__).parent))
from geo_units import units  # noqa: E402

GEO = Path(__file__).resolve().parent.parent / "data" / "geo"
TOL = 0.0025  # degrees (~250 m) – plenty for a 600px-wide map
TOL_BG = 0.0008


def ascii_key(s):
    s = s.replace("đ", "dj").replace("Đ", "Dj")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower().replace("-", " ").strip()


def main():
    by_key = {ascii_key(u["name"]): u for u in units()}
    feats = []
    gb = json.loads((GEO / "gb_adm2_simplified.geojson").read_text())
    for f in gb["features"]:
        name = f["properties"]["shapeName"]
        if name == "Belgrade":
            continue
        base = name.replace(" Municipality", "").replace(" Municipal*", "").replace(" City", "")
        u = by_key.get(ascii_key(base))
        if not u:
            print("UNMATCHED", name)
            continue
        g = shape(f["geometry"]).simplify(TOL, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"slug": u["slug"], "name": u["name"]}, "geometry": mapping(g)})

    bg_names = {ascii_key(u["name"].replace(" (Beograd)", "")): u for u in units() if u["region"] == "BG"}
    for p in sorted(GEO.glob("bg_[0-9]*.json")):
        rel = json.loads(p.read_text())["elements"][0]
        nm = rel["tags"]["name:sr-Latn"].replace("Gradska opština ", "")
        u = bg_names.get(ascii_key(nm))
        if not u:
            print("UNMATCHED BG", nm)
            continue
        lines = [LineString([(pt["lon"], pt["lat"]) for pt in m["geometry"]])
                 for m in rel["members"] if m["type"] == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
        polys = list(polygonize(unary_union(lines)))
        g = unary_union(polys).simplify(TOL_BG, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"slug": u["slug"], "name": u["name"]}, "geometry": mapping(g)})

    got = {f["properties"]["slug"] for f in feats}
    missing = [u["name"] for u in units() if u["slug"] not in got]
    print(len(feats), "features; missing:", missing)

    x = json.loads((GEO / "xkx_adm0.geojson").read_text())["features"][0]
    g = shape(x["geometry"]).simplify(TOL, preserve_topology=True)
    feats.append({"type": "Feature", "properties": {"slug": "kim", "name": "AP Kosovo i Metohija"},
                  "geometry": mapping(g)})

    def rnd(o):
        if isinstance(o, (list, tuple)):
            return [rnd(v) for v in o]
        return round(o, 4) if isinstance(o, float) else o

    for f in feats:
        f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
    (GEO / "opstine.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    print("wrote", (GEO / "opstine.geojson").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
