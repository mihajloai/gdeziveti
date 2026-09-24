#!/usr/bin/env python3
"""One-off (re-run only when motorways/airports change): connectivity per municipality.

For every municipality seat (OSM place node inside the municipality; polygon centre for
Belgrade's inner-city municipalities) compute driving time (OSRM, OpenStreetMap roads) to:
  - nearest large business centre: Beograd, Novi Sad, Niš, Kragujevac
  - nearest motorway junction (OSM highway=motorway_junction inside Serbia)
  - nearest international airport: Beograd (BEG), Niš (INI), Morava/Kraljevo (KVO)

Inputs:  data/geo/opstine.geojson, data/geo/conn/{junctions,towns,villages}.json (Overpass dumps)
Output:  data/clean/povezanost.csv
"""
import csv
import json
import math
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from geo_units import units  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GEO = ROOT / "data" / "geo"
OSRM = "https://router.project-osrm.org/table/v1/driving/"

CENTERS = {"Beograd": (20.4612, 44.8125), "Novi Sad": (19.8452, 45.2551),
           "Niš": (21.8958, 43.3209), "Kragujevac": (20.9114, 44.0128)}
AIRPORTS = {"Aerodrom Beograd": (20.3091, 44.8184), "Aerodrom Niš": (21.8537, 43.3373),
            "Aerodrom Morava (Kraljevo)": (20.5872, 43.8183)}
# Inner Belgrade city municipalities: approximate centre of the built-up part (municipal hall area)
BG_INNER = {"Stari grad": (20.4569, 44.8176), "Vračar": (20.4780, 44.7990), "Savski venac": (20.4520, 44.7960),
            "Novi Beograd": (20.4210, 44.8150), "Zvezdara": (20.5050, 44.7960), "Palilula (Beograd)": (20.4850, 44.8180),
            "Voždovac": (20.4800, 44.7780), "Zemun": (20.4010, 44.8430), "Čukarica": (20.4160, 44.7830),
            "Rakovica": (20.4410, 44.7430)}


def key(s):
    s = s.replace("đ", "dj").replace("Đ", "Dj")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


D = {"Lj": "Љ", "lj": "љ", "Nj": "Њ", "nj": "њ", "Dž": "Џ", "dž": "џ"}
S = dict(zip("ABVGDĐEŽZIJKLMNOPRSTĆUFHCČŠabvgdđežzijklmnoprstćufhcčš",
             "АБВГДЂЕЖЗИЈКЛМНОПРСТЋУФХЦЧШабвгдђежзијклмнопрстћуфхцчш"))


def cyr(s):
    o, i = "", 0
    while i < len(s):
        if s[i:i + 2] in D:
            o += D[s[i:i + 2]]
            i += 2
        else:
            o += S.get(s[i], s[i])
            i += 1
    return o


def hav(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def osrm(src, dests):
    coords = ";".join(f"{x:.5f},{y:.5f}" for x, y in [src] + dests)
    url = OSRM + coords + "?sources=0&annotations=duration"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gdeziveti.rs one-off connectivity calc"})
            d = json.load(urllib.request.urlopen(req, timeout=60))
            if d.get("code") == "Ok":
                return d["durations"][0][1:]
        except Exception as e:  # noqa: BLE001
            print("  retry", e)
        time.sleep(3 + attempt * 3)
    raise SystemExit("OSRM failed")


def main():
    gj = json.loads((GEO / "opstine.geojson").read_text())
    poly = {f["properties"]["slug"]: shape(f["geometry"]).buffer(0) for f in gj["features"] if f["properties"]["slug"] != "kim"}
    serbia = unary_union(list(poly.values())).buffer(0.002)
    places = json.loads((GEO / "conn" / "towns.json").read_text())["elements"] + \
        json.loads((GEO / "conn" / "villages.json").read_text())["elements"]
    rank = {"city": 0, "town": 1, "village": 2, "hamlet": 3, "locality": 4}
    junctions = [(e["lon"], e["lat"]) for e in json.loads((GEO / "conn" / "junctions.json").read_text())["elements"]
                 if serbia.contains(Point(e["lon"], e["lat"]))]
    print(len(junctions), "motorway junctions in Serbia")

    rows = []
    for u in units():
        p = poly[u["slug"]]
        seat = BG_INNER.get(u["name"])
        if not seat:
            names = {key(u["name"]), key(cyr(u["name"]))}
            cand = [e for e in places
                    if (key(e["tags"].get("name:sr-Latn", "")) in names or e["tags"].get("name", "") == cyr(u["name"]))
                    and p.buffer(0.01).contains(Point(e["lon"], e["lat"]))]
            cand.sort(key=lambda e: rank.get(e["tags"].get("place"), 9))
            if cand:
                seat = (cand[0]["lon"], cand[0]["lat"])
        if not seat:
            c = p.representative_point()
            seat = (c.x, c.y)
            print("  polygon point for", u["name"])
        near_j = sorted(junctions, key=lambda j: hav(seat, j))[:5]
        dests = list(CENTERS.values()) + list(AIRPORTS.values()) + near_j
        dur = osrm(seat, dests)
        c_names, a_names = list(CENTERS), list(AIRPORTS)
        cd = dur[:4]
        ad = dur[4:7]
        jd = [d for d in dur[7:] if d is not None]
        ci = min(range(4), key=lambda i: cd[i])
        ai = min(range(3), key=lambda i: ad[i])
        rows.append([u["name"], round(seat[1], 5), round(seat[0], 5), c_names[ci], round(cd[ci] / 60),
                     round(min(jd) / 60) if jd else "", a_names[ai], round(ad[ai] / 60)])
        print(u["name"], rows[-1][3:])
        time.sleep(1.1)  # be gentle with the public demo server

    out = ROOT / "data" / "clean" / "povezanost.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["naziv", "lat", "lon", "centar", "min_centar", "min_autoput", "aerodrom", "min_aerodrom"])
        w.writerows(rows)
    print("wrote", out)


if __name__ == "__main__":
    main()
