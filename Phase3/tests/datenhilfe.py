"""kleine studiengänge und unveränderte dateivorlage für tests"""

from dataclasses import replace
from datetime import date
import json
from pathlib import Path

from modul import Modul
from pruefungsleistung import Leistungsstatus, Pruefungsleistung
from semester import Semester
from studiengang import Studiengang
from studienphase import Studienmodell, Studienphase


STUDIENDATEI = Path(__file__).with_name("studienstand.json")


def dateidaten():
    return json.loads(STUDIENDATEI.read_text(encoding="utf-8"))


def studium():
    s = Studiengang("Teststudium")
    s.planung_aendern(
        replace(
            s.planung,
            beginn=date(2024, 1, 1),
            gesamt_ects=180,
            leistungsstand_vollstaendig=True,
            studienphasen=(Studienphase(date(2024, 1, 1), Studienmodell.vollzeit, 1),),
        )
    )
    s.semester_hinzufuegen(Semester(1))
    return s


def modul(s, titel="Modul", ects=5, note=2.0, status=Leistungsstatus.bestanden):
    m = Modul(titel, ects, Pruefungsleistung(titel, note, status))
    s.modul_hinzufuegen(m, s.semester[0])
    return m
