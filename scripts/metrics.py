"""Metric definitions shown on the site. Order inside a group = order in UI.

type: "num" (numeric, ranked) or "cat" (categories with levels)
better: "high" | "low" | "neutral"
diverging: red for negative, blue for positive values
"""

GROUPS = {
    "novac": "Novac i stan",
    "stanovnistvo": "Stanovništvo",
    "porodica": "Porodica",
    "sredina": "Životna sredina",
    "povezanost": "Povezanost",
    "bezbednost": "Bezbednost",
    "turizam": "Turizam",
}

METRICS = {
    # ---------------- novac i stan
    "neto": {
        "group": "novac", "label": "Prosečna neto plata", "short": "Plata", "unit": "RSD", "better": "high",
        "desc": "Prosečna mesečna neto zarada zaposlenih koji žive u toj opštini.",
        "source": "Republički zavod za statistiku",
    },
    "cena_m2": {
        "group": "novac", "label": "Cena kvadrata stana", "short": "Cena m²", "unit": "€/m²", "better": "low",
        "desc": "Srednja (medijalna) cena kvadrata iz stvarnih kupoprodajnih ugovora, ne iz oglasa. RGZ je objavljuje samo za gradove i beogradske opštine sa dovoljno prodaja.",
        "source": "Republički geodetski zavod",
    },
    "godine_stan": {
        "group": "novac", "label": "Godina rada za stan od 50 m²", "short": "Pristupačnost", "unit": "god.",
        "decimals": True, "better": "low",
        "desc": "Koliko godina celokupne prosečne neto plate je potrebno za stan od 50 m² u toj opštini.",
        "source": "izračunato iz podataka RZS i RGZ",
    },
    "nezaposlenost": {
        "group": "novac", "label": "Stopa registrovane nezaposlenosti", "short": "Nezaposlenost", "unit": "%",
        "decimals": True, "better": "low",
        "desc": "Broj lica na evidenciji NSZ u odnosu na stanovništvo radnog uzrasta (15–64).",
        "source": "Nacionalna služba za zapošljavanje / RZS",
    },
    # ---------------- stanovništvo
    "pop_promena": {
        "group": "stanovnistvo", "label": "Promena broja stanovnika 2011–2022", "short": "Rast stanovništva",
        "unit": "%", "decimals": True, "signed": True, "diverging": True, "better": "high",
        "desc": "Za koliko se promenio broj stanovnika između dva popisa (2011. i 2022).",
        "source": "Popis stanovništva, RZS", "census": True,
    },
    "prirastaj": {
        "group": "stanovnistvo", "label": "Prirodni priraštaj", "short": "Prirodni priraštaj", "unit": "‰",
        "decimals": True, "signed": True, "diverging": True, "better": "high",
        "desc": "Broj živorođenih minus broj umrlih na 1.000 stanovnika u toku godine.",
        "source": "Republički zavod za statistiku",
    },
    "starost": {
        "group": "stanovnistvo", "label": "Prosečna starost stanovnika", "short": "Prosečna starost", "unit": "god.",
        "decimals": True, "better": "low",
        "desc": "Prosečna starost svih stanovnika opštine (procena RZS).",
        "source": "Republički zavod za statistiku",
    },
    # ---------------- porodica
    "vrtici": {
        "group": "porodica", "label": "Deca koja nisu primljena u državni vrtić zbog nedostatka mesta",
        "short": "Mesta u vrtićima", "unit": "%", "decimals": True, "better": "low",
        "desc": "Udeo dece koja nisu primljena u javni vrtić zbog popunjenosti kapaciteta, u odnosu na svu decu koja su tražila mesto. Kada nema mesta, mnoge opštine sufinansiraju privatni vrtić, ali iznos i uslovi zavise od opštine i za to ne postoji zvanična statistika.",
        "source": "Republički zavod za statistiku",
    },
    # ---------------- životna sredina
    "voda": {
        "group": "sredina", "type": "cat", "label": "Ispravnost vode za piće iz gradskog vodovoda",
        "short": "Voda", "better": "high",
        "desc": "Ocena vode iz javnog vodovoda u sedištu opštine. Vodovod je neispravan ako je više od 20% uzoraka hemijski ili više od 5% mikrobiološki neispravno tokom godine. Ne odnosi se na seoske vodovode i bunare.",
        "source": "Institut za javno zdravlje „Batut“",
        "levels": [
            {"code": "ispravna", "label": "Ispravna", "color": "var(--st-good)", "score": 1.0},
            {"code": "hemijski", "label": "Hemijski neispravna", "color": "var(--st-warn)", "score": 0.35},
            {"code": "mikrobioloski", "label": "Mikrobiološki neispravna", "color": "var(--st-serious)", "score": 0.3},
            {"code": "oba", "label": "Hemijski i mikrobiološki neispravna", "color": "var(--st-critical)", "score": 0.0},
        ],
    },
    "vazduh": {
        "group": "sredina", "type": "cat", "label": "Kvalitet vazduha", "short": "Vazduh", "better": "high",
        "desc": "„Prekomerno zagađen“ je zvanična ocena Agencije za zaštitu životne sredine iz godišnjeg izveštaja. „Previše dana sa zagađenjem“ znači da je na mernom mestu više od 35 dana u godini (koliko zakon dozvoljava) bilo previše suspendovanih čestica PM10. Većina manjih opština nema mernu stanicu.",
        "source": "Agencija za zaštitu životne sredine (SEPA)",
        "levels": [
            {"code": "meri_se", "label": "U granicama", "color": "var(--st-good)", "score": 0.9},
            {"code": "cesto", "label": "Previše dana sa zagađenjem (PM10)", "color": "var(--st-serious)", "score": 0.4},
            {"code": "prekomerno", "label": "Prekomerno zagađen (ocena SEPA)", "color": "var(--st-critical)", "score": 0.0},
        ],
        "nodata_label": "nema merenja",
    },
    # ---------------- povezanost
    "povezanost": {
        "group": "povezanost", "label": "Povezanost (ocena 0–100)", "short": "Povezanost", "unit": "/100",
        "better": "high",
        "desc": "Ocena od 0 do 100 na osnovu vremena vožnje do najbližeg velikog poslovnog centra (Beograd, Novi Sad, Niš, Kragujevac) – 50%, do najbližeg uključenja na auto-put – 25% i do najbližeg međunarodnog aerodroma – 25%.",
        "source": "izračunato iz OpenStreetMap puteva (OSRM)",
    },
    # ---------------- bezbednost
    "kriminal": {
        "group": "bezbednost", "label": "Osuđeni za nasilna i imovinska krivična dela na 10.000 stanovnika",
        "short": "Kriminal", "unit": "", "decimals": True, "better": "low",
        "desc": "Pravnosnažno osuđena punoletna lica za krivična dela protiv života i tela i protiv imovine, prema mestu gde je delo izvršeno, na 10.000 stanovnika. Ovo je najbolji zvanični podatak po opštinama, ali nije isto što i broj zločina: centralne opštine (npr. Savski venac, Stari grad) imaju više dela jer tu dolazi mnogo ljudi, a sudski postupci kasne.",
        "source": "Republički zavod za statistiku (Opštine i regioni u Republici Srbiji)",
    },
    # ---------------- turizam
    "turizam": {
        "group": "turizam", "label": "Noćenja turista (poslednjih 12 meseci)", "short": "Noćenja turista",
        "unit": "", "better": "neutral",
        "desc": "Ukupan broj noćenja domaćih i stranih turista u poslednjih 12 meseci. Pokazuje koliko je mesto turističko – nije ni dobro ni loše samo po sebi.",
        "source": "Republički zavod za statistiku",
    },
}

QUIZ_WEIGHTS = {
    "neto": {"title": "Visoka plata", "hint": "Koliko je važno da se u mestu dobro zarađuje?", "good": "dobre plate"},
    "cena_m2": {"title": "Jeftin stan", "hint": "Niska cena kvadrata.", "good": "jeftini stanovi"},
    "godine_stan": {"title": "Pristupačan stan u odnosu na platu", "hint": "Za koliko plata se kupuje stan.", "good": "stan je pristupačan"},
    "nezaposlenost": {"title": "Lako do posla", "hint": "Niska nezaposlenost.", "good": "niska nezaposlenost"},
    "povezanost": {"title": "Dobra povezanost", "hint": "Blizu većeg grada, auto-puta i aerodroma.", "good": "dobro povezano"},
    "vazduh": {"title": "Čist vazduh", "hint": "Da vazduh nije prekomerno zagađen.", "good": "čist vazduh"},
    "voda": {"title": "Ispravna voda iz česme", "hint": "Ispravan gradski vodovod.", "good": "ispravna voda"},
    "vrtici": {"title": "Lako do mesta u vrtiću", "hint": "Za porodice sa malom decom.", "good": "ima mesta u vrtićima"},
    "starost": {"title": "Mlađa sredina", "hint": "Niža prosečna starost stanovnika.", "good": "mlađe stanovništvo"},
    "prirastaj": {"title": "Mesto koje živi", "hint": "Više rođenih nego umrlih.", "good": "dobar priraštaj"},
    "pop_promena": {"title": "Mesto koje raste", "hint": "Stanovništvo raste umesto da opada.", "good": "mesto raste"},
}
