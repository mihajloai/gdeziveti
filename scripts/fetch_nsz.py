#!/usr/bin/env python3
"""Newest National Employment Service (NSZ) monthly bulletin -> registered
unemployed per municipality. Rate = unemployed / population aged 15-64
(from data/clean/stanovnistvo.csv, produced by fetch_rzs.py).
Writes data/clean/nezaposlenost.csv (overrides the older RZS figure)."""
import csv
import html as htmlmod
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from geo_units import units  # noqa: E402
from fetch_rgz import lat  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "nsz"
CLEAN = ROOT / "data" / "clean"
LIST_URL = "https://www.nsz.gov.rs/sadrzaj/statisticki-bilteni-nsz/4111"
UA = "Mozilla/5.0 (compatible; gdeziveti-bot/1.0; +https://gdeziveti.rs)"
MONTHS = {"januar": 1, "februar": 2, "mart": 3, "april": 4, "maj": 5, "jun": 6, "jul": 7, "avgust": 8,
          "septembar": 9, "oktobar": 10, "novembar": 11, "decembar": 12}
ALIAS = {"Petrovac": "Petrovac na Mlavi", "Palilula": "Palilula (Beograd)", "Stari Grad": "Stari grad",
         "Savski Venac": "Savski venac", "Bela Palanka": "Bela Palanka"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180).read()


def latest_bulletin():
    page = get(LIST_URL).decode("utf-8", "ignore")
    best = None
    for href, text in re.findall(r'href="([^"]+\.pdf)"[^>]*>(.*?)</a>', page, re.S):
        t = lat(htmlmod.unescape(re.sub("<[^>]+>", "", text))).lower()
        m = re.search(r"(" + "|".join(MONTHS) + r")\s+(20\d\d)", t)
        if m:
            k = (int(m.group(2)), MONTHS[m.group(1)])
            if not best or k > best[0]:
                best = (k, href)
    if not best:
        raise SystemExit("no NSZ bulletin found")
    (y, mth), href = best
    RAW.mkdir(parents=True, exist_ok=True)
    pdf = RAW / f"bilten_{y}_{mth:02d}.pdf"
    pdf.write_bytes(get(href))
    name = [k for k, v in MONTHS.items() if v == mth][0]
    return pdf, f"{name} {y}."


def main():
    pdf, period = latest_bulletin()
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    lines = txt.splitlines()
    starts = [i for i, ln in enumerate(lines) if "DATA BY COUNTIES AND MUNICIPALITIES" in ln]
    if not starts:
        raise SystemExit("municipality table not found")
    block = lines[starts[0]: starts[-1] + 120]
    names = {u["name"] for u in units()}
    found = {}
    for ln in block:
        m = re.match(r"^([А-ЯЂЈЉЊЋЏ][А-Яа-яЂЈЉЊЋЏђјљњћџ .()\-]*?)\s{2,}(\d{1,3}(?:\.\d{3})*)\s+\d", ln)
        if not m:
            continue  # indented lines = regions, districts, or sub-municipalities of a city
        raw = m.group(1).strip()
        base = re.sub(r"\s*\(.*?\)", "", re.sub(r"\s*-\s*град$", "", raw)).strip()
        n = lat(base)
        n = ALIAS.get(n, n)
        # capitalisation: RZS uses "Novi Sad", "Bačka Palanka" etc.
        cand = [x for x in names if x.lower() == n.lower()]
        if cand and cand[0] not in found:
            found[cand[0]] = int(m.group(2).replace(".", ""))
    # ---- AP Kosovo i Metohija: NSZ records of the Kosovska Mitrovica branch (counts only) ----
    kim, district = [], None
    in_kim = False
    for ln in block:
        if "Регион Косово и Метохија" in ln:
            in_kim = True
            continue
        if not in_kim:
            continue
        if "Територијално" in ln or "Република Србија" in ln:
            break
        m = re.match(r"^(\s*)([А-ЯЂЈЉЊЋЏ][А-Яа-яЂЈЉЊЋЏђјљњћџ .()\-]*?)\s{2,}(\d{1,3}(?:\.\d{3})*)\s+(\d{1,3}(?:\.\d{3})*)", ln)
        if not m:
            continue
        name = re.sub(r"\s*-\s*град$", "", m.group(2).strip())
        name = re.sub(r"\s*-\s*", "-", name)
        cnt, women = int(m.group(3).replace(".", "")), int(m.group(4).replace(".", ""))
        if m.group(1):  # indented = district (okrug)
            district = lat(name).replace("-", "-")
        else:
            kim.append((district, lat(name), cnt, women))
    with (CLEAN / "kim_nsz.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["okrug", "opstina", "nezaposleni", "zene"])
        for row in kim:
            w.writerow(row)
    print("KiM municipalities:", len(kim))

    pop = {}
    with (CLEAN / "stanovnistvo.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["radni_uzrast"]:
                pop[r["naziv"]] = float(r["radni_uzrast"])
    missing = sorted(names - set(found))
    if len(found) < 150:
        raise SystemExit(f"only {len(found)} municipalities parsed, missing: {missing}")
    with (CLEAN / "nezaposlenost.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["naziv", "stopa", "broj"])
        for n, cnt in sorted(found.items()):
            if n in pop:
                w.writerow([n, round(cnt / pop[n] * 100, 1), cnt])
    meta_p = CLEAN / "meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    meta["nezaposlenost"] = {"period": period, "verified": True}
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"unemployment for {len(found)} units ({period}); missing: {missing}")


if __name__ == "__main__":
    main()
