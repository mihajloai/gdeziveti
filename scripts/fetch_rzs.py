#!/usr/bin/env python3
"""Download municipal statistics from the RZS open-data service and write
clean CSVs into data/clean/.

  zarade.csv        12-month average net wage by municipality of residence
  stanovnistvo.csv  census population 2011 & 2022, estimate for latest year, 15-64 population
  nezaposlenost.csv registered unemployed (latest month) / population 15-64
"""
import csv
import io
import json
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from geo_units import units  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
BASE = "https://opendata.stat.gov.rs/data/WcfJsonRestService.Service1.svc/dataset/{}/2/csv"
UA = "Mozilla/5.0 (compatible; gdeziveti-bot/1.0; +https://gdeziveti.rs)"

# Units whose RZS figure is published for the whole city (which contains several city municipalities)
CITY_IDS = {"Novi Sad": "89010", "Niš": "79022", "Požarevac": "79049", "Vranje": "79057", "Užice": "79065"}
MONTHS = ["januar", "februar", "mart", "april", "maj", "jun", "jul", "avgust", "septembar", "oktobar", "novembar", "decembar"]


def download(ds):
    RAW.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            req = urllib.request.Request(BASE.format(ds), headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=300).read()
            break
        except Exception as e:  # noqa: BLE001
            print("retry", ds, e)
            time.sleep(5)
    else:
        raise SystemExit(f"could not download {ds}")
    if data[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(data))
        data = z.read(z.namelist()[0])
    text = data.decode("utf-8-sig")
    (RAW / f"{ds}.csv").write_text(text, encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def lower_keys(rows):
    return [{k.lower(): v for k, v in r.items()} for r in rows]


def id_map(rows):
    """name -> territory id, using the names RZS uses."""
    names = {}
    for r in rows:
        names.setdefault(r["nter"].strip(), r["idter"])
    out = {}
    for u in units():
        n = u["name"]
        if n in CITY_IDS:
            out[n] = CITY_IDS[n]
        elif n in names:
            out[n] = names[n]
        else:
            print("WARNING: no RZS id for", n)
    return out


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    meta = json.loads((CLEAN / "meta.json").read_text()) if (CLEAN / "meta.json").exists() else {}

    # ---- wages (by municipality of residence) ----
    w = lower_keys(download("2403040103IND01"))
    ids = id_map(w)
    periods = sorted({(r["god"], r["mes"]) for r in w})
    last12 = periods[-12:]
    byter = defaultdict(dict)
    for r in w:
        if r["vrednost"]:
            byter[r["idter"]][(r["god"], r["mes"])] = float(r["vrednost"])
    with (CLEAN / "zarade.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["naziv", "neto", "neto_poslednji_mesec"])
        for n, i in ids.items():
            vals = [byter[i][p] for p in last12 if p in byter[i]]
            if len(vals) >= 10:
                wr.writerow([n, round(sum(vals) / len(vals)), round(byter[i].get(last12[-1], 0)) or ""])
    (g0, m0), (g1, m1) = last12[0], last12[-1]
    meta["neto"] = {"period": f"prosek {MONTHS[int(m0)-1]} {g0} – {MONTHS[int(m1)-1]} {g1}.", "verified": True,
                    "note": "prema opštini prebivališta zaposlenih"}
    rs = [byter["RS"][p] for p in last12 if p in byter["RS"]]
    meta["neto"]["serbia"] = round(sum(rs) / len(rs)) if rs else None

    # ---- population: census 2011/2022 ----
    g = lower_keys(download("02IND01G01"))
    census = defaultdict(dict)
    for r in g:
        if r["idindikator"] == "IND01G1001" and r["vrednost"]:
            census[r["idter"]][r["god"]] = float(r["vrednost"])

    # ---- population by age (estimates) ----
    a = lower_keys(download("18030302IND01"))
    last_year = max(r["god"] for r in a)
    work_age = defaultdict(float)
    total = {}
    wa_groups = {"15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64"}
    for r in a:
        if r["god"] != last_year or r["idpol"] != "0":
            continue
        if not r["vrednost"]:
            continue
        if r["idstargrupa"] in wa_groups:
            work_age[r["idter"]] += float(r["vrednost"])
        elif r["idstargrupa"] == "0":
            total[r["idter"]] = float(r["vrednost"])
    with (CLEAN / "stanovnistvo.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["naziv", "pop2011", "pop2022", "pop_procena", "radni_uzrast"])
        for n, i in ids.items():
            c = census.get(i, {})
            wr.writerow([n, int(c.get("2011", 0)) or "", int(c.get("2022", 0)) or "",
                         int(total.get(i, 0)) or "", int(work_age.get(i, 0)) or ""])
    meta["pop_promena"] = {"period": "popisi 2011. i 2022.", "verified": True}
    meta["population"] = {"period": f"procena {last_year}.", "verified": True}

    # ---- registered unemployment ----
    m = lower_keys(download("01IND01M01"))
    un = [r for r in m if r["idindikator"] == "IND03M03"]
    up = max((r["god"], r["mes"]) for r in un)
    unemp = {r["idter"]: float(r["vrednost"]) for r in un if (r["god"], r["mes"]) == up and r["vrednost"]}
    with (CLEAN / "nezaposlenost.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["naziv", "stopa", "broj"])
        for n, i in ids.items():
            if i in unemp and work_age.get(i):
                wr.writerow([n, round(unemp[i] / work_age[i] * 100, 1), int(unemp[i])])
    meta["nezaposlenost"] = {"period": f"{MONTHS[int(up[1])-1]} {up[0]}.", "verified": True}

    (CLEAN / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wages", last12[0], "->", last12[-1], "| unemployment", up, "| age", last_year)


if __name__ == "__main__":
    main()
