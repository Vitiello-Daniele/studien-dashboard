"""bedienelemente mit temporären studiendaten prüfen"""

from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import tkinter as tk
import unittest
from unittest.mock import patch

from datenhilfe import STUDIENDATEI
from dashboard_controller import DashboardController
from dashboard_view import DashboardView
from json_repository import JsonRepository
from kennzahlen_service import KennzahlenService


def feld(fenster, name):
    for widget in fenster.winfo_children():
        if widget.winfo_name() == name:
            return widget
        gefunden = feld(widget, name)
        if gefunden is not None:
            return gefunden
    return None


def einsetzen(widget, text):
    widget.delete(0, "end")
    widget.insert(0, text)


class OberflaechenTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pfad = Path(self.temp.name) / "studienstand.json"
        shutil.copy2(STUDIENDATEI, self.pfad)
        self.controller = DashboardController(JsonRepository(self.pfad), KennzahlenService())
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        self.view = DashboardView(self.controller, self.root)
        self.view.anzeigen(self.controller.laden())
        self.root.update_idletasks()
        self.fehler = patch("dashboard_view.messagebox.showerror").start()
        self.addCleanup(patch.stopall)

    def test_sechs_semester_und_filter(self):
        tabelle = feld(self.root, "tabelle")
        self.assertEqual(len(tabelle.get_children()), 6)
        filterfeld = feld(self.root, "filter")
        filterfeld.set("Semester 6")
        filterfeld.event_generate("<<ComboboxSelected>>")
        self.root.update()
        self.assertEqual(tabelle.get_children(), ("s_6",))
        self.assertEqual(len(tabelle.get_children("s_6")), 2)

    def test_leistung_bearbeiten_und_speichern(self):
        tabelle = feld(self.root, "tabelle")
        tabelle.selection_set("m_29")
        self.root.update()
        feld(self.root, "bearbeiten").invoke()
        dialog = feld(self.root, "leistung")
        einsetzen(feld(dialog, "note"), "1,75")
        feld(dialog, "status").set("bestanden")
        feld(dialog, "uebernehmen").invoke()
        self.assertFalse(self.fehler.called)
        self.assertEqual(self.controller.aktualisieren(date.today()).kennzahlen.erreichte_ects, 145)
        tabelle.selection_set("m_29")
        self.root.update()
        feld(self.root, "bearbeiten").invoke()
        dialog = feld(self.root, "leistung")
        self.assertEqual(feld(dialog, "note").get(), "1,75")
        feld(dialog, "uebernehmen").invoke()
        feld(self.root, "speichern").invoke()
        self.assertFalse(self.controller.geaendert)
        daten = self.controller.laden()
        self.assertEqual(daten.kennzahlen.erreichte_ects, 145)
        self.assertEqual(daten.module[29].leistungen[0].note, 1.75)

    def test_neues_modul_ueber_den_dialog(self):
        feld(self.root, "ergaenzen").invoke()
        dialog = feld(self.root, "leistung")
        einsetzen(feld(dialog, "titel"), "Neues Wahlmodul")
        feld(dialog, "uebernehmen").invoke()
        self.assertFalse(self.fehler.called)
        d = self.controller.aktualisieren(date.today())
        self.assertEqual(len(d.module), 31)
        self.assertEqual(d.module[-1].leistungen[0].name, "Neues Wahlmodul")

    def test_ergaenzen_und_bearbeiten_treffen_trotz_filter_die_richtige_leistung(self):
        vorher = self.controller.aktualisieren(date.today()).module[29].leistungen[0]
        feld(self.root, "ergaenzen").invoke()
        dialog = feld(self.root, "leistung")
        auswahl = feld(dialog, "modul")
        auswahl.set(self.controller.aktualisieren(date.today()).module[29].titel)
        auswahl.event_generate("<<ComboboxSelected>>")
        einsetzen(feld(dialog, "name"), "Zusatzprüfung")
        feld(dialog, "uebernehmen").invoke()
        filterfeld = feld(self.root, "filter")
        filterfeld.set("Semester 6")
        filterfeld.event_generate("<<ComboboxSelected>>")
        tabelle = feld(self.root, "tabelle")
        tabelle.selection_set("p_29_1")
        self.root.update()
        feld(self.root, "bearbeiten").invoke()
        dialog = feld(self.root, "leistung")
        einsetzen(feld(dialog, "note"), "1,7")
        feld(dialog, "status").set("bestanden")
        feld(dialog, "uebernehmen").invoke()
        self.assertFalse(self.fehler.called)
        leistungen = self.controller.aktualisieren(date.today()).module[29].leistungen
        self.assertEqual(leistungen[0], vorher)
        self.assertEqual(leistungen[1].name, "Zusatzprüfung")
        self.assertEqual(leistungen[1].note, 1.7)

    def test_eingabefehler_bleibt_im_dialog(self):
        feld(self.root, "ergaenzen").invoke()
        dialog = feld(self.root, "leistung")
        einsetzen(feld(dialog, "titel"), "Testmodul")
        einsetzen(feld(dialog, "note"), "6")
        feld(dialog, "uebernehmen").invoke()
        self.assertTrue(self.fehler.called)
        self.assertTrue(dialog.winfo_exists())
        self.assertFalse(self.controller.geaendert)

    def test_einstellungen_auf_vollzeit_umstellen(self):
        feld(self.root, "einstellungen").invoke()
        dialog = self.root.nametowidget("einstellungen")
        modell = feld(dialog, "modell")
        modell.set("vollzeit")
        modell.event_generate("<<ComboboxSelected>>")
        self.assertEqual(str(feld(dialog, "teilzeitmonate")["state"]), "disabled")
        feld(dialog, "uebernehmen").invoke()
        self.assertFalse(self.fehler.called)
        self.assertEqual(
            self.controller.aktualisieren(date.today()).kennzahlen.geplanter_abschluss,
            date(2027, 1, 1),
        )

    def test_abbrechen_beim_schliessen_und_verwerfen_beim_laden(self):
        werte = self.controller.aktualisieren(date.today()).planung
        self.controller.einstellungen_aendern(replace(werte, zielnote="1,5"))
        with patch("dashboard_view.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(self.view._aenderungen_klaeren())
        with patch("dashboard_view.messagebox.askyesnocancel", return_value=False):
            self.view._neu_laden()
        self.assertFalse(self.controller.geaendert)
        self.assertEqual(self.controller.aktualisieren(date.today()).kennzahlen.zielnote, 2)

    def test_speicherfehler_verhindert_das_schliessen(self):
        werte = self.controller.aktualisieren(date.today()).planung
        self.controller.einstellungen_aendern(replace(werte, zielnote="1,5"))
        with patch("dashboard_view.messagebox.askyesnocancel", return_value=True):
            with patch.object(self.controller, "speichern", side_effect=OSError("gesperrt")):
                self.assertFalse(self.view._aenderungen_klaeren())
        self.assertTrue(self.fehler.called)
        self.assertTrue(self.controller.geaendert)

    def test_bedienknoepfe_bleiben_bei_minimaler_fenstergroesse_sichtbar(self):
        self.root.geometry("1000x680")
        self.root.deiconify()
        self.root.update()
        for name in ("ergaenzen", "bearbeiten", "einstellungen", "speichern"):
            button = feld(self.root, name)
            self.assertTrue(button.winfo_ismapped())
            unten = button.winfo_rooty() + button.winfo_height()
            self.assertLessEqual(unten, self.root.winfo_rooty() + self.root.winfo_height())

    def test_fehlende_kennzahlen_bleiben_lesbar_und_werden_nicht_zu_null(self):
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        daten["studiengang"]["gesamt_ects"] = None
        daten["studiengang"]["module"][0]["pruefungsleistungen"][0]["status"] = "unbekannt"
        self.pfad.write_text(json.dumps(daten), encoding="utf-8")
        self.view.anzeigen(self.controller.laden())
        self.root.geometry("1000x680")
        self.root.deiconify()
        self.root.update()
        wert, _ = self.view._karten["Studienfortschritt"]
        self.assertIn("nicht verfügbar", wert["text"])
        for wert, detail in self.view._karten.values():
            rechts = wert.master.winfo_rootx() + wert.master.winfo_width()
            self.assertLessEqual(rechts, self.root.winfo_rootx() + self.root.winfo_width())


if __name__ == "__main__":
    unittest.main()
