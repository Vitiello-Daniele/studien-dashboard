"""eingaben, ausdrückliches speichern und konsistente ansichtsdaten"""

from dataclasses import FrozenInstanceError, replace
from datetime import date
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from datenhilfe import STUDIENDATEI
from datenobjekte import Leistungsaktion, LeistungsAenderung
from dashboard_controller import DashboardController
from json_repository import JsonRepository
from kennzahlen_service import KennzahlenService
from pruefungsleistung import Leistungsstatus


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pfad = Path(self.temp.name) / "studienstand.json"
        shutil.copy2(STUDIENDATEI, self.pfad)
        self.repo = JsonRepository(self.pfad)
        self.controller = DashboardController(self.repo, KennzahlenService())
        self.daten = self.controller.laden()

    def leistung(self, **aenderungen):
        werte = LeistungsAenderung(
            aktion=Leistungsaktion.bearbeiten,
            modul_index=29,
            leistung_index=0,
            name=self.daten.module[29].titel,
            note="1,3",
            status=Leistungsstatus.bestanden,
            semester="6",
        )
        return replace(werte, **aenderungen)

    def test_aendern_berechnet_neu_und_speichert_erst_auf_anforderung(self):
        vorher = self.pfad.read_bytes()
        self.controller.leistung_aendern(self.leistung())
        d = self.controller.aktualisieren(date(2026, 10, 9))
        self.assertEqual(d.kennzahlen.erreichte_ects, 145)
        self.assertTrue(self.controller.geaendert)
        self.assertEqual(self.pfad.read_bytes(), vorher)
        self.controller.speichern()
        self.assertFalse(self.controller.geaendert)
        self.assertEqual(self.controller.laden().kennzahlen.erreichte_ects, 145)

    def test_neues_modul_und_zusaetzliche_leistung(self):
        self.controller.leistung_aendern(
            self.leistung(
                aktion=Leistungsaktion.neues_modul,
                modul_index=None,
                leistung_index=None,
                titel="Neues Wahlmodul",
                ects="5",
                name="Projekt",
            )
        )
        self.assertEqual(len(self.controller.aktualisieren(date.today()).module), 31)
        self.controller.leistung_aendern(
            self.leistung(
                aktion=Leistungsaktion.ergaenzen,
                leistung_index=None,
                name="Zusatz",
                note="",
                status=Leistungsstatus.offen,
            )
        )
        d = self.controller.aktualisieren(date.today())
        self.assertEqual(len(d.module[29].leistungen), 2)
        self.assertEqual(d.kennzahlen.erreichte_ects, 145)

    def test_fehlerhafte_aenderung_erhaelt_die_bisherigen_angaben(self):
        for aenderung in (
            {"note": "6"},
            {"semester": "0"},
            {"status": "fertig"},
            {"modul_index": -1},
            {"leistung_index": 10},
            {"modul_index": True},
            {"leistung_index": False},
            {"semester": 1.5},
        ):
            with self.subTest(aenderung=aenderung), self.assertRaises(ValueError):
                self.controller.leistung_aendern(self.leistung(**aenderung))
            self.assertFalse(self.controller.geaendert)
            self.assertEqual(self.controller.aktualisieren(date.today()).module, self.daten.module)

        for aenderung, meldung in (
            ({"note": "abc"}, "note: bitte eine zahl"),
            ({"semester": "abc"}, "semester: bitte eine ganze zahl"),
            (
                {
                    "aktion": Leistungsaktion.neues_modul,
                    "modul_index": None,
                    "leistung_index": None,
                    "titel": "Neues Modul",
                    "ects": "abc",
                },
                "ects: bitte eine ganze zahl",
            ),
        ):
            with self.subTest(aenderung=aenderung), self.assertRaisesRegex(ValueError, meldung):
                self.controller.leistung_aendern(self.leistung(**aenderung))
            self.assertEqual(self.controller.aktualisieren(self.daten.stichtag), self.daten)

    def test_mischmodell_bildet_die_vollzeitphase_automatisch(self):
        werte = self.daten.planung
        self.assertEqual(werte.modell, "mischmodell")
        self.assertEqual(werte.teilzeitmonate, "5")
        self.controller.einstellungen_aendern(werte)
        self.assertEqual(
            self.controller.aktualisieren(date.today()).kennzahlen.geplanter_abschluss,
            date(2027, 2, 8),
        )

    def test_vollzeit_und_teilzeit_umstellen(self):
        werte = self.daten.planung
        self.controller.einstellungen_aendern(replace(werte, modell="vollzeit"))
        self.assertEqual(
            self.controller.aktualisieren(date.today()).kennzahlen.geplanter_abschluss,
            date(2027, 1, 1),
        )
        self.controller.einstellungen_aendern(
            replace(werte, modell="teilzeit", teilzeitdauer_monate="72")
        )
        self.assertEqual(
            self.controller.aktualisieren(date.today()).kennzahlen.geplanter_abschluss,
            date(2030, 1, 1),
        )

    def test_fehlerhafte_einstellungen_erhalten_die_gesamte_planung(self):
        for aenderung in (
            {"zielnote": "nan"},
            {"beginn": "2024-02-30"},
            {"teilzeitmonate": "0"},
            {"gesamt_ects": "1"},
            {"vollzeitdauer_monate": 36.5},
            {"teilzeitdauer_monate": 48.5},
            {"teilzeitmonate": True},
        ):
            with self.subTest(aenderung=aenderung), self.assertRaises(ValueError):
                self.controller.einstellungen_aendern(replace(self.daten.planung, **aenderung))
            self.assertEqual(
                self.controller.aktualisieren(date.today()).planung, self.daten.planung
            )
            self.assertFalse(self.controller.geaendert)

        for feld, meldung in (
            ("zielnote", "zielnote: bitte eine zahl"),
            ("beginn", "studienbeginn:.*jjjj-mm-tt"),
            ("vollzeitdauer_monate", "vollzeitdauer: bitte eine ganze zahl"),
            ("teilzeitdauer_monate", "teilzeitdauer: bitte eine ganze zahl"),
            ("teilzeitmonate", "teilzeitmonate: bitte eine ganze zahl"),
            ("gesamt_ects", "gesamt-ects: bitte eine ganze zahl"),
        ):
            with self.subTest(feld=feld), self.assertRaisesRegex(ValueError, meldung):
                self.controller.einstellungen_aendern(replace(self.daten.planung, **{feld: "abc"}))
            self.assertEqual(self.controller.aktualisieren(self.daten.stichtag), self.daten)

    def test_fehlgeschlagenes_speichern_behaelt_den_aenderungsstatus(self):
        self.controller.leistung_aendern(self.leistung())
        with patch.object(self.repo, "speichern", side_effect=OSError("gesperrt")):
            with self.assertRaises(OSError):
                self.controller.speichern()
        self.assertTrue(self.controller.geaendert)

    def test_defektes_neuladen_verliert_keine_offenen_aenderungen(self):
        self.controller.leistung_aendern(self.leistung())
        self.pfad.write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.controller.laden()
        self.assertEqual(self.controller.aktualisieren(date.today()).kennzahlen.erreichte_ects, 145)
        self.assertTrue(self.controller.geaendert)

    def test_ohne_geladene_datei_kann_nicht_gespeichert_werden(self):
        controller = DashboardController(self.repo, KennzahlenService())
        vorher = self.pfad.read_bytes()
        with self.assertRaises(ValueError):
            controller.speichern()
        self.assertEqual(self.pfad.read_bytes(), vorher)

    def test_aktion_und_zielpositionen_muessen_zusammenpassen(self):
        for aktion, modul, leistung in (
            (Leistungsaktion.neues_modul, 29, None),
            (Leistungsaktion.neues_modul, None, 0),
            (Leistungsaktion.ergaenzen, None, None),
            (Leistungsaktion.ergaenzen, 29, 0),
            (Leistungsaktion.bearbeiten, None, 0),
            (Leistungsaktion.bearbeiten, 29, None),
            ("bearbeiten", 29, 0),
        ):
            with self.subTest(aktion=aktion, modul=modul, leistung=leistung):
                with self.assertRaises(ValueError):
                    self.controller.leistung_aendern(
                        self.leistung(aktion=aktion, modul_index=modul, leistung_index=leistung)
                    )
                self.assertEqual(self.controller.aktualisieren(self.daten.stichtag), self.daten)

    def test_gleicher_leistungsname_in_zwei_modulen_bleibt_eindeutig(self):
        self.controller.leistung_aendern(self.leistung(modul_index=28, name="Projekt", note="2"))
        self.controller.leistung_aendern(self.leistung(name="Projekt", note="1"))
        self.controller.leistung_aendern(
            self.leistung(
                aktion=Leistungsaktion.ergaenzen, leistung_index=None, name="Klausur", note="3"
            )
        )
        self.controller.leistung_aendern(
            self.leistung(leistung_index=1, name="Klausur", note="4", semester="5")
        )
        module = self.controller.aktualisieren(date.today()).module
        self.assertEqual(module[28].leistungen[0].note, 2)
        self.assertEqual(module[29].leistungen[0].note, 1)
        self.assertEqual(module[29].leistungen[1].note, 4)
        self.assertEqual(module[29].semester, 5)

    def test_anzeigedaten_bleiben_ein_getrennter_unveraenderbarer_stand(self):
        with self.assertRaises(FrozenInstanceError):
            self.daten.module[29].leistungen[0].note = 1
        self.controller.leistung_aendern(self.leistung())
        self.assertIsNone(self.daten.module[29].leistungen[0].note)
        self.assertEqual(self.daten.kennzahlen.erreichte_ects, 140)
        self.assertEqual(self.controller.aktualisieren(date.today()).kennzahlen.erreichte_ects, 145)


if __name__ == "__main__":
    unittest.main()
