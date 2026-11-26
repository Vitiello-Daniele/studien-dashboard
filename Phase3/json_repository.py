"""fachobjekte laden und die datei erst nach vollständigem schreiben ersetzen"""

from datetime import date
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from datenobjekte import Studienplanung
from modul import Modul
from pruefungsleistung import Leistungsstatus, Pruefungsleistung
from semester import Semester
from studiengang import Studiengang
from studienphase import Studienmodell, Studienphase


def json_objekt(eintraege):
    objekt = {}
    for name, wert in eintraege:
        if name in objekt:
            raise ValueError(f"doppelter eintrag in der json-datei: {name}")
        objekt[name] = wert
    return objekt


class JsonRepository:
    def __init__(self, pfad: Path) -> None:
        self._pfad = Path(pfad)
        self._daten = {}
        self._gelesen = None

    @property
    def datenstand(self) -> str | None:
        return self._daten.get("herkunft", {}).get("stand")

    def laden(self) -> Studiengang:
        try:
            gelesen = self._pfad.read_bytes()
            daten = json.loads(gelesen.decode("utf-8-sig"), object_pairs_hook=json_objekt)
            s = daten["studiengang"]
            studium = Studiengang(s["name"])
            dauer = s.get("vollzeitdauer_monate")
            if dauer is None:
                jahre = s["vollzeitdauer_jahre"]
                if type(jahre) is not int or jahre <= 0:
                    raise ValueError("die bisherige jahresdauer ist ungültig")
                dauer = jahre * 12
            if not all(isinstance(s[key], list) for key in ("studienphasen", "semester", "module")):
                raise ValueError("studienphasen, semester und module müssen listen sein")
            phasen = [
                Studienphase(
                    date.fromisoformat(p["beginn"]), Studienmodell(p["modell"]), p["vollzeitanteil"]
                )
                for p in s["studienphasen"]
            ]
            studium.planung_aendern(
                Studienplanung(
                    name=studium.name,
                    beginn=date.fromisoformat(s["beginn"]) if s["beginn"] is not None else None,
                    vollzeitdauer_monate=dauer,
                    zielnote=s["zielnote"],
                    gesamt_ects=s["gesamt_ects"],
                    leistungsstand_vollstaendig=s["leistungsstand_vollstaendig"],
                    studienphasen=tuple(phasen),
                )
            )
            semester = {}
            for eintrag in s["semester"]:
                objekt = Semester(eintrag["nummer"])
                studium.semester_hinzufuegen(objekt)
                semester[objekt.nummer] = objekt
            for m in s["module"]:
                if not isinstance(m["pruefungsleistungen"], list) or not m["pruefungsleistungen"]:
                    raise ValueError("ein modul braucht mindestens eine prüfungsleistung")
                if type(m["semester"]) is not int:
                    raise ValueError("jedes modul braucht eine semesternummer")
                if m["semester"] not in semester:
                    raise ValueError("das semester des moduls ist nicht vorhanden")
                leistungen = [
                    Pruefungsleistung(p["name"], p["note"], Leistungsstatus(p["status"]))
                    for p in m["pruefungsleistungen"]
                ]
                modul = Modul(m["titel"], m["ects"], leistungen[0])
                for leistung in leistungen[1:]:
                    modul.leistung_hinzufuegen(leistung)
                studium.modul_hinzufuegen(modul, semester[m["semester"]])
            herkunft = daten.get("herkunft", {})
            if not isinstance(herkunft, dict):
                raise ValueError("die herkunft muss ein objekt sein")
            if herkunft.get("stand") is not None:
                date.fromisoformat(herkunft["stand"])
        except UnicodeDecodeError as fehler:
            raise ValueError("die studiendatei muss als utf-8 gespeichert sein") from fehler
        except json.JSONDecodeError as fehler:
            raise ValueError(
                f"die studiendatei ist kein gültiges json, zeile {fehler.lineno}, spalte {fehler.colno}"
            ) from fehler
        except KeyError as fehler:
            raise ValueError(f"feld fehlt in der studiendatei: {fehler.args[0]}") from fehler
        except (TypeError, AttributeError) as fehler:
            raise ValueError("die studiendatei ist falsch aufgebaut") from fehler
        except ValueError as fehler:
            raise ValueError(f"die studiendatei enthält ungültige angaben: {fehler}") from fehler
        self._daten = daten
        self._gelesen = gelesen
        return studium

    def speichern(self, s: Studiengang) -> None:
        self._dateistand_pruefen()
        daten = self._daten.copy()
        daten["herkunft"] = {**daten.get("herkunft", {}), "stand": date.today().isoformat()}
        daten["studiengang"] = {
            "name": s.name,
            "beginn": s.beginn.isoformat() if s.beginn else None,
            "vollzeitdauer_monate": s.vollzeitdauer_monate,
            "zielnote": s.zielnote,
            "gesamt_ects": s.gesamt_ects,
            "leistungsstand_vollstaendig": s.leistungsstand_vollstaendig,
            "studienphasen": [
                {
                    "beginn": p.beginn.isoformat(),
                    "modell": p.modell.value,
                    "vollzeitanteil": p.vollzeitanteil,
                }
                for p in s.studienphasen
            ],
            "semester": [{"nummer": semester.nummer} for semester in s.semester],
            "module": [
                {
                    "titel": m.titel,
                    "ects": m.ects,
                    "semester": m.semester.nummer,
                    "pruefungsleistungen": [
                        {"name": p.name, "note": p.note, "status": p.status.value}
                        for p in m.pruefungsleistungen
                    ],
                }
                for m in s.module
            ],
        }
        temporaer = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._pfad.parent,
                prefix=".studienstand_",
                suffix=".tmp",
                delete=False,
            ) as ziel:
                temporaer = Path(ziel.name)
                json.dump(daten, ziel, ensure_ascii=False, indent=2, allow_nan=False)
                ziel.write("\n")
                ziel.flush()
                os.fsync(ziel.fileno())
            geschrieben = temporaer.read_bytes()
            self._dateistand_pruefen()
            os.replace(temporaer, self._pfad)
        finally:
            if temporaer is not None:
                temporaer.unlink(missing_ok=True)
        self._daten = daten
        self._gelesen = geschrieben

    def _dateistand_pruefen(self) -> None:
        stand = self._pfad.read_bytes() if self._pfad.exists() else None
        if stand != self._gelesen:
            raise ValueError(
                "die datei wurde außerhalb des dashboards geändert, bitte zuerst neu laden"
            )
