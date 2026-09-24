# Gde živeti — gdeziveti.rs

Besplatan sajt koji poredi svih 161 gradova i opština u Srbiji (Beograd po gradskim opštinama):
plate, cene stanova, pristupačnost stana, nezaposlenost i promena broja stanovnika.

- **Mapa** sa rang listom
- **Uporedi**: 2–3 mesta jedno pored drugog (link se može deliti)
- **Kviz „Gde da živim?“**: top 10 mesta prema prioritetima korisnika
- **Stranica za svaku opštinu** (dobro za Google pretragu)
- Latinica / ćirilica

## Kako radi (bez održavanja)

Sajt je statičan (samo HTML, CSS i JavaScript) i hostuje se besplatno na **Cloudflare Pages**
(build komanda: `python3 scripts/build.py`, izlazni folder: `dist`).
Jednom mesečno (12. u mesecu) GitHub Actions sam:

1. preuzme nove podatke (`scripts/fetch_*.py`),
2. sačuva ih u `data/clean/`,
3. proveri da se sajt pravi bez greške, a Cloudflare Pages zatim sam objavi novu verziju.

Ako neki izvor ne radi, zadržavaju se prethodni podaci, a sajt i dalje radi.
Ručno pokretanje: na GitHubu **Actions → Ažuriranje podataka i objava sajta → Run workflow**.

## Izvori podataka

| Podatak | Izvor | Skripta |
|---|---|---|
| Neto plata (prema opštini prebivališta, prosek 12 meseci) | RZS, otvoreni podaci | `fetch_rzs.py` |
| Stanovništvo (popisi 2011/2022, procena po starosti) | RZS | `fetch_rzs.py` |
| Registrovani nezaposleni | NSZ, mesečni statistički bilten | `fetch_nsz.py` |
| Cena kvadrata stana (medijana, stvarne kupoprodaje) | RGZ, „Statistika cena nepokretnosti“ | `fetch_rgz.py` |
| Kurs evra | NBS (preko kurs.resenje.org) | `fetch_eur.py` |
| Prosečna starost, prirodni priraštaj, vrtići, noćenja turista | RZS, otvoreni podaci | `fetch_rzs2.py` |
| Osuđeni za nasilna i imovinska krivična dela | RZS, „Opštine i regioni u Republici Srbiji“ (Excel) | `fetch_rzs2.py` |
| Ispravnost vode za piće | Institut „Batut“, godišnji izveštaj (PDF) | `fetch_batut.py` |
| Kvalitet vazduha | SEPA godišnji izveštaj — **ručno**, vidi `data/manual/README.md` | `data/manual/vazduh.csv` |
| Povezanost (vreme vožnje) | OpenStreetMap + OSRM, jednokratno | `prepare_connectivity.py` |
| Granice opština | geoBoundaries / OpenStreetMap (ODbL) | `prepare_geo.py` (jednokratno) |

## Lokalno pokretanje (opciono)

```bash
pip install jinja2
python3 scripts/build.py          # napravi sajt u dist/
python3 -m http.server -d dist    # otvori http://localhost:8000
```

## Domen

Domen se povezuje u Cloudflare-u: Workers & Pages → gdeziveti → Custom domains.
Za mapu sajta (sitemap) u Cloudflare podešavanjima dodaj promenljivu `SITE_URL = https://gdeziveti.rs`.
