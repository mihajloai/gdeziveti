#!/usr/bin/env python3
"""Download the newest RGZ "Statistika cena nepokretnosti" report (PDF) and extract
median flat prices (EUR/m2) for cities (Table 1) and Belgrade cadastral
municipalities (Table 2). Writes data/clean/cene_stanova.csv.

Requires `pdftotext` (poppler-utils)."""
import csv
import http.cookiejar
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from geo_units import units  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "rgz"
CLEAN = ROOT / "data" / "clean"
LIST_URL = "https://www.rgz.gov.rs/kvartalni-polugodi%C5%A1nji-i-godi%C5%A1nji-izve%C5%A1taji"
UA = "Mozilla/5.0 (compatible; gdeziveti-bot/1.0; +https://gdeziveti.rs)"
MIN_SALES = 30

CYR = dict(zip("АБВГДЂЕЖЗИЈКЛМНОПРСТЋУФХЦЧШ", ["A", "B", "V", "G", "D", "Đ", "E", "Ž", "Z", "I", "J", "K", "L", "M", "N", "O", "P", "R", "S", "T", "Ć", "U", "F", "H", "C", "Č", "Š"]))
CYR.update({"Љ": "Lj", "Њ": "Nj", "Џ": "Dž"})
# Belgrade cadastral municipality -> city municipality
BG_KO = {"Stara Rakovica": "Rakovica", "Palilula": "Palilula (Beograd)", "Stari Grad": "Stari grad",
         "Savski Venac": "Savski venac", "Novi Beograd": "Novi Beograd"}


def lat(s):
    s = "".join(CYR.get(ch, ch) for ch in s.upper())
    return " ".join(w.capitalize() for w in s.split())


_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return _OPENER.open(req, timeout=120).read()


def latest_report():
    html = get(LIST_URL).decode("utf-8", "ignore")
    links = [h for h in re.findall(r'href="([^"]+\.pdf)"', html) if "Статистика цена непокретности" in urllib.parse.unquote(h)]
    if not links:
        raise SystemExit("no 'Statistika cena' report found")

    def key(h):
        name = urllib.parse.unquote(h)
        year = int(re.search(r"20\d\d", name).group(0))
        half = 1 if "полугод" in name.lower() else 2  # annual report covers the full year
        return (year, half)

    best = max(links, key=key)
    name = urllib.parse.unquote(best).split("/")[-1]
    RAW.mkdir(parents=True, exist_ok=True)
    pdf = RAW / name
    pdf.write_bytes(get("https://www.rgz.gov.rs" + urllib.parse.quote(urllib.parse.unquote(best))))
    y, h = key(best)
    period = f"prvo polugodište {y}." if h == 1 else f"{y}. godina"
    return pdf, period


NUM = r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?|/"


def parse_table(lines):
    """Yield (name, median, average, count) from a table block."""
    rows, pending, last_from_numbers = [], "", False
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^([А-ЯЂЈЉЊЋЏ*][А-ЯЂЈЉЊЋЏ* ]*?)\s{2,}(" + NUM + r")\s+(" + NUM + r")\s+(-?" + NUM + r")\s+(" + NUM + r")", s)
        n = re.match(r"^(" + NUM + r")\s+(" + NUM + r")\s+(-?" + NUM + r")\s+(" + NUM + r")", s)
        if m:
            rows.append([m.group(1).strip(" *"), m.group(2), m.group(3), m.group(5)])
            pending, last_from_numbers = "", False
        elif n:
            rows.append([pending, n.group(1), n.group(2), n.group(4)])
            pending, last_from_numbers = "", True
        elif re.fullmatch(r"[А-ЯЂЈЉЊЋЏ ]+", s) and len(s) <= 25:
            if last_from_numbers and rows:
                rows[-1][0] = (rows[-1][0] + " " + s).strip()
                last_from_numbers = False
            else:
                pending = (pending + " " + s).strip()
        else:
            pending, last_from_numbers = "", False

    def f(x):
        return None if x == "/" else float(x.replace(".", "").replace(",", "."))

    return [(r[0], f(r[1]), f(r[2]), f(r[3])) for r in rows]


def main():
    pdf, period = latest_report()
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    lines = txt.splitlines()

    def block(title_start, title_end):
        idx = [i for i, ln in enumerate(lines) if title_start in ln]
        start = idx[-1]  # last occurrence = the table (first is the table of contents)
        end = next(i for i in range(start + 1, len(lines)) if title_end in lines[i])
        return lines[start:end]

    t1 = parse_table(block("Табела 1: Статистика цена станова у градовима", "Напомена"))
    t2 = parse_table(block("Табела 2: Статистика цена станова у катастарским", "Табела 3"))
    names = {u["name"] for u in units()}
    out = {}
    for name, med, avg, cnt in t1:
        n = lat(name)
        if n == "Beograd":
            continue
        if n in names and med and cnt and cnt >= MIN_SALES:
            out[n] = (med, int(cnt))
        elif n not in names:
            print("unmatched city:", name, n)
    for name, med, avg, cnt in t2:
        n = lat(name)
        n = BG_KO.get(n, n)
        if n in names and med and cnt and cnt >= MIN_SALES:
            out[n] = (med, int(cnt))
        elif n not in names:
            print("unmatched KO:", name, n)

    with (CLEAN / "cene_stanova.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["naziv", "cena_m2", "broj_prodaja"])
        for n, (med, cnt) in sorted(out.items()):
            w.writerow([n, int(med), cnt])
    meta_p = CLEAN / "meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    meta["cena_m2"] = {"period": period, "verified": True, "note": "medijana, stanovi, samo gradovi sa 30+ prodaja"}
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} units with flat prices ({period}) from {pdf.name}")


if __name__ == "__main__":
    main()
