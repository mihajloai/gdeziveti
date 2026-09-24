# Ručno održavani podaci

## vazduh.csv — kvalitet vazduha (ažurira se jednom godišnje, ručno)

Sajt Agencije za zaštitu životne sredine (sepa.gov.rs) nije dostupan automatskim alatima
(problem sa sertifikatom sajta), pa se ovaj fajl ažurira ručno kada SEPA objavi godišnji izveštaj.

- Izvor: **SEPA, „Godišnji izveštaj o stanju kvaliteta vazduha u Republici Srbiji 2024. godine“** (poglavlje „Оцена квалитета ваздуха“ i Zaključak).
- `kategorija`: `prekomerno` = vazduh III kategorije (prekomerno zagađen) po zvaničnoj oceni.
  Aglomeracije (Beograd, Novi Sad, Niš, Bor, Užice, Kosjerić, Smederevo, Pančevo) obuhvataju celu teritoriju grada/opštine,
  pa su npr. svih 17 beogradskih opština `prekomerno`.
  `meri_se` = u opštini postoji merno mesto (automatsko, manuelno ili indikativno), a vazduh nije ocenjen kao prekomerno zagađen.
  Opštine kojih nema u fajlu nemaju merenja.
- `pm10_dani`: broj dana sa PM10 > 50 µg/m³ (dozvoljeno 35 dana godišnje) na najgorem automatskom mernom mestu u opštini,
  iz Tabele 4 izveštaja. Indikativna merenja (Tabela 5) imaju premalo uzoraka, pa se ne koriste za broj dana.
- `merno_mesto`: stanica sa tim brojem dana; `napomena`: zbog čega je vazduh ocenjen kao prekomerno zagađen.
- Godina podataka: **2024.** (promeni i `AIR_YEAR` u scripts/build.py kad ažuriraš fajl)
