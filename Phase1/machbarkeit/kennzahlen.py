"""json-daten prüfen und kennzahlen berechnen; entity-klassen folgen in phase 2"""

from datetime import date, timedelta
import json
from math import ceil, isfinite
from pathlib import Path


STUDIENDATEI = Path(__file__).with_name("studienstand.json")
STATUSWERTE = {"unbekannt", "offen", "eingebucht", "bestanden", "anerkannt", "nicht_bestanden"}
ABGESCHLOSSEN = {"bestanden", "anerkannt"}


def zahl(wert, name, minimum=0):
    if type(wert) not in (int, float) or not isfinite(wert) or wert < minimum:
        raise ValueError(f"{name} muss eine endliche Zahl ab {minimum} sein.")


def titelschluessel(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Modul und Prüfungsleistung brauchen eine Bezeichnung.")
    return " ".join(text.translate(str.maketrans("", "", '"„“')).casefold().split())


def validiere(daten):
    """fehlende angaben zulassen, falsche werte und doppelzählungen verhindern"""
    try:
        if not isinstance(daten["herkunft"]["art"], str):
            raise ValueError("Die Herkunft muss angegeben sein.")
        studium = daten["studiengang"]
        if studium["name"] is not None:
            titelschluessel(studium["name"])
        beginn = date.fromisoformat(studium["beginn"]) if studium["beginn"] is not None else None
        dauer = studium["vollzeitdauer_jahre"]
        if type(dauer) is not int or dauer <= 0:
            raise ValueError("Die Zieldauer muss eine positive Anzahl Jahre sein.")
        if beginn is not None:
            zieldatum(beginn, dauer)
        zahl(studium["zielnote"], "Zielnote", minimum=0.1)
        if studium["gesamt_ects"] is not None:
            zahl(studium["gesamt_ects"], "Gesamt-ECTS", minimum=1)
        if type(studium["leistungsstand_vollstaendig"]) is not bool:
            raise ValueError("Der Vollständigkeitsvermerk muss wahr oder falsch sein.")
        if not isinstance(studium["studienphasen"], list):
            raise ValueError("Studienphasen müssen als Liste gespeichert sein.")
        vorher = None
        for phase in studium["studienphasen"]:
            start = date.fromisoformat(phase["beginn"])
            if beginn is None or (vorher is None and start != beginn):
                raise ValueError("Die erste Studienphase muss am Studienbeginn anfangen.")
            if vorher is not None and start <= vorher:
                raise ValueError("Studienphasen müssen zeitlich aufsteigend und eindeutig sein.")
            vorher = start
            modell, faktor = phase["modell"], phase["vollzeitanteil"]
            if modell not in {"teilzeit", "vollzeit"}:
                raise ValueError("Studienmodell muss teilzeit oder vollzeit sein.")
            if faktor is not None:
                zahl(faktor, "Vollzeitanteil", minimum=0.01)
                if faktor > 1 or (modell == "teilzeit" and faktor >= 1):
                    raise ValueError("Teilzeitanteil muss kleiner als 1 sein.")
            if modell == "vollzeit" and faktor != 1:
                raise ValueError("Vollzeit entspricht dem Anteil 1.")
        if not isinstance(studium["semester"], list):
            raise ValueError("Semester müssen als Liste gespeichert sein.")
        nummern = set()
        for semester in studium["semester"]:
            nummer = semester["nummer"]
            if type(nummer) is not int or nummer <= 0 or nummer in nummern:
                raise ValueError("Semesternummern müssen positiv und eindeutig sein.")
            nummern.add(nummer)
        if not isinstance(studium["module"], list):
            raise ValueError("Module müssen als Liste gespeichert sein.")
        titel = set()
        for modul in studium["module"]:
            schluessel = titelschluessel(modul["titel"])
            if schluessel in titel:
                raise ValueError("Ein Modul darf nur einmal vorkommen.")
            titel.add(schluessel)
            nummer = modul["semester"]
            if nummer is not None and (type(nummer) is not int or nummer not in nummern):
                raise ValueError("Die Semesterzuordnung verweist auf kein erfasstes Semester.")
            if modul["ects"] is not None:
                zahl(modul["ects"], "Modul-ECTS", minimum=1)
            leistungen = modul["pruefungsleistungen"]
            if not isinstance(leistungen, list) or not leistungen:
                raise ValueError("Ein Modul braucht mindestens eine geplante Prüfungsleistung.")
            namen = set()
            for pruefung in leistungen:
                name = titelschluessel(pruefung["name"])
                if name in namen:
                    raise ValueError("Eine Prüfungsleistung darf im Modul nur einmal vorkommen.")
                namen.add(name)
                if pruefung["status"] not in STATUSWERTE:
                    raise ValueError("Unbekannter Leistungsstatus.")
                if pruefung["note"] is not None:
                    zahl(pruefung["note"], "Note", minimum=0.1)
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError("Die Datei entspricht nicht dem erwarteten Studiendatenformat.") from error


def lade_daten(datei=STUDIENDATEI):
    with Path(datei).open(encoding="utf-8") as quelle:
        daten = json.load(quelle)
    validiere(daten)
    return daten


def zieldatum(beginn, jahre):
    """vollzeit-referenzdauer; ein 29. februar endet ggf. am 28. februar"""
    try:
        return beginn.replace(year=beginn.year + jahre)
    except ValueError:
        if beginn.month == 2 and beginn.day == 29:
            return beginn.replace(year=beginn.year + jahre, day=28)
        raise


def gewichtete_tage(phasen, bis):
    """die letzte phase gilt bis zur nächsten phase bzw. bis zum stichtag"""
    tage = 0
    for index, phase in enumerate(phasen):
        start = date.fromisoformat(phase["beginn"])
        ende = min(bis, date.fromisoformat(phasen[index + 1]["beginn"])) if index + 1 < len(phasen) else bis
        tage += max(0, (ende - start).days) * phase["vollzeitanteil"]
    return tage


def zieltermin_mit_phasen(phasen, vollzeit_tage):
    """das vollzeitbudget über die bekannten studienphasen verteilen"""
    rest = vollzeit_tage
    for index, phase in enumerate(phasen):
        start = date.fromisoformat(phase["beginn"])
        faktor = phase["vollzeitanteil"]
        if index + 1 < len(phasen):
            naechster_start = date.fromisoformat(phasen[index + 1]["beginn"])
            kapazitaet = (naechster_start - start).days * faktor
            if rest > kapazitaet:
                rest -= kapazitaet
                continue
        return start + timedelta(days=ceil(rest / faktor))


def berechne(daten, stichtag):
    # shortcut: ein ist-datenstand; historische verläufe benötigen abschlussdaten
    validiere(daten)
    studium = daten["studiengang"]
    module = studium["module"]
    leistungen = [p for m in module for p in m["pruefungsleistungen"]]
    noten = [p["note"] for p in leistungen if p["note"] is not None]
    unbekannt = sum(p["status"] == "unbekannt" for p in leistungen)
    fertig = [m for m in module if all(p["status"] in ABGESCHLOSSEN for p in m["pruefungsleistungen"])]
    ects_fehlen = any(m["ects"] is None for m in fertig)
    erworben = None if unbekannt or ects_fehlen else sum(m["ects"] for m in fertig)
    gesamt = studium["gesamt_ects"]
    if gesamt is not None and erworben is not None and erworben > gesamt:
        raise ValueError("Erworbene ECTS überschreiten den angegebenen Gesamtumfang.")
    ergebnis = {
        "module": module,
        "anzahl_leistungen": len(leistungen),
        "abgeschlossene_module": len(fertig),
        "anerkannte_leistungen": sum(p["status"] == "anerkannt" for p in leistungen),
        "eingebuchte_leistungen": sum(p["status"] == "eingebucht" for p in leistungen),
        "erfasste_ects": None if any(m["ects"] is None for m in module) else sum(m["ects"] for m in module),
        "erworbene_ects": erworben,
        "unbekannte_status": unbekannt,
        "notenschnitt": sum(noten) / len(noten) if noten else None,
        "anzahl_noten": len(noten),
        "zeitstatus": "Nicht beurteilbar",
        "zeitplan_hinweise": [],
        "zieldatum": None,
        "soll_ects": None,
        "abweichung_ects": None,
    }
    hinweise = ergebnis["zeitplan_hinweise"]
    if studium["beginn"] is None:
        hinweise.append("Studienbeginn fehlt")
    if gesamt is None:
        hinweise.append("Gesamt-ECTS fehlen")
    if erworben is None:
        hinweise.append("ECTS oder Leistungsstatus unvollständig")
    if not studium["leistungsstand_vollstaendig"]:
        hinweise.append("vollständiger Leistungsstand nicht bestätigt")
    phasen = studium["studienphasen"]
    if not phasen:
        hinweise.append("Studienmodell fehlt")
    elif any(p["vollzeitanteil"] is None for p in phasen):
        hinweise.append("Teilzeitumfang fehlt")
    if studium["beginn"] is not None:
        beginn = date.fromisoformat(studium["beginn"])
        vollzeit_tage = (zieldatum(beginn, studium["vollzeitdauer_jahre"]) - beginn).days
        if phasen and all(p["vollzeitanteil"] is not None for p in phasen):
            ergebnis["zieldatum"] = zieltermin_mit_phasen(phasen, vollzeit_tage)
    if hinweise:
        return ergebnis
    ende = ergebnis["zieldatum"]
    zeitanteil = min(1.0, gewichtete_tage(phasen, min(stichtag, ende)) / vollzeit_tage)
    soll = gesamt * zeitanteil
    ergebnis["soll_ects"] = soll
    ergebnis["abweichung_ects"] = erworben - soll
    if stichtag < beginn:
        ergebnis["zeitstatus"] = "Noch nicht begonnen"
    elif erworben >= gesamt:
        ergebnis["zeitstatus"] = "Zielumfang erreicht"
    else:
        ergebnis["zeitstatus"] = "Im Zeitplan" if erworben >= soll else "Hinter dem Zeitplan"
    return ergebnis
