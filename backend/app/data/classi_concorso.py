"""
Database classi di concorso italiane.
Fonte: DPR 19/2016
"""

# Formato: codice_ufficiale -> (codice_sidi, grado, denominazione)
CLASSI_CONCORSO = {
    # I GRADO
    "A-01": ("A001", "I GRADO", "ARTE E IMMAGINE NELLA SCUOLA SECONDARIA DI I GRADO"),
    "A-49": ("A049", "I GRADO", "SCIENZE MOTORIE E SPORTIVE NELLA SCUOLA SECONDARIA DI I GRADO"),
    "A-30": ("A030", "I GRADO", "MUSICA NELLA SCUOLA SECONDARIA DI I GRADO"),
    "A-60": ("A060", "I GRADO", "TECNOLOGIA NELLA SCUOLA SECONDARIA DI I GRADO"),
    "A-22": ("A022", "I GRADO", "ITALIANO, STORIA, GEOGRAFIA NELLA SCUOLA SECONDARIA DI I GRADO"),
    "A-28": ("A028", "I GRADO", "MATEMATICA E SCIENZE"),
    "A-56": ("A056", "I GRADO", "STRUMENTO MUSICALE NELLA SCUOLA SECONDARIA DI I GRADO"),
    "A-23": ("A023", "I GRADO", "LINGUA ITALIANA PER DISCENTI DI LINGUA STRANIERA (ALLOGLOTTI)"),

    # I GRADO - Lingue
    "AA25": ("AA25", "I GRADO", "LINGUA INGLESE E SECONDA LINGUA COMUNITARIA (FRANCESE)"),
    "AB25": ("AB25", "I GRADO", "LINGUA INGLESE E SECONDA LINGUA COMUNITARIA (INGLESE)"),
    "AC25": ("AC25", "I GRADO", "LINGUA INGLESE E SECONDA LINGUA COMUNITARIA (SPAGNOLO)"),
    "AD25": ("AD25", "I GRADO", "LINGUA INGLESE E SECONDA LINGUA COMUNITARIA (TEDESCO)"),

    # I GRADO - Strumenti
    "AA56": ("AA56", "I GRADO", "STRUMENTO MUSICALE (ARPA)"),
    "AB56": ("AB56", "I GRADO", "STRUMENTO MUSICALE (CHITARRA)"),
    "AC56": ("AC56", "I GRADO", "STRUMENTO MUSICALE (CLARINETTO)"),
    "AD56": ("AD56", "I GRADO", "STRUMENTO MUSICALE (CORNO)"),
    "AG56": ("AG56", "I GRADO", "STRUMENTO MUSICALE (FLAUTO)"),
    "AJ56": ("AJ56", "I GRADO", "STRUMENTO MUSICALE (PIANOFORTE)"),
    "AL56": ("AL56", "I GRADO", "STRUMENTO MUSICALE (TROMBA)"),
    "AM56": ("AM56", "I GRADO", "STRUMENTO MUSICALE (VIOLINO)"),

    # II GRADO - Materie principali
    "A-02": ("A002", "II GRADO", "DESIGN DEI METALLI, OREFICERIA, PIETRE DURE E GEMME"),
    "A-03": ("A003", "II GRADO", "DESIGN DELLA CERAMICA"),
    "A-04": ("A004", "II GRADO", "DESIGN DEL LIBRO"),
    "A-05": ("A005", "II GRADO", "DESIGN DEL TESSUTO E DELLA MODA"),
    "A-06": ("A006", "II GRADO", "DESIGN DEL VETRO"),
    "A-07": ("A007", "II GRADO", "DISCIPLINE AUDIOVISIVE"),
    "A-08": ("A008", "II GRADO", "DISCIPLINE GEOMETRICHE, ARCHITETTURA, DESIGN"),
    "A-09": ("A009", "II GRADO", "DISCIPLINE GRAFICHE, PITTORICHE E SCENOGRAFICHE"),
    "A-10": ("A010", "II GRADO", "DISCIPLINE GRAFICO-PUBBLICITARIE"),
    "A-11": ("A011", "II GRADO", "DISCIPLINE LETTERARIE E LATINO"),
    "A-12": ("A012", "II GRADO", "DISCIPLINE LETTERARIE ISTITUTI II GRADO"),
    "A-13": ("A013", "II GRADO", "DISCIPLINE LETTERARIE, LATINO E GRECO"),
    "A-14": ("A014", "II GRADO", "DISCIPLINE PLASTICHE, SCULTOREE E SCENOPLASTICHE"),
    "A-15": ("A015", "II GRADO", "DISCIPLINE SANITARIE"),
    "A-16": ("A016", "II GRADO", "DISEGNO ARTISTICO E MODELLAZIONE ODONTOTECNICA"),
    "A-17": ("A017", "II GRADO", "DISEGNO E STORIA DELL'ARTE"),
    "A-18": ("A018", "II GRADO", "FILOSOFIA E SCIENZE UMANE"),
    "A-19": ("A019", "II GRADO", "FILOSOFIA E STORIA"),
    "A-20": ("A020", "II GRADO", "FISICA"),
    "A-21": ("A021", "II GRADO", "GEOGRAFIA"),
    "A-26": ("A026", "II GRADO", "MATEMATICA"),
    "A-27": ("A027", "II GRADO", "MATEMATICA E FISICA"),
    "A-29": ("A029", "II GRADO", "MUSICA ISTITUTI II GRADO"),
    "A-31": ("A031", "II GRADO", "SCIENZE DEGLI ALIMENTI"),
    "A-32": ("A032", "II GRADO", "SCIENZE DELLA GEOLOGIA E DELLA MINERALOGIA"),
    "A-33": ("A033", "II GRADO", "SCIENZE E TECNOLOGIE AERONAUTICHE"),
    "A-34": ("A034", "II GRADO", "SCIENZE E TECNOLOGIE CHIMICHE"),
    "A-37": ("A037", "II GRADO", "SCIENZE E TECNOLOGIE DELLE COSTRUZIONI"),
    "A-38": ("A038", "II GRADO", "SCIENZE E TECNOLOGIE DELLE COSTRUZIONI AERONAUTICHE"),
    "A-39": ("A039", "II GRADO", "SCIENZE E TECNOLOGIE DELLE COSTRUZIONI NAVALI"),
    "A-40": ("A040", "II GRADO", "SCIENZE E TECNOLOGIE ELETTRICHE ED ELETTRONICHE"),
    "A-41": ("A041", "II GRADO", "SCIENZE E TECNOLOGIE INFORMATICHE"),
    "A-42": ("A042", "II GRADO", "SCIENZE E TECNOLOGIE MECCANICHE"),
    "A-43": ("A043", "II GRADO", "SCIENZE E TECNOLOGIE NAUTICHE"),
    "A-44": ("A044", "II GRADO", "SCIENZE E TECNOLOGIE TESSILI, ABBIGLIAMENTO E MODA"),
    "A-45": ("A045", "II GRADO", "SCIENZE ECONOMICO-AZIENDALI"),
    "A-46": ("A046", "II GRADO", "SCIENZE GIURIDICO-ECONOMICHE"),
    "A-47": ("A047", "II GRADO", "SCIENZE MATEMATICHE APPLICATE"),
    "A-48": ("A048", "II GRADO", "SCIENZE MOTORIE E SPORTIVE II GRADO"),
    "A-50": ("A050", "II GRADO", "SCIENZE NATURALI, CHIMICHE E BIOLOGICHE"),
    "A-51": ("A051", "II GRADO", "SCIENZE, TECNOLOGIE E TECNICHE AGRARIE"),
    "A-54": ("A054", "II GRADO", "STORIA DELL'ARTE"),

    # II GRADO - Lingue straniere
    "AA24": ("AA24", "II GRADO", "LINGUE E CULTURE STRANIERE (FRANCESE)"),
    "AB24": ("AB24", "II GRADO", "LINGUE E CULTURE STRANIERE (INGLESE)"),
    "AC24": ("AC24", "II GRADO", "LINGUE E CULTURE STRANIERE (SPAGNOLO)"),
    "AD24": ("AD24", "II GRADO", "LINGUE E CULTURE STRANIERE (TEDESCO)"),
    "AE24": ("AE24", "II GRADO", "LINGUE E CULTURE STRANIERE (RUSSO)"),

    # II GRADO - Strumenti musicali
    "AA55": ("AA55", "II GRADO", "STRUMENTO MUSICALE (ARPA)"),
    "AB55": ("AB55", "II GRADO", "STRUMENTO MUSICALE (CHITARRA)"),
    "AC55": ("AC55", "II GRADO", "STRUMENTO MUSICALE (CLARINETTO)"),
    "AD55": ("AD55", "II GRADO", "STRUMENTO MUSICALE (CORNO)"),
    "AG55": ("AG55", "II GRADO", "STRUMENTO MUSICALE (FLAUTO)"),
    "AJ55": ("AJ55", "II GRADO", "STRUMENTO MUSICALE (PIANOFORTE)"),

    # Classi B - Laboratori
    "B-02": ("B002", "II GRADO", "CONVERSAZIONE IN LINGUA STRANIERA"),
    "B-03": ("B003", "II GRADO", "LABORATORI DI FISICA"),
    "B-12": ("B012", "II GRADO", "LABORATORI DI SCIENZE E TECNOLOGIE CHIMICHE"),
    "B-15": ("B015", "II GRADO", "LABORATORI DI SCIENZE E TECNOLOGIE ELETTRICHE"),
    "B-16": ("B016", "II GRADO", "LABORATORI DI SCIENZE E TECNOLOGIE INFORMATICHE"),
    "B-17": ("B017", "II GRADO", "LABORATORI DI SCIENZE E TECNOLOGIE MECCANICHE"),
}

# Indice per ricerca: codice normalizzato -> codice ufficiale
CODICI_NORMALIZZATI = {}
for codice_uff, (codice_sidi, grado, denom) in CLASSI_CONCORSO.items():
    # Normalizza rimuovendo trattini, spazi, maiuscole/minuscole
    norm_uff = codice_uff.replace("-", "").replace(" ", "").upper()
    norm_sidi = codice_sidi.replace("-", "").replace(" ", "").upper()

    CODICI_NORMALIZZATI[norm_uff] = codice_uff
    CODICI_NORMALIZZATI[norm_sidi] = codice_uff

    # Aggiungi anche varianti comuni
    if "-" in codice_uff:
        # A-42 -> A42, A042
        senza_trattino = codice_uff.replace("-", "")
        CODICI_NORMALIZZATI[senza_trattino.upper()] = codice_uff

        # Aggiungi versione con zero padding: A42 -> A042
        if len(senza_trattino) == 3 and senza_trattino[0].isalpha():
            con_zero = senza_trattino[0] + "0" + senza_trattino[1:]
            CODICI_NORMALIZZATI[con_zero.upper()] = codice_uff


def normalizza_classe_concorso(codice: str) -> str:
    """
    Normalizza un codice classe di concorso al formato ufficiale.

    Esempi:
        "A042" -> "A-42"
        "A-42" -> "A-42"
        "A 042" -> "A-42"
        "a042" -> "A-42"
        "A001" -> "A-01"
        "AA24" -> "AA24"

    Args:
        codice: Codice da normalizzare

    Returns:
        Codice ufficiale o None se non valido
    """
    if not codice:
        return None

    # Rimuovi spazi, trattini e converti in maiuscolo
    norm = codice.replace("-", "").replace(" ", "").strip().upper()

    # Cerca nel dizionario
    return CODICI_NORMALIZZATI.get(norm)


def get_info_classe(codice: str) -> dict:
    """
    Recupera informazioni complete su una classe di concorso.

    Returns:
        Dict con codice_ufficiale, codice_sidi, grado, denominazione
        o None se non trovato
    """
    codice_norm = normalizza_classe_concorso(codice)
    if not codice_norm:
        return None

    info = CLASSI_CONCORSO.get(codice_norm)
    if not info:
        return None

    return {
        "codice_ufficiale": codice_norm,
        "codice_sidi": info[0],
        "grado": info[1],
        "denominazione": info[2]
    }


def get_esempi_classi() -> str:
    """Restituisce una stringa con esempi di classi di concorso per il prompt LLM"""
    esempi = [
        "A-01", "A-22", "A-28", "A-49",  # I grado comuni
        "A-11", "A-12", "A-13", "A-19", "A-26", "A-27", "A-42", "A-46", "A-48", "A-50",  # II grado comuni
        "AA24", "AB24", "AC24",  # Lingue
        "AB56", "AC56", "AJ56",  # Strumenti I grado
        "B-12", "B-16", "B-17",  # Laboratori
    ]
    return ", ".join(esempi)
