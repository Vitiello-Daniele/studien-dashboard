"""gültige änderungen und zusammenhängende objektbeziehungen"""

from dataclasses import replace
from datetime import date, datetime
import unittest

from datenhilfe import modul, studium
from pruefungsleistung import Leistungsstatus, Pruefungsleistung
from semester import Semester
from studienphase import Studienmodell, Studienphase
from zeitrechnung import monate_addieren


class FachklassenTests(unittest.TestCase):
    def test_ungueltige_note_erhaelt_bisherigen_zustand(self):
        p = Pruefungsleistung("Prüfung", 2, Leistungsstatus.bestanden)
        for note in (True, False, "2", 0, 6, float("nan"), float("inf")):
            with self.subTest(note=note), self.assertRaises(ValueError):
                p.aktualisieren("Neu", note, Leistungsstatus.offen)
            self.assertEqual((p.name, p.note, p.status), ("Prüfung", 2, Leistungsstatus.bestanden))

    def test_mehrere_leistungen_muessen_abgeschlossen_sein(self):
        s = studium()
        m = modul(s)
        p = Pruefungsleistung("Projekt", status=Leistungsstatus.offen)
        m.leistung_hinzufuegen(p)
        self.assertFalse(m.abgeschlossen)
        p.aktualisieren("Projekt", None, Leistungsstatus.anerkannt)
        self.assertTrue(m.abgeschlossen)

    def test_doppelte_leistungen_bei_aufnahme_und_umbenennung(self):
        m = modul(studium())
        p = Pruefungsleistung("Projekt")
        m.leistung_hinzufuegen(p)
        with self.assertRaises(ValueError):
            m.leistung_hinzufuegen(Pruefungsleistung("modul"))
        with self.assertRaises(ValueError):
            p.aktualisieren("Modul", None, Leistungsstatus.offen)
        self.assertEqual(p.name, "Projekt")

    def test_verschieben_erhaelt_dasselbe_modul_und_seine_leistungen(self):
        s = studium()
        m = modul(s)
        p = m.pruefungsleistungen[0]
        zweites = Semester(2)
        s.semester_hinzufuegen(zweites)
        s.modul_verschieben(m, zweites)
        self.assertIs(s.module[0], zweites.module[0])
        self.assertIs(m.pruefungsleistungen[0], p)
        self.assertFalse(s.semester[0].module)
        with self.assertRaises(ValueError):
            s.semester_entfernen(zweites)

    def test_fremde_zuordnung_und_doppelte_titel_werden_abgewiesen(self):
        s = studium()
        m = modul(s)
        fremd = studium()
        with self.assertRaises(ValueError):
            s.modul_verschieben(m, fremd.semester[0])
        with self.assertRaises(ValueError):
            fremd.modul_hinzufuegen(m, fremd.semester[0])
        with self.assertRaises(ValueError):
            modul(s, "modul")
        self.assertIs(m.semester, s.semester[0])

    def test_fehlerhafte_planung_wird_nicht_teilweise_uebernommen(self):
        s = studium()
        modul(s)
        for wert in (0, True, "36", 999999):
            with self.subTest(wert=wert), self.assertRaises(ValueError):
                s.planung_aendern(replace(s.planung, name="Geändert", vollzeitdauer_monate=wert))
            self.assertEqual(s.name, "Teststudium")
            self.assertEqual(s.vollzeitdauer_monate, 36)
        with self.assertRaises(ValueError):
            s.planung_aendern(replace(s.planung, gesamt_ects=4))

    def test_studienphasen_brauchen_einen_eindeutigen_zeitablauf(self):
        s = studium()
        alt = s.studienphasen
        for phasen in (
            [Studienphase(date(2024, 2, 1), Studienmodell.vollzeit, 1)],
            [alt[0], alt[0]],
            ["teilzeit"],
        ):
            with self.subTest(phasen=phasen), self.assertRaises(ValueError):
                s.planung_aendern(replace(s.planung, studienphasen=tuple(phasen)))
            self.assertEqual(s.studienphasen, alt)

    def test_monatsenden_und_schaltjahr(self):
        self.assertEqual(monate_addieren(date(2024, 1, 31), 1), date(2024, 2, 29))
        self.assertEqual(monate_addieren(date(2024, 2, 29), 12), date(2025, 2, 28))
        self.assertEqual(monate_addieren(date(2023, 1, 31), 1), date(2023, 2, 28))
        for datum, monate in (
            (datetime(2024, 1, 1), 1),
            (date(2024, 1, 1), True),
            (date(9999, 12, 1), 1),
        ):
            with self.subTest(datum=datum, monate=monate), self.assertRaises(ValueError):
                monate_addieren(datum, monate)

    def test_studienmodell_und_anteil_muessen_zusammenpassen(self):
        for modell, anteil in (
            (Studienmodell.vollzeit, 0.75),
            (Studienmodell.teilzeit, 1),
            (Studienmodell.teilzeit, True),
            (Studienmodell.teilzeit, float("nan")),
        ):
            with self.subTest(modell=modell, anteil=anteil), self.assertRaises(ValueError):
                Studienphase(date(2024, 1, 1), modell, anteil)

    def test_studienphase_gehoert_genau_einem_studiengang(self):
        erster = studium()
        zweiter = studium()
        phase = erster.studienphasen[0]
        with self.assertRaises(ValueError):
            zweiter.planung_aendern(replace(zweiter.planung, studienphasen=(phase,)))
        self.assertIs(erster.studienphasen[0], phase)
        erster.planung_aendern(replace(erster.planung, studienphasen=()))
        zweiter.planung_aendern(replace(zweiter.planung, studienphasen=(phase,)))
        self.assertIs(zweiter.studienphasen[0], phase)


if __name__ == "__main__":
    unittest.main()
