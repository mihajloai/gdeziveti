"""Static list of the 161 local units used on the site (145 cities/municipalities
outside Kosovo and Metohija, with the City of Belgrade split into its 17 city
municipalities). Each unit is mapped to its district (okrug) and statistical
region. Names follow the Statistical Office (RZS) Latin spelling."""

REGIONS = {
    "BG": "Beograd",
    "VO": "Vojvodina",
    "SZ": "Šumadija i Zapadna Srbija",
    "JI": "Južna i Istočna Srbija",
}

# district -> (region code, [units])
DISTRICTS = {
    "Grad Beograd": ("BG", ["Barajevo", "Voždovac", "Vračar", "Grocka", "Zvezdara", "Zemun",
                           "Lazarevac", "Mladenovac", "Novi Beograd", "Obrenovac",
                           "Palilula (Beograd)", "Rakovica", "Savski venac", "Sopot",
                           "Stari grad", "Surčin", "Čukarica"]),
    "Zapadnobački": ("VO", ["Sombor", "Apatin", "Kula", "Odžaci"]),
    "Južnobanatski": ("VO", ["Pančevo", "Alibunar", "Bela Crkva", "Vršac", "Kovačica", "Kovin",
                             "Opovo", "Plandište"]),
    "Južnobački": ("VO", ["Novi Sad", "Bač", "Bačka Palanka", "Bački Petrovac", "Beočin", "Bečej",
                          "Vrbas", "Žabalj", "Srbobran", "Sremski Karlovci", "Temerin", "Titel"]),
    "Severnobanatski": ("VO", ["Kikinda", "Ada", "Kanjiža", "Novi Kneževac", "Senta", "Čoka"]),
    "Severnobački": ("VO", ["Subotica", "Bačka Topola", "Mali Iđoš"]),
    "Srednjebanatski": ("VO", ["Zrenjanin", "Žitište", "Nova Crnja", "Novi Bečej", "Sečanj"]),
    "Sremski": ("VO", ["Sremska Mitrovica", "Inđija", "Irig", "Pećinci", "Ruma", "Stara Pazova", "Šid"]),
    "Zlatiborski": ("SZ", ["Užice", "Arilje", "Bajina Bašta", "Kosjerić", "Nova Varoš", "Požega",
                          "Priboj", "Prijepolje", "Sjenica", "Čajetina"]),
    "Kolubarski": ("SZ", ["Valjevo", "Lajkovac", "Ljig", "Mionica", "Osečina", "Ub"]),
    "Mačvanski": ("SZ", ["Šabac", "Bogatić", "Vladimirci", "Koceljeva", "Krupanj", "Loznica",
                        "Ljubovija", "Mali Zvornik"]),
    "Moravički": ("SZ", ["Čačak", "Gornji Milanovac", "Ivanjica", "Lučani"]),
    "Pomoravski": ("SZ", ["Jagodina", "Despotovac", "Paraćin", "Rekovac", "Svilajnac", "Ćuprija"]),
    "Rasinski": ("SZ", ["Kruševac", "Aleksandrovac", "Brus", "Varvarin", "Trstenik", "Ćićevac"]),
    "Raški": ("SZ", ["Kraljevo", "Vrnjačka Banja", "Novi Pazar", "Raška", "Tutin"]),
    "Šumadijski": ("SZ", ["Kragujevac", "Aranđelovac", "Batočina", "Knić", "Lapovo", "Rača", "Topola"]),
    "Borski": ("JI", ["Bor", "Kladovo", "Majdanpek", "Negotin"]),
    "Braničevski": ("JI", ["Požarevac", "Veliko Gradište", "Golubac", "Žabari", "Žagubica", "Kučevo",
                          "Malo Crniće", "Petrovac na Mlavi"]),
    "Zaječarski": ("JI", ["Zaječar", "Boljevac", "Knjaževac", "Sokobanja"]),
    "Jablanički": ("JI", ["Leskovac", "Bojnik", "Vlasotince", "Lebane", "Medveđa", "Crna Trava"]),
    "Nišavski": ("JI", ["Niš", "Aleksinac", "Gadžin Han", "Doljevac", "Merošina", "Ražanj", "Svrljig"]),
    "Pirotski": ("JI", ["Pirot", "Babušnica", "Bela Palanka", "Dimitrovgrad"]),
    "Podunavski": ("JI", ["Smederevo", "Velika Plana", "Smederevska Palanka"]),
    "Pčinjski": ("JI", ["Vranje", "Bosilegrad", "Bujanovac", "Vladičin Han", "Preševo", "Surdulica",
                       "Trgovište"]),
    "Toplički": ("JI", ["Prokuplje", "Blace", "Žitorađa", "Kuršumlija"]),
}

_LAT = {"č": "c", "ć": "c", "š": "s", "ž": "z", "đ": "dj", "Č": "c", "Ć": "c", "Š": "s", "Ž": "z", "Đ": "dj"}


def slugify(name: str) -> str:
    s = "".join(_LAT.get(ch, ch) for ch in name).lower()
    out = []
    for ch in s:
        out.append(ch if ch.isalnum() else "-")
    slug = "-".join(p for p in "".join(out).split("-") if p)
    return slug


def units():
    for district, (region, names) in DISTRICTS.items():
        for n in names:
            yield {"name": n, "slug": slugify(n), "district": district, "region": region}


if __name__ == "__main__":
    u = list(units())
    print(len(u), "units")
    assert len({x["slug"] for x in u}) == len(u)
