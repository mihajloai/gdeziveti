# Ručno održavani podaci

## vazduh.csv — kvalitet vazduha (ažurira se jednom godišnje, ručno)

Sajt Agencije za zaštitu životne sredine (sepa.gov.rs) nije dostupan automatskim alatima
(problem sa sertifikatom sajta), pa se ovaj fajl ažurira ručno kada SEPA objavi godišnji izveštaj.

- `kategorija`: `prekomerno` = vazduh ocenjen kao prekomerno zagađen u godišnjem izveštaju SEPA;
  `meri_se` = u opštini postoji merenje, a vazduh nije ocenjen kao prekomerno zagađen.
  Opštine kojih nema u fajlu nemaju merenja.
- `pm10_dani`: broj dana sa prekoračenjem dnevne granične vrednosti PM10 (50 µg/m³; dozvoljeno 35 dana godišnje),
  iz mesečnih izveštaja SEPA (sažetak: RERI, „Analiza stanja kvaliteta vazduha u Republici Srbiji za 2024. godinu“)
  i lokalnog monitoringa (Šabac, Pančevo).
- Godina podataka: **2024.** (promeni i `AIR_YEAR` u scripts/build.py kad ažuriraš fajl)
