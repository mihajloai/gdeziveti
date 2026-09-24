#!/usr/bin/env python3
"""NBS middle EUR/RSD rate (via kurs.resenje.org, a free mirror of NBS data)."""
import json
import urllib.request
from pathlib import Path

CLEAN = Path(__file__).resolve().parent.parent / "data" / "clean"
try:
    r = json.load(urllib.request.urlopen("https://kurs.resenje.org/api/v1/currencies/eur/rates/today", timeout=30))
    (CLEAN / "eur.json").write_text(json.dumps({"rate": r["exchange_middle"], "date": r["date"]}))
    print("EUR", r["exchange_middle"], r["date"])
except Exception as e:  # keep previous value if the service is down
    print("EUR rate not updated:", e)
