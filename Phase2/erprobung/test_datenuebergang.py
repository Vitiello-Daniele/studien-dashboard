"""json-datenübergang mit kleinen beispielen prüfen"""

from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path
import unittest

from probe_json import als_daten, aus_daten, rundlauf
from pruefungsleistung import Leistungsstatus, Pruefungsleistung
from studienphase import Studienmodell, Studienphase


class DatenuebergangTests(unittest.TestCase):
    def setUp(self):
        self.daten = {
            "pruefungsleistung": {
                "name": "prüfung", "note": None, "status": "eingebucht",
            },
            "studienphase": {
                "beginn": "2024-01-01", "modell": "teilzeit", "vollzeitanteil": 0.75,
            },
        }

    def test_studienphase_uebernimmt_datum_modell_und_anteil(self):
        for modell, anteil in (
            (Studienmodell.vollzeit, 1), (Studienmodell.teilzeit, 0.75),
            (Studienmodell.teilzeit, None),
        ):
            with self.subTest(modell=modell, anteil=anteil):
                phase = Studienphase(date(2024, 1, 1), modell, anteil)
                self.assertEqual(phase.beginn, date(2024, 1, 1))
                self.assertIs(phase.modell, modell)
                self.assertEqual(phase.vollzeitanteil, anteil)

    def test_studienphase_lehnt_unpassende_angaben_ab(self):
        for beginn in (None, "2024-01-01", datetime(2024, 1, 1)):
            with self.subTest(beginn=beginn):
                with self.assertRaises(ValueError):
                    Studienphase(beginn, Studienmodell.teilzeit, 0.75)
        with self.assertRaises(ValueError):
            Studienphase(date(2024, 1, 1), "teilzeit", 0.75)
        for anteil in (0, -1, 1, 1.1, True, False, "0.75", float("nan"), float("inf")):
            with self.subTest(anteil=anteil):
                with self.assertRaises(ValueError):
                    Studienphase(date(2024, 1, 1), Studienmodell.teilzeit, anteil)
        for anteil in (None, 0.75):
            with self.subTest(vollzeitanteil=anteil):
                with self.assertRaises(ValueError):
                    Studienphase(date(2024, 1, 1), Studienmodell.vollzeit, anteil)

    def test_studienphase_erlaubt_nur_lesenden_zugriff(self):
        phase = Studienphase(date(2024, 1, 1), Studienmodell.teilzeit, 0.75)
        for attribut, wert in (("beginn", None), ("modell", "fertig"), ("vollzeitanteil", 0)):
            with self.subTest(attribut=attribut):
                with self.assertRaises(AttributeError):
                    setattr(phase, attribut, wert)

    def test_json_verwendet_text_und_null(self):
        leistung = Pruefungsleistung("prüfung", status=Leistungsstatus.eingebucht)
        phase = Studienphase(date(2024, 1, 1), Studienmodell.teilzeit, 0.75)
        daten = als_daten(leistung, phase)
        self.assertEqual(daten, self.daten)
        text = json.dumps(daten, ensure_ascii=False, allow_nan=False)
        self.assertIn('"note": null', text)
        self.assertIn('"beginn": "2024-01-01"', text)
        self.assertIn('"name": "prüfung"', text)

    def test_rundlauf_erhaelt_werte_in_neuen_objekten(self):
        for note, status, modell, anteil in (
            (1.7, Leistungsstatus.bestanden, Studienmodell.vollzeit, 1),
            (None, Leistungsstatus.eingebucht, Studienmodell.teilzeit, 0.75),
            (None, Leistungsstatus.anerkannt, Studienmodell.teilzeit, None),
        ):
            with self.subTest(status=status, modell=modell, anteil=anteil):
                leistung = Pruefungsleistung("prüfung", note, status)
                phase = Studienphase(date(2024, 2, 29), modell, anteil)
                vorher = als_daten(leistung, phase)
                neue_leistung, neue_phase = rundlauf(leistung, phase)
                self.assertIsNot(neue_leistung, leistung)
                self.assertIsNot(neue_phase, phase)
                self.assertEqual(neue_leistung.name, "prüfung")
                self.assertEqual(neue_leistung.note, note)
                self.assertIs(neue_leistung.status, status)
                self.assertEqual(neue_phase.beginn, date(2024, 2, 29))
                self.assertIs(type(neue_phase.beginn), date)
                self.assertIs(neue_phase.modell, modell)
                self.assertEqual(neue_phase.vollzeitanteil, anteil)
                self.assertEqual(als_daten(leistung, phase), vorher)

    def test_unbekannte_enumwerte_werden_beim_laden_abgewiesen(self):
        for teil, feld, wert in (
            ("pruefungsleistung", "status", "fertig"),
            ("studienphase", "modell", "mischmodell"),
        ):
            with self.subTest(feld=feld):
                daten = deepcopy(self.daten)
                daten[teil][feld] = wert
                with self.assertRaises(ValueError):
                    aus_daten(daten)

    def test_ungueltige_datumswerte_werden_beim_laden_abgewiesen(self):
        for beginn in ("2024-02-30", "kein datum", "2024-01-01T12:00:00", None, 20240101):
            with self.subTest(beginn=beginn):
                self.daten["studienphase"]["beginn"] = beginn
                with self.assertRaises(ValueError):
                    aus_daten(self.daten)

    def test_unvollstaendige_oder_falsch_aufgebaute_daten_werden_abgewiesen(self):
        for daten in (None, [], {}, {"pruefungsleistung": {}, "studienphase": {}}):
            with self.subTest(daten=daten):
                with self.assertRaises(ValueError):
                    aus_daten(daten)
        for teil, feld in (("pruefungsleistung", "note"), ("studienphase", "beginn")):
            with self.subTest(feld=feld):
                daten = deepcopy(self.daten)
                del daten[teil][feld]
                with self.assertRaises(ValueError):
                    aus_daten(daten)

    def test_fachregeln_gelten_auch_beim_laden(self):
        for teil, feld, wert in (
            ("pruefungsleistung", "name", " "),
            ("pruefungsleistung", "note", 0),
            ("pruefungsleistung", "note", True),
            ("studienphase", "vollzeitanteil", 1),
            ("studienphase", "modell", "vollzeit"),
        ):
            with self.subTest(feld=feld, wert=wert):
                daten = deepcopy(self.daten)
                daten[teil][feld] = wert
                with self.assertRaises(ValueError):
                    aus_daten(daten)

    def test_vorhandene_studienphasen_behalten_ihre_werte(self):
        datei = (Path(__file__).resolve().parents[2]
                 / "Phase1" / "machbarkeit" / "studienstand.json")
        original = datei.read_bytes()
        daten = json.loads(original)["studiengang"]
        for eintrag in daten["studienphasen"]:
            with self.subTest(beginn=eintrag["beginn"]):
                probe = {
                    "pruefungsleistung": daten["module"][0]["pruefungsleistungen"][0],
                    "studienphase": eintrag,
                }
                leistung, phase = aus_daten(probe)
                self.assertEqual(als_daten(*rundlauf(leistung, phase)), probe)
        self.assertEqual(datei.read_bytes(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
