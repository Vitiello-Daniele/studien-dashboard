"""technische beispiele; persönliche studiendaten werden nur gelesen"""

import json
from pathlib import Path
import unittest

from pruefungsleistung import Leistungsstatus, Pruefungsleistung


class PruefungsleistungTests(unittest.TestCase):
    def test_neue_leistung_hat_keine_erfundene_note(self):
        leistung = Pruefungsleistung("projekt")
        self.assertIsNone(leistung.note)
        self.assertIs(leistung.status, Leistungsstatus.unbekannt)
        self.assertFalse(leistung.abgeschlossen)

    def test_nur_bestanden_und_anerkannt_sind_abgeschlossen(self):
        for status in Leistungsstatus:
            with self.subTest(status=status):
                leistung = Pruefungsleistung("projekt", status=status)
                erwartet = status in (Leistungsstatus.bestanden, Leistungsstatus.anerkannt)
                self.assertEqual(leistung.abgeschlossen, erwartet)

    def test_anerkennung_braucht_keine_note(self):
        leistung = Pruefungsleistung("anerkennung", status=Leistungsstatus.anerkannt)
        self.assertTrue(leistung.abgeschlossen)
        self.assertIsNone(leistung.note)

    def test_gueltige_noten_und_grenzen(self):
        for note in (1, 1.0, 1.7, 4.0, 5):
            with self.subTest(note=note):
                leistung = Pruefungsleistung("projekt", note)
                self.assertEqual(leistung.note, note)

    def test_ungueltige_noten_werden_abgewiesen(self):
        for note in (True, False, "1.7", "", [], 0, -1, 0.9, 5.1,
                     float("nan"), float("inf"), float("-inf")):
            with self.subTest(note=note):
                with self.assertRaises(ValueError):
                    Pruefungsleistung("projekt", note)

    def test_ungueltige_namen_werden_abgewiesen(self):
        for name in ("", " \t\n", None, 5, True, []):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    Pruefungsleistung(name)

    def test_unbekannte_statuswerte_werden_abgewiesen(self):
        for status in (None, "bestanden", "fertig", 1, True, []):
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    Pruefungsleistung("projekt", status=status)

    def test_aktualisieren_aendert_auch_den_abgeleiteten_abschluss(self):
        leistung = Pruefungsleistung(" projekt ", status=Leistungsstatus.eingebucht)
        self.assertEqual(leistung.name, "projekt")
        leistung.aktualisieren("projektbericht", 1.7, Leistungsstatus.bestanden)
        self.assertEqual(leistung.name, "projektbericht")
        self.assertEqual(leistung.note, 1.7)
        self.assertIs(leistung.status, Leistungsstatus.bestanden)
        self.assertTrue(leistung.abgeschlossen)
        leistung.aktualisieren("projektbericht", None, Leistungsstatus.offen)
        self.assertIsNone(leistung.note)
        self.assertFalse(leistung.abgeschlossen)

    def test_ungueltige_aenderung_laesst_alle_werte_unveraendert(self):
        leistung = Pruefungsleistung("projekt", 2.0, Leistungsstatus.bestanden)
        for werte in (("", 1.0, Leistungsstatus.offen),
                      ("neu", 0, Leistungsstatus.offen),
                      ("neu", 1.0, "offen")):
            with self.subTest(werte=werte):
                with self.assertRaises(ValueError):
                    leistung.aktualisieren(*werte)
                self.assertEqual(leistung.name, "projekt")
                self.assertEqual(leistung.note, 2.0)
                self.assertIs(leistung.status, Leistungsstatus.bestanden)

    def test_direktes_schreiben_umgeht_die_pruefung_nicht(self):
        leistung = Pruefungsleistung("projekt")
        for attribut, wert in (("name", ""), ("note", 0),
                               ("status", "fertig"), ("abgeschlossen", True)):
            with self.subTest(attribut=attribut):
                with self.assertRaises(AttributeError):
                    setattr(leistung, attribut, wert)

    def test_zwei_instanzen_behalten_ihren_eigenen_stand(self):
        erste = Pruefungsleistung("projekt")
        zweite = Pruefungsleistung("projekt")
        erste.aktualisieren("projekt", 1.7, Leistungsstatus.bestanden)
        self.assertIsNone(zweite.note)
        self.assertIs(zweite.status, Leistungsstatus.unbekannt)
        self.assertIsNot(erste, zweite)

    def test_vorhandene_leistungen_lassen_sich_unveraendert_abbilden(self):
        datei = (Path(__file__).resolve().parents[2]
                 / "Phase1" / "machbarkeit" / "studienstand.json")
        daten = json.loads(datei.read_text(encoding="utf-8"))
        leistungen = []
        for modul in daten["studiengang"]["module"]:
            for eintrag in modul["pruefungsleistungen"]:
                leistung = Pruefungsleistung(
                    eintrag["name"], eintrag["note"], Leistungsstatus(eintrag["status"])
                )
                self.assertEqual(leistung.name, eintrag["name"])
                self.assertEqual(leistung.note, eintrag["note"])
                self.assertEqual(leistung.status.value, eintrag["status"])
                leistungen.append(leistung)
        self.assertEqual(len(leistungen), 30)
        self.assertEqual(sum(p.note is not None for p in leistungen), 27)
        self.assertEqual(sum(p.abgeschlossen for p in leistungen), 28)


if __name__ == "__main__":
    unittest.main(verbosity=2)
