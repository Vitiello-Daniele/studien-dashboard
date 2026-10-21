"""technische tests; geänderte werte sind testfälle, keine persönlichen studiendaten"""

import copy
from datetime import date, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
import unittest

from kennzahlen import STUDIENDATEI, berechne, lade_daten, validiere, zieldatum
from probe_gui import baue_fenster
from probe_speicherung import pruefe


class MachbarkeitTests(unittest.TestCase):
    def setUp(self):
        self.daten = lade_daten()
        self.studium = self.daten["studiengang"]
        self.studium.update(beginn=None, gesamt_ects=None,
                            leistungsstand_vollstaendig=False, studienphasen=[])
        self.studium["module"] = self.studium["module"][:2]
        self.module = self.studium["module"]
        for modul in self.module:
            for pruefung in modul["pruefungsleistungen"]:
                pruefung.update(note=None, status="unbekannt")

    def test_fehlende_noten_werden_nicht_erfunden(self):
        result = berechne(self.daten, date(2026, 10, 9))
        self.assertEqual(result["erfasste_ects"], 10)
        self.assertIsNone(result["notenschnitt"])
        self.assertEqual(result["zeitstatus"], "Nicht beurteilbar")
        self.assertEqual(result["unbekannte_status"], 2)

    def test_json_schreiben_und_lesen(self):
        pruefe(STUDIENDATEI)

    def test_beschaedigte_datei_wird_nicht_ueberschrieben(self):
        with TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "defekt.json"
            pfad.write_text("{kaputt", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                lade_daten(pfad)
            self.assertEqual(pfad.read_text(encoding="utf-8"), "{kaputt")

    def zeitdaten(self):
        self.studium["beginn"] = "2026-04-26"
        self.studium["studienphasen"] = [{"beginn": "2026-04-26", "modell": "vollzeit", "vollzeitanteil": 1.0}]
        self.studium["vollzeitdauer_jahre"] = 3
        self.studium["gesamt_ects"] = 10  # technischer mini-plan, kein studienumfang
        self.studium["leistungsstand_vollstaendig"] = True
        for modul in self.module:
            modul["pruefungsleistungen"][0]["status"] = "offen"
        beginn = date(2026, 4, 26)
        ende = zieldatum(beginn, 3)
        return beginn + timedelta(days=(ende - beginn).days // 2)

    def test_zeitplan_erreicht(self):
        mitte = self.zeitdaten()
        self.module[0]["pruefungsleistungen"][0]["status"] = "bestanden"
        result = berechne(self.daten, mitte)
        self.assertEqual(result["zeitstatus"], "Im Zeitplan")
        self.assertAlmostEqual(result["soll_ects"], 5)
        self.assertAlmostEqual(result["abweichung_ects"], 0)

    def test_zeitplan_rueckstand(self):
        mitte = self.zeitdaten()
        result = berechne(self.daten, mitte)
        self.assertEqual(result["zeitstatus"], "Hinter dem Zeitplan")
        self.assertAlmostEqual(result["abweichung_ects"], -5)

    def test_unbekannter_status_verhindert_zeiturteil(self):
        mitte = self.zeitdaten()
        self.module[0]["pruefungsleistungen"][0]["status"] = "unbekannt"
        self.assertEqual(berechne(self.daten, mitte)["zeitstatus"], "Nicht beurteilbar")

    def test_unvollstaendiger_leistungsstand_verhindert_zeiturteil(self):
        mitte = self.zeitdaten()
        self.studium["leistungsstand_vollstaendig"] = False
        self.assertEqual(berechne(self.daten, mitte)["zeitstatus"], "Nicht beurteilbar")

    def test_vor_beginn_und_nach_zieltermin(self):
        self.zeitdaten()
        self.assertEqual(berechne(self.daten, date(2026, 4, 25))["zeitstatus"], "Noch nicht begonnen")
        result = berechne(self.daten, date(2030, 4, 26))
        self.assertEqual(result["soll_ects"], 10)
        self.assertEqual(result["zeitstatus"], "Hinter dem Zeitplan")
        for modul in self.module:
            modul["pruefungsleistungen"][0]["status"] = "bestanden"
        self.assertEqual(berechne(self.daten, date(2029, 4, 26))["zeitstatus"], "Zielumfang erreicht")
        self.assertEqual(berechne(self.daten, date(2030, 4, 26))["zeitstatus"], "Zielumfang erreicht")

    def test_kalenderjahre_und_schaltjahr(self):
        self.assertEqual(zieldatum(date(2026, 4, 26), 3), date(2029, 4, 26))
        self.assertEqual(zieldatum(date(2024, 2, 29), 3), date(2027, 2, 28))

    def test_notenmittelwert_als_eigene_entwurfsregel(self):
        self.module[0]["pruefungsleistungen"][0]["note"] = 1.7
        self.module[1]["pruefungsleistungen"][0]["note"] = 2.3
        result = berechne(self.daten, date(2026, 10, 9))
        self.assertEqual(result["notenschnitt"], 2.0)
        self.assertEqual(result["anzahl_noten"], 2)

    def test_ungueltige_werte_werden_abgewiesen(self):
        for feld, wert in [("ects", 0), ("ects", True), ("ects", float("nan"))]:
            with self.subTest(wert=wert):
                daten = copy.deepcopy(self.daten)
                daten["studiengang"]["module"][0][feld] = wert
                with self.assertRaises(ValueError):
                    validiere(daten)
        for wert in [0, True, float("nan")]:
            with self.subTest(note=wert):
                daten = copy.deepcopy(self.daten)
                daten["studiengang"]["module"][0]["pruefungsleistungen"][0]["note"] = wert
                with self.assertRaises(ValueError):
                    validiere(daten)

    def test_leere_module_liefern_keinen_notenschnitt(self):
        self.studium["module"] = []
        result = berechne(self.daten, date(2026, 10, 9))
        self.assertIsNone(result["notenschnitt"])
        self.assertEqual(result["zeitstatus"], "Nicht beurteilbar")

    def test_tkinter_button_eingabe_und_fehlerbehandlung(self):
        root = tk.Tk()
        root.withdraw()
        try:
            gui = baue_fenster(root, self.daten)
            self.assertEqual(len(gui["tabelle"].get_children()), 2)
            self.assertIn("Nicht beurteilbar", gui["zeitplan"].cget("text"))
            self.assertIn("unbekannt", gui["fortschritt"].cget("text"))
            self.assertNotIn("%", gui["fortschritt"].cget("text"))
            gui["stichtag"].delete(0, "end")
            gui["stichtag"].insert(0, "kein Datum")
            gui["button"].invoke()
            self.assertIn("Eingabe prüfen", gui["meldung"].cget("text"))
            gui["stichtag"].delete(0, "end")
            gui["stichtag"].insert(0, "2026-10-09")
            gui["button"].invoke()
            self.assertEqual(gui["meldung"].cget("text"), "")
        finally:
            root.destroy()


    def test_persoenlicher_stand_ohne_doppelzaehlung(self):
        daten = lade_daten()
        for modul in daten["studiengang"]["module"]:
            for pruefung in modul["pruefungsleistungen"]:
                self.assertEqual(set(pruefung), {"name", "status", "note"})
        result = berechne(daten, date(2026, 10, 9))
        self.assertEqual(len(result["module"]), 30)
        self.assertEqual(result["anzahl_leistungen"], 30)
        self.assertEqual(result["abgeschlossene_module"], 28)
        self.assertEqual(result["anzahl_noten"], 27)
        self.assertAlmostEqual(result["notenschnitt"], 51.4 / 27)
        self.assertEqual(result["anerkannte_leistungen"], 1)
        self.assertEqual(result["eingebuchte_leistungen"], 2)
        self.assertEqual(result["erworbene_ects"], 140)
        self.assertEqual(result["erfasste_ects"], 150)
        self.assertAlmostEqual(result["soll_ects"], 180 * 974 / 1096)
        self.assertEqual(result["zeitstatus"], "Hinter dem Zeitplan")
        self.assertEqual(result["zieldatum"], date(2027, 2, 8))
        self.assertEqual(daten["studiengang"]["beginn"], "2024-01-01")
        self.assertEqual(daten["studiengang"]["studienphasen"][1]["beginn"], "2024-06-01")

    def test_anerkennung_zaehlt_ects_aber_keine_erfundene_note(self):
        mitte = self.zeitdaten()
        self.module[0]["pruefungsleistungen"][0]["status"] = "anerkannt"
        result = berechne(self.daten, mitte)
        self.assertEqual(result["erworbene_ects"], 5)
        self.assertEqual(result["abgeschlossene_module"], 1)
        self.assertIsNone(result["notenschnitt"])

    def test_fehlende_ects_werden_nicht_als_null_gezaehlt(self):
        mitte = self.zeitdaten()
        self.module[0]["pruefungsleistungen"][0]["status"] = "bestanden"
        self.module[0]["ects"] = None
        result = berechne(self.daten, mitte)
        self.assertIsNone(result["erworbene_ects"])
        self.assertIsNone(result["erfasste_ects"])
        self.assertEqual(result["zeitstatus"], "Nicht beurteilbar")

    def test_teilzeit_verlaengert_ziel_und_reduziert_soll(self):
        self.zeitdaten()
        self.studium["beginn"] = "2026-01-01"
        self.studium["vollzeitdauer_jahre"] = 1
        self.studium["gesamt_ects"] = 365  # rein technischer plan: ein ects je vollzeittag
        self.studium["studienphasen"] = [
            {"beginn": "2026-01-01", "modell": "teilzeit", "vollzeitanteil": 0.5},
            {"beginn": "2026-04-11", "modell": "vollzeit", "vollzeitanteil": 1.0},
        ]
        self.assertAlmostEqual(berechne(self.daten, date(2026, 4, 11))["soll_ects"], 50)
        self.assertAlmostEqual(berechne(self.daten, date(2026, 4, 12))["soll_ects"], 51)
        self.assertEqual(berechne(self.daten, date(2026, 4, 12))["zieldatum"], date(2027, 2, 20))

    def test_unbekannter_teilzeitumfang_verhindert_zeiturteil(self):
        mitte = self.zeitdaten()
        self.studium["studienphasen"][0].update(modell="teilzeit", vollzeitanteil=None)
        result = berechne(self.daten, mitte)
        self.assertEqual(result["zeitstatus"], "Nicht beurteilbar")
        self.assertIn("Teilzeitumfang fehlt", result["zeitplan_hinweise"])

    def test_modul_mit_zwei_leistungen_zaehlt_ects_nur_einmal(self):
        mitte = self.zeitdaten()
        erste = self.module[0]["pruefungsleistungen"][0]
        erste["status"] = "bestanden"
        zweite = copy.deepcopy(erste)
        zweite.update(name="Zweite Kursleistung", status="eingebucht")
        self.module[0]["pruefungsleistungen"].append(zweite)
        self.assertEqual(berechne(self.daten, mitte)["erworbene_ects"], 0)
        zweite["status"] = "bestanden"
        self.assertEqual(berechne(self.daten, mitte)["erworbene_ects"], 5)

    def test_doppelte_module_und_leistungen_werden_abgewiesen(self):
        daten = copy.deepcopy(self.daten)
        daten["studiengang"]["module"].append(copy.deepcopy(self.module[0]))
        with self.assertRaisesRegex(ValueError, "Modul darf nur einmal"):
            validiere(daten)
        self.module[0]["pruefungsleistungen"].append(copy.deepcopy(self.module[0]["pruefungsleistungen"][0]))
        with self.assertRaisesRegex(ValueError, "Prüfungsleistung darf"):
            validiere(self.daten)

    def test_unplausible_phase_und_semesterzuordnung(self):
        self.zeitdaten()
        self.studium["studienphasen"].append(copy.deepcopy(self.studium["studienphasen"][0]))
        with self.assertRaisesRegex(ValueError, "aufsteigend"):
            validiere(self.daten)
        self.studium["studienphasen"].pop()
        self.module[0]["semester"] = 99
        with self.assertRaisesRegex(ValueError, "Semesterzuordnung"):
            validiere(self.daten)

    def test_wahlpflichtmodule_werden_einzeln_abgeschlossen(self):
        daten = lade_daten()
        module = [m for m in daten["studiengang"]["module"] if m["semester"] == 6]
        self.assertEqual(len(module), 2)
        for modul, erworben in zip(module, (145, 150)):
            self.assertEqual(modul["ects"], 5)
            self.assertEqual(len(modul["pruefungsleistungen"]), 1)
            modul["pruefungsleistungen"][0].update(status="bestanden", note=2.0)
            self.assertEqual(berechne(daten, date(2026, 10, 9))["erworbene_ects"], erworben)

    def test_gui_zeigt_wahlpflichtmodule_einzeln(self):
        root = tk.Tk()
        root.withdraw()
        try:
            gui = baue_fenster(root, lade_daten())
            self.assertEqual(len(gui["tabelle"].get_children()), 30)
            self.assertIn("140 von 180 ECTS", gui["fortschritt"].cget("text"))
            self.assertIn("77,8 %", gui["fortschritt"].cget("text"))
            self.assertIn("1,90", gui["notenziel"].cget("text"))
            for titel in ("Einführung in Data Science", "Projekt: Objektorientierte und funktionale Programmierung mit Python"):
                zeile = next(item for item in gui["tabelle"].get_children()
                             if gui["tabelle"].item(item, "text") == titel)
                werte = gui["tabelle"].item(zeile, "values")
                self.assertEqual(str(werte[0]), "5")
                self.assertEqual(werte[1], "")
                self.assertEqual(werte[2], "eingebucht")
                self.assertEqual(gui["tabelle"].get_children(zeile), ())
            self.assertIn("Hinter dem Zeitplan", gui["zeitplan"].cget("text"))
            self.assertIn("-20,0 ECTS", gui["zeitplan"].cget("text"))
            self.assertIn("08.02.2027", gui["zeitplan"].cget("text"))
            gui["stichtag"].delete(0, "end")
            gui["stichtag"].insert(0, "2023-12-31")
            gui["button"].invoke()
            self.assertIn("Noch nicht begonnen", gui["zeitplan"].cget("text"))
            self.assertEqual(gui["meldung"].cget("text"), "")
        finally:
            root.destroy()

    def test_json_aenderung_wird_tatsaechlich_eingelesen(self):
        daten = copy.deepcopy(self.daten)
        daten["studiengang"]["module"][0]["pruefungsleistungen"][0]["note"] = 1.7
        with TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "angepasst.json"
            pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
            result = berechne(lade_daten(pfad), date(2026, 10, 9))
            self.assertEqual(result["notenschnitt"], 1.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
