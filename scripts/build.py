#!/usr/bin/env python3
"""Build the static site into dist/.

Inputs (all optional except the unit list):
  data/clean/zarade.csv          naziv,neto
  data/clean/cene_stanova.csv    naziv,cena_m2
  data/clean/nezaposlenost.csv   naziv,stopa
  data/clean/stanovnistvo.csv    naziv,pop2011,pop2022
  data/clean/meta.json           {metric: {period, verified}}
  data/geo/opstine.geojson       municipality polygons (property 'slug' after prepare_geo.py)

Usage:  python3 scripts/build.py [--base /repo-name/]
"""
import csv
import json
import math
import os
import shutil
import statistics
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, str(Path(__file__).parent))
from geo_units import REGIONS, units  # noqa: E402
from metrics import GROUPS, METRICS, QUIZ_WEIGHTS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
DIST = ROOT / "dist"
EUR_RSD = 117.2  # NBS middle rate; overwritten by data/clean/eur.json if present


def read_csv(name):
    p = CLEAN / name
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as f:
        return {r["naziv"].strip(): r for r in csv.DictReader(f)}


def num(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


AIR_YEAR = 2024  # year of data/manual/vazduh.csv (updated by hand, see data/manual/README.md)


def conn_score(c, h, a):
    """0-100: nearest business centre (50%), motorway (25%), airport (25%)."""
    def part(minutes, zero_at):
        return max(0.0, 1 - minutes / zero_at) * 100
    return round(0.5 * part(c, 150) + 0.25 * part(h, 90) + 0.25 * part(a, 180))


def period_year(txt):
    import re
    ys = [int(y) for y in re.findall(r"(20\d\d)", txt or "")]
    return max(ys) if ys else None


def build_dataset():
    global EUR_RSD
    meta = json.loads((CLEAN / "meta.json").read_text()) if (CLEAN / "meta.json").exists() else {}
    if (CLEAN / "eur.json").exists():
        EUR_RSD = json.loads((CLEAN / "eur.json").read_text())["rate"]
    R = {n: read_csv(f) for n, f in {
        "wages": "zarade.csv", "prices": "cene_stanova.csv", "unemp": "nezaposlenost.csv", "pop": "stanovnistvo.csv",
        "age": "starost.csv", "nat": "prirastaj.csv", "kg": "vrtici.csv", "tour": "turizam.csv", "crime": "kriminal.csv",
        "water": "voda.csv", "conn": "povezanost.csv"}.items()}
    air_p = ROOT / "data" / "manual" / "vazduh.csv"
    air = {}
    if air_p.exists():
        with air_p.open(encoding="utf-8") as f:
            air = {r["naziv"]: r for r in csv.DictReader(f)}
    meta.setdefault("vazduh", {"period": f"{AIR_YEAR}. godina", "year": AIR_YEAR, "verified": True})

    out = []
    for u in units():
        n = u["name"]
        g = lambda key, col: num(R[key].get(n, {}).get(col))  # noqa: E731
        v, c, d = {}, {}, {}
        v["neto"] = g("wages", "neto")
        v["cena_m2"] = g("prices", "cena_m2")
        v["nezaposlenost"] = g("unemp", "stopa")
        p11, p22 = g("pop", "pop2011"), g("pop", "pop2022")
        # 2011 census was boycotted by most of the Albanian population in these three municipalities,
        # so the 2011 figure is not comparable (RZS note).
        comparable = n not in ("Preševo", "Bujanovac", "Medveđa")
        v["pop_promena"] = round((p22 / p11 - 1) * 100, 1) if p11 and p22 and comparable else None
        v["godine_stan"] = round(50 * v["cena_m2"] * EUR_RSD / (v["neto"] * 12), 1) if v["neto"] and v["cena_m2"] else None
        v["starost"] = g("age", "prosecna_starost")
        v["prirastaj"] = g("nat", "prirastaj_na_1000")
        if n in R["nat"]:
            d["prirastaj"] = {"rodjeni": g("nat", "rodjeni_na_1000"), "umrli": g("nat", "umrli_na_1000")}
        v["vrtici"] = g("kg", "odbijeni_pct")
        if n in R["kg"]:
            d["vrtici"] = {"nisu_primljeni": g("kg", "nisu_primljeni"), "upisani": g("kg", "upisani"),
                           "privatni_pct": g("kg", "privatni_pct")}
        v["turizam"] = g("tour", "nocenja_12m")
        if n in R["tour"]:
            d["turizam"] = {"po_stanovniku": g("tour", "nocenja_po_stanovniku")}
        v["kriminal"] = g("crime", "nasilni_imovinski_na_10000")
        if n in R["crime"]:
            d["kriminal"] = {"ukupno": g("crime", "osudjeni_ukupno"), "zivot": g("crime", "protiv_zivota_i_tela"),
                             "imovina": g("crime", "protiv_imovine")}
        if n in R["conn"]:
            mc, mh, ma = g("conn", "min_centar"), g("conn", "min_autoput"), g("conn", "min_aerodrom")
            v["povezanost"] = conn_score(mc, mh, ma)
            d["povezanost"] = {"centar": R["conn"][n]["centar"], "min_centar": mc, "min_autoput": mh,
                               "aerodrom": R["conn"][n]["aerodrom"], "min_aerodrom": ma}
        else:
            v["povezanost"] = None
        if n in R["water"]:
            c["voda"] = R["water"][n]["kategorija"]
            d["voda"] = {"fh": num(R["water"][n]["fizicko_hemijska_pct"]), "mb": num(R["water"][n]["mikrobioloska_pct"])}
        if n in air:
            cat = air[n]["kategorija"]
            if cat == "meri_se" and (num(air[n]["pm10_dani"]) or 0) > 35:
                cat = "cesto"
            c["vazduh"] = cat
            d["vazduh"] = {"pm10_dani": num(air[n]["pm10_dani"]), "mesto": air[n]["merno_mesto"], "napomena": air[n]["napomena"]}
        out.append({**u, "population": int(p22) if p22 else None, "v": v, "c": c, "d": d})

    def has(k):
        if METRICS[k].get("type") == "cat":
            return any(k in x["c"] for x in out)
        return any(x["v"].get(k) is not None for x in out)

    active = [k for k in METRICS if has(k)]
    serbia = {}
    for k in METRICS:
        vals = [x["v"].get(k) for x in out if x["v"].get(k) is not None]
        serbia[k] = round(statistics.median(vals), 1) if vals else None

    this_year = date.today().year
    metrics = {}
    for k, m in METRICS.items():
        mm = dict(m)
        mm.setdefault("type", "num")
        mm["period"] = meta.get(k, {}).get("period", "")
        if k == "godine_stan":
            mm["period"] = " / ".join(filter(None, [meta.get("neto", {}).get("period"), meta.get("cena_m2", {}).get("period")]))
        if k == "povezanost":
            mm["period"] = "putna mreža 2026."
        mm["year"] = meta.get(k, {}).get("year") or period_year(mm["period"])
        mm["verified"] = meta.get(k, {}).get("verified", True)
        age = this_year - mm["year"] if mm.get("year") else 0
        if m.get("census"):
            mm["freshness"] = "Najnoviji dostupni podaci – popis se sprovodi jednom u 10 godina."
            mm["stale"] = False
        elif age >= 3:
            mm["freshness"] = f"Najnoviji podaci koje je izvor objavio, ali su stari {age} godine – noviji još nisu objavljeni."
            mm["stale"] = True
        else:
            mm["freshness"] = "Najnoviji dostupni podaci."
            mm["stale"] = False
        metrics[k] = mm

    return {
        "updated": date.today().isoformat(),
        "eur_rate": EUR_RSD,
        "order": active,
        "groups": GROUPS,
        "metrics": metrics,
        "regions": REGIONS,
        "serbia": serbia,
        "serbiaLabel": "medijana Srbije",
        "quizWeights": {k: v for k, v in QUIZ_WEIGHTS.items() if k in active},
        "units": out,
    }


# ---------------------------------------------------------------- map
def load_map():
    p = ROOT / "data" / "geo" / "opstine.geojson"
    if not p.exists():
        return None
    gj = json.loads(p.read_text())
    # equirectangular with cos(lat) correction, fit to 600px width
    lat0 = math.radians(44.0)
    pts = []

    def rings(geom):
        if geom["type"] == "Polygon":
            return [geom["coordinates"]]
        return geom["coordinates"]

    for f in gj["features"]:
        for poly in rings(f["geometry"]):
            for ring in poly:
                pts.extend(ring)
    xs = [x * math.cos(lat0) for x, _ in pts]
    ys = [-y for _, y in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W = 600.0
    s = W / (maxx - minx)
    H = (maxy - miny) * s

    def proj(x, y):
        return ((x * math.cos(lat0) - minx) * s, (-y - miny) * s)

    paths = []
    for f in gj["features"]:
        d = []
        for poly in rings(f["geometry"]):
            for ring in poly:
                seg = []
                for i, (x, y) in enumerate(ring):
                    px, py = proj(x, y)
                    seg.append(("M" if i == 0 else "L") + f"{px:.1f},{py:.1f}")
                d.append("".join(seg) + "Z")
        props = f["properties"]
        paths.append({"slug": props.get("slug") or "", "name": props.get("name", ""), "d": "".join(d)})
    return {"w": round(W), "h": round(H), "paths": paths}


# ---------------------------------------------------------------- pages
def similar_units(data, u, n=6):
    core = ["neto", "cena_m2", "nezaposlenost", "starost", "prirastaj", "povezanost"]
    keys = [k for k in core if k in data["order"] and u["v"].get(k) is not None]
    if not keys:
        return []
    spreads = {}
    for k in keys:
        vals = [x["v"][k] for x in data["units"] if x["v"].get(k) is not None]
        spreads[k] = statistics.pstdev(vals) or 1
    scored = []
    for x in data["units"]:
        if x["slug"] == u["slug"]:
            continue
        dist, cnt = 0.0, 0
        for k in keys:
            if x["v"].get(k) is None:
                continue
            dist += ((x["v"][k] - u["v"][k]) / spreads[k]) ** 2
            cnt += 1
        if cnt:
            scored.append((dist / cnt, x))
    scored.sort(key=lambda t: t[0])
    return [x for _, x in scored[:n]]


def ranks(data):
    r = {}
    for k in data["order"]:
        m = data["metrics"][k]
        if m["type"] == "cat":
            continue
        vals = [x for x in data["units"] if x["v"].get(k) is not None]
        vals.sort(key=lambda x: x["v"][k], reverse=(m["better"] != "low"))
        r[k] = {}
        for i, x in enumerate(vals):
            r[k][x["slug"]] = r[k][vals[i - 1]["slug"]] if i and vals[i - 1]["v"][k] == x["v"][k] else i + 1
        r[k]["_n"] = len(vals)
    return r


def fmt_num(v, m=None):
    if v is None:
        return "—"
    dec = m and m.get("decimals")
    s = f"{v:,.1f}" if dec else f"{v:,.0f}"
    s = s.replace(",", "#").replace(".", ",").replace("#", ".")
    if m and m.get("signed") and v > 0:
        s = "+" + s
    if m and m.get("unit"):
        s += ("" if m["unit"].startswith("/") else "\u00a0") + m["unit"]
    return s


def fmt_plain(v, dec=False):
    return fmt_num(v, {"decimals": dec}) if v is not None else "—"


def detail_text(k, u):
    d = (u.get("d") or {}).get(k)
    if not d:
        return ""
    f = fmt_plain
    if k == "povezanost":
        return (f"{f(d['min_centar'])} min do: {d['centar']} · {f(d['min_autoput'])} min do auto-puta · "
                f"{f(d['min_aerodrom'])} min do: {d['aerodrom']}")
    if k == "vazduh":
        t = (f"{f(d['pm10_dani'])} dana sa previše PM10 čestica (dozvoljeno 35)" + (f", merno mesto {d['mesto']}" if d["mesto"] else "")
             ) if d.get("pm10_dani") is not None else "merenja postoje"
        return t + (f" · {d['napomena']}" if d.get("napomena") else "")
    if k == "voda":
        parts = []
        if d.get("fh") is not None:
            parts.append(f"hemijski neispravnih uzoraka {f(d['fh'], True)}%")
        if d.get("mb") is not None:
            parts.append(f"mikrobiološki {f(d['mb'], True)}%")
        return " · ".join(parts)
    if k == "vrtici":
        return (f"{f(d['nisu_primljeni'])} dece nije primljeno, {f(d['upisani'])} upisano · "
                f"u privatnim vrtićima: {f(d['privatni_pct'], True)}%")
    if k == "kriminal":
        return f"{f(d['zivot'])} protiv života i tela, {f(d['imovina'])} protiv imovine (ukupno osuđenih: {f(d['ukupno'])})"
    if k == "prirastaj":
        return f"rođeno {f(d['rodjeni'], True)}, umrlo {f(d['umrli'], True)} na 1.000 stanovnika"
    if k == "turizam" and d.get("po_stanovniku") is not None:
        return f"{f(d['po_stanovniku'], True)} noćenja po stanovniku"
    return ""


def level_of(m, code):
    return next((lv for lv in m.get("levels", []) if lv["code"] == code), None)


def main():
    base = "/"
    relative = "--relative" in sys.argv
    ix = "index.html" if "--explicit-index" in sys.argv else ""
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
        if not base.endswith("/"):
            base += "/"
    data = build_dataset()
    mp = load_map()

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "src" / "assets", DIST / "assets")
    (DIST / "assets" / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

    env = Environment(loader=FileSystemLoader(ROOT / "src" / "templates"), autoescape=select_autoescape(["html"]))
    env.filters["n"] = fmt_num
    env.globals["detail"] = detail_text
    env.globals["level_of"] = level_of
    # cache-busting: a new version of app.js/app.css gets a new URL, so phones never mix old and new files
    import hashlib
    env.globals["data_v"] = hashlib.md5((DIST / "assets" / "data.json").read_bytes()).hexdigest()[:8]
    env.globals["asset_v"] = hashlib.md5(b"".join((ROOT / "src" / "assets" / f).read_bytes() for f in ("app.js", "app.css"))).hexdigest()[:8]
    rk = ranks(data)
    ctx = {"ix": ix, "base": base, "data": data, "map": mp, "regions": REGIONS, "metrics": data["metrics"], "ranks": rk,
           "unverified": [k for k in data["order"] if not data["metrics"][k].get("verified", True)]}

    def write(path, tpl, **kw):
        out = DIST / path
        out.parent.mkdir(parents=True, exist_ok=True)
        c = dict(ctx)
        if relative:
            c["base"] = "../" * path.count("/") or "./"
        c.update(kw)
        out.write_text(env.get_template(tpl).render(**c), encoding="utf-8")

    write("index.html", "home.html", page="home")
    write("uporedi/index.html", "compare.html", page="compare")
    write("kviz/index.html", "quiz.html", page="quiz")
    write("o-podacima/index.html", "about.html", page="about")
    for u in data["units"]:
        write(f"opstina/{u['slug']}/index.html", "unit.html", page="unit", u=u, similar=similar_units(data, u))
    kim = []
    if (CLEAN / "kim_nsz.csv").exists():
        with (CLEAN / "kim_nsz.csv").open(encoding="utf-8") as f:
            kim = [dict(r, nezaposleni=int(r["nezaposleni"]), zene=int(r["zene"])) for r in csv.DictReader(f)]
    meta = json.loads((CLEAN / "meta.json").read_text()) if (CLEAN / "meta.json").exists() else {}
    write("kosovo-i-metohija/index.html", "kim.html", page="kim", kim=kim,
          kim_period=meta.get("nezaposlenost", {}).get("period", ""), kim_total=sum(r["nezaposleni"] for r in kim))
    write("404.html", "404.html", page="404")

    # sitemap
    site = os.environ.get("SITE_URL", "").rstrip("/")
    if site:
        urls = ["", "uporedi/", "kviz/", "o-podacima/", "kosovo-i-metohija/"] + [f"opstina/{u['slug']}/" for u in data["units"]]
        (DIST / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f"<url><loc>{site}{base}{p}</loc></url>" for p in urls) + "</urlset>")
        (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site}{base}sitemap.xml\n")
    (DIST / ".nojekyll").write_text("")
    print(f"built {len(data['units'])} unit pages, metrics: {data['order']}, map: {'yes' if mp else 'no'}")


if __name__ == "__main__":
    main()
