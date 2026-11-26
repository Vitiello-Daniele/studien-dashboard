"""eingaben prüfen und fachobjekte mit speicherung und berechnung verbinden"""

from datetime import date

from datenobjekte import (
    DashboardDaten,
    EinstellungenEingabe,
    Leistungsaktion,
    LeistungsAenderung,
    LeistungsAnzeige,
    ModulAnzeige,
    Studienplanung,
)
from json_repository import JsonRepository
from kennzahlen_service import KennzahlenService
from modul import Modul
from pruefungsleistung import Pruefungsleistung
from studienphase import Studienmodell, Studienphase
from zeitrechnung import monate_addieren


def zahl(text: str, feld: str, ganzzahlig: bool = False) -> int | float:
    try:
        return int(str(text)) if ganzzahlig else float(text.replace(",", "."))
    except (AttributeError, TypeError, ValueError) as fehler:
        art = "ganze zahl" if ganzzahlig else "zahl"
        raise ValueError(f"{feld}: bitte eine {art} eingeben") from fehler


class DashboardController:
    def __init__(self, repository: JsonRepository, service: KennzahlenService) -> None:
        self._repository = repository
        self._service = service
        self._studiengang = None
        self._geaendert = False

    @property
    def geaendert(self) -> bool:
        return self._geaendert

    def laden(self) -> DashboardDaten:
        studium = self._repository.laden()
        self._studiengang = studium
        self._geaendert = False
        return self.aktualisieren(date.today())

    def aktualisieren(self, stichtag: date) -> DashboardDaten:
        """anzeigewerte kopieren und fachobjekte im controller behalten"""
        s = self._geladen()
        stand = self._repository.datenstand
        return DashboardDaten(
            name=s.name,
            stichtag=stichtag,
            datenstand=date.fromisoformat(stand) if stand else None,
            geaendert=self.geaendert,
            semester=tuple(sorted(semester.nummer for semester in s.semester)),
            module=tuple(
                ModulAnzeige(
                    index=i,
                    titel=m.titel,
                    ects=m.ects,
                    semester=m.semester.nummer,
                    leistungen=tuple(
                        LeistungsAnzeige(j, p.name, p.note, p.status)
                        for j, p in enumerate(m.pruefungsleistungen)
                    ),
                )
                for i, m in enumerate(s.module)
            ),
            planung=self._planung(),
            kennzahlen=self._service.berechne(s, stichtag),
        )

    def leistung_aendern(self, werte: LeistungsAenderung) -> None:
        """aktion und zielpositionen vor jeder änderung prüfen"""
        s = self._geladen()
        if not isinstance(werte, LeistungsAenderung):
            raise ValueError("die eingabe muss als leistungsänderung vorliegen")
        try:
            aktion = werte.aktion
            index = werte.modul_index
            pruefung = werte.leistung_index
            if not isinstance(aktion, Leistungsaktion):
                raise ValueError("die leistungsaktion ist unbekannt")
            if aktion is Leistungsaktion.neues_modul:
                if index is not None or pruefung is not None:
                    raise ValueError("ein neues modul darf keine vorhandenen zielpositionen haben")
            else:
                if type(index) is not int or not 0 <= index < len(s.module):
                    raise ValueError("das ausgewählte modul ist nicht vorhanden")
                modul = s.module[index]
                if aktion is Leistungsaktion.ergaenzen:
                    if pruefung is not None:
                        raise ValueError(
                            "beim ergänzen darf keine vorhandene leistung gewählt sein"
                        )
                elif type(pruefung) is not int or not 0 <= pruefung < len(
                    modul.pruefungsleistungen
                ):
                    raise ValueError("zum bearbeiten muss eine vorhandene leistung gewählt sein")

            note = werte.note.strip()
            note = zahl(note, "note") if note else None
            leistung = Pruefungsleistung(werte.name, note, werte.status)
            nummer = zahl(werte.semester, "semester", ganzzahlig=True)
            semester = next((item for item in s.semester if item.nummer == nummer), None)
            if semester is None:
                raise ValueError("das gewählte semester ist nicht vorhanden")

            if aktion is Leistungsaktion.neues_modul:
                ects = werte.ects.strip()
                modul = Modul(
                    werte.titel, zahl(ects, "ects", ganzzahlig=True) if ects else None, leistung
                )
                s.modul_hinzufuegen(modul, semester)
            else:
                if aktion is Leistungsaktion.ergaenzen:
                    modul.leistung_hinzufuegen(leistung)
                else:
                    modul.pruefungsleistungen[pruefung].aktualisieren(
                        leistung.name, note, werte.status
                    )
                s.modul_verschieben(modul, semester)
        except (AttributeError, TypeError, ValueError) as fehler:
            raise ValueError(f"leistung prüfen: {fehler}") from fehler
        self._geaendert = True

    def einstellungen_aendern(self, werte: EinstellungenEingabe) -> None:
        """dialogtexte umwandeln und die vollständige planung gemeinsam übergeben"""
        s = self._geladen()
        if not isinstance(werte, EinstellungenEingabe):
            raise ValueError("die eingabe muss als einstellungseingabe vorliegen")
        try:
            try:
                beginn = date.fromisoformat(werte.beginn.strip()) if werte.beginn.strip() else None
            except ValueError as fehler:
                raise ValueError(
                    "studienbeginn: bitte ein gültiges datum im format jjjj-mm-tt eingeben"
                ) from fehler
            dauer = zahl(werte.vollzeitdauer_monate, "vollzeitdauer", ganzzahlig=True)
            modell = werte.modell
            if modell not in ("vollzeit", "teilzeit", "mischmodell", "vorhandene phasen"):
                raise ValueError("das studienmodell ist unbekannt")
            if modell == "vorhandene phasen":
                phasen = s.studienphasen
            elif beginn is None:
                phasen = ()
            elif modell == "vollzeit":
                phasen = (Studienphase(beginn, Studienmodell.vollzeit, 1.0),)
            else:
                teilzeitdauer = zahl(werte.teilzeitdauer_monate, "teilzeitdauer", ganzzahlig=True)
                if teilzeitdauer <= dauer or dauer <= 0:
                    raise ValueError("die teilzeitdauer muss länger als die vollzeitdauer sein")
                phasen = (Studienphase(beginn, Studienmodell.teilzeit, dauer / teilzeitdauer),)
                if modell == "mischmodell":
                    monate = zahl(werte.teilzeitmonate, "teilzeitmonate", ganzzahlig=True)
                    if not 0 < monate < teilzeitdauer:
                        raise ValueError(
                            "teilzeitmonate müssen zwischen 1 und der teilzeitdauer liegen"
                        )
                    phasen += (
                        Studienphase(monate_addieren(beginn, monate), Studienmodell.vollzeit, 1.0),
                    )
            gesamt = werte.gesamt_ects.strip()
            s.planung_aendern(
                Studienplanung(
                    name=werte.name.strip() or None,
                    beginn=beginn,
                    vollzeitdauer_monate=dauer,
                    zielnote=zahl(werte.zielnote, "zielnote"),
                    gesamt_ects=zahl(gesamt, "gesamt-ects", ganzzahlig=True) if gesamt else None,
                    leistungsstand_vollstaendig=werte.leistungsstand_vollstaendig,
                    studienphasen=phasen,
                )
            )
        except (AttributeError, TypeError, ValueError) as fehler:
            raise ValueError(f"einstellungen prüfen: {fehler}") from fehler
        self._geaendert = True

    def speichern(self) -> None:
        self._repository.speichern(self._geladen())
        self._geaendert = False

    def _geladen(self):
        if self._studiengang is None:
            raise ValueError("zuerst eine gültige studiendatei laden")
        return self._studiengang

    def _planung(self) -> EinstellungenEingabe:
        s = self._geladen()
        # freie phasenfolgen erhalten, wenn sie nicht in das einfache formular passen
        modell = "vorhandene phasen"
        teilzeitdauer = round(s.vollzeitdauer_monate * 4 / 3)
        teilzeitmonate = 1
        phasen = s.studienphasen
        if len(phasen) == 1 and phasen[0].modell is Studienmodell.vollzeit:
            modell = "vollzeit"
        elif phasen and phasen[0].vollzeitanteil and phasen[0].modell is Studienmodell.teilzeit:
            dauer = s.vollzeitdauer_monate / phasen[0].vollzeitanteil
            if dauer.is_integer():
                teilzeitdauer = int(dauer)
                if len(phasen) == 1:
                    modell = "teilzeit"
                elif len(phasen) == 2 and phasen[1].modell is Studienmodell.vollzeit:
                    monate = (
                        (phasen[1].beginn.year - s.beginn.year) * 12
                        + phasen[1].beginn.month
                        - s.beginn.month
                    )
                    if monate > 0 and monate_addieren(s.beginn, monate) == phasen[1].beginn:
                        modell = "mischmodell"
                        teilzeitmonate = monate
        return EinstellungenEingabe(
            name=s.name or "",
            beginn=s.beginn.isoformat() if s.beginn else "",
            vollzeitdauer_monate=str(s.vollzeitdauer_monate),
            zielnote=str(s.zielnote),
            gesamt_ects=str(s.gesamt_ects) if s.gesamt_ects is not None else "",
            modell=modell,
            teilzeitdauer_monate=str(teilzeitdauer),
            teilzeitmonate=str(teilzeitmonate),
            leistungsstand_vollstaendig=s.leistungsstand_vollstaendig,
        )
