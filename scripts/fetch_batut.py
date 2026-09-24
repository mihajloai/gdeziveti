#!/usr/bin/env python3
"""Newest Batut report "Zdravstvena ispravnost vode za piće" -> data/clean/voda.csv

The report lists every public water system of urban settlements in one of four tables:
  Table 8  – ispravni (compliant)
  Table 9  – only physico-chemical non-compliance (>20% of samples in the year)
  Table 10 – only microbiological non-compliance (>5% of samples)
  Table 11 – both ("udružena" neispravnost)
Only the system of the municipal seat is used (e.g. KOSTOLAC is skipped, POŽAREVAC counts).
The Belgrade system (BEOGRAD) is applied to Belgrade's inner-city municipalities."""
import csv
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch_rzs2 import c2l, meta_update  # noqa: E402
from geo_units import units  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "batut"
CLEAN = ROOT / "data" / "clean"
UA = "Mozilla/5.0 (compatible; gdeziveti-bot/1.0; +https://gdeziveti.rs)"
BASE = "https://www.batut.org.rs/download/izvestaji/"
PATTERNS = ["Zdravstvena ispravnost vode za pice {y}.pdf", "Izvestaj vode za pice {y}.pdf",
            "Zdravstvena ispravnost vode za pice {y}.PDF"]
BG_SYSTEM = ["Stari grad", "Vračar", "Savski venac", "Novi Beograd", "Zvezdara", "Palilula (Beograd)",
             "Voždovac", "Zemun", "Čukarica", "Rakovica", "Surčin"]
ALIAS = {"Soko Banja": "Sokobanja", "Bosiljgrad": "Bosilegrad"}
LOOKALIKE = str.maketrans("ABEKMHOPCTXYaeopcxy", "АВЕКМНОРСТХУаеорсху")
RANK = {"ispravna": 0, "hemijski": 1, "mikrobioloski": 1, "oba": 2}
TABLES = [("Табела 8.", "ispravna"), ("Табела 9.", "hemijski"), ("Табела 10.", "mikrobioloski"), ("Табела 11.", "oba")]


def find_report():
    for y in range(date.today().year, date.today().year - 7, -1):
        for pat in PATTERNS:
            url = BASE + urllib.parse.quote(pat.format(y=y))
            try:
                data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()
            except Exception:  # noqa: BLE001
                continue
            if data[:4] == b"%PDF":
                RAW.mkdir(parents=True, exist_ok=True)
                p = RAW / f"voda_{y}.pdf"
                p.write_bytes(data)
                return p, y
    raise SystemExit("no Batut water report found")


def main():
    pdf, year = find_report()
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    lines = txt.splitlines()
    starts = []
    for marker, cat in TABLES:
        idx = [i for i, ln in enumerate(lines) if ln.strip().startswith(marker)]
        if not idx:
            raise SystemExit(f"table {marker} not found")
        starts.append((idx[-1], cat))
    starts.sort()
    names = {u["name"].lower(): u["name"] for u in units()}
    result = {}
    for k, (start, cat) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else start + 200
        for ln in lines[start + 1:end]:
            m = re.match(r"^\s*(\d{1,3})\s+([A-Za-zА-Яа-яЂЈЉЊЋЏђјљњћџ .\-]+?)\*?\s{2,}(\d+[.,]?\d*)\*?(?:\s+(\d+[.,]?\d*))?\s*$", ln)
            if not m:
                continue
            raw = m.group(2).translate(LOOKALIKE).strip()
            n = " ".join(w.capitalize() for w in c2l(raw).split())
            n = ALIAS.get(n, n)
            vals = [float(v.replace(",", ".")) for v in (m.group(3), m.group(4)) if v]
            if cat == "ispravna" or cat == "oba":
                fh, mb = (vals + [None, None])[:2]
            elif cat == "hemijski":
                fh, mb = vals[0], None
            else:
                fh, mb = None, vals[0]
            targets = BG_SYSTEM if n == "Beograd" else [names[n.lower()]] if n.lower() in names else []
            for t in targets:
                prev = result.get(t)
                if not prev or RANK[cat] > RANK[prev[0]]:
                    result[t] = (cat, fh, mb)
    with (CLEAN / "voda.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["naziv", "kategorija", "fizicko_hemijska_pct", "mikrobioloska_pct"])
        for n, (cat, fh, mb) in sorted(result.items()):
            w.writerow([n, cat, "" if fh is None else fh, "" if mb is None else mb])
    meta_update({"voda": {"period": f"{year}. godina", "year": year, "verified": True}})
    print(f"water {year}: {len(result)} municipalities;",
          {c: sum(1 for v in result.values() if v[0] == c) for c in RANK})


if __name__ == "__main__":
    main()
