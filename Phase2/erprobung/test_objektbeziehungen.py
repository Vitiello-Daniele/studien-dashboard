"""objektbeziehungen mit kleinen beispielen und vorhandenen studiendaten prüfen"""

import gc
import json
from pathlib import Path
import unittest
import weakref

from modul import Modul
from pruefungsleistung import Leistungsstatus, Pruefungsleistung
from semester import Semester
from studiengang import Studiengang


class ObjektbeziehungenTests(unittest.TestCase):
    def setUp(self):
        self.studium = Studiengang("softwareentwicklung")
        self.erstes = Semester(1)
        self.zweites = Semester(2)
        self.studium.semester_hinzufuegen(self.erstes)
        self.studium.semester_hinzufuegen(self.zweites)
        self.leistung = Pruefungsleistung("projekt", 1.7, Leistungsstatus.bestanden)
        self.modul = Modul(" python ", 5, self.leistung)
        self.studium.modul_hinzufuegen(self.modul, self.erstes)

    def test_modul_uebernimmt_die_vorhandene_leistung(self):
        self.assertEqual(self.modul.titel, "python")
        self.assertEqual(self.modul.ects, 5)
        self.assertIs(self.modul.pruefungsleistungen[0], self.leistung)
        self.assertEqual(self.modul.pruefungsleistungen[0].note, 1.7)
        offen = Modul("weiteres modul", None, Pruefungsleistung("projekt"))
        self.assertIsNone(offen.ects)

    def test_modul_lehnt_ungueltige_angaben_ab(self):
        leistung = Pruefungsleistung("projekt")
        for titel in ("", " \t", None, 5, True):
            with self.subTest(titel=titel):
                with self.assertRaises(ValueError):
                    Modul(titel, 5, leistung)
        for ects in (0, -1, True, False, 5.0, "5", [], float("nan")):
            with self.subTest(ects=ects):
                with self.assertRaises(ValueError):
                    Modul("python", ects, leistung)
        for ungueltig in (None, "projekt", [], True):
            with self.subTest(leistung=ungueltig):
                with self.assertRaises(ValueError):
                    Modul("python", 5, ungueltig)
        gueltig = Modul("python", 5, leistung)
        self.assertIs(gueltig.pruefungsleistungen[0], leistung)

    def test_mehrere_leistungen_bleiben_eigene_objekte(self):
        zweite = Pruefungsleistung("praesentation")
        self.modul.leistung_hinzufuegen(zweite)
        self.assertEqual(self.modul.pruefungsleistungen, (self.leistung, zweite))
        zweite.aktualisieren("praesentation", 2.0, Leistungsstatus.bestanden)
        self.assertEqual(self.modul.pruefungsleistungen[1].note, 2.0)
        self.assertEqual(self.leistung.note, 1.7)

    def test_eine_leistung_gehoert_nur_zu_einem_modul(self):
        with self.assertRaises(ValueError):
            Modul("anderes modul", 5, self.leistung)
        andere = Pruefungsleistung("klausur")
        modul = Modul("anderes modul", 5, andere)
        for ziel in (self.modul, modul):
            with self.subTest(ziel=ziel.titel):
                with self.assertRaises(ValueError):
                    ziel.leistung_hinzufuegen(self.leistung)
        for ungueltig in (None, "klausur", True):
            with self.subTest(leistung=ungueltig):
                with self.assertRaises(ValueError):
                    modul.leistung_hinzufuegen(ungueltig)
        self.assertEqual(self.modul.pruefungsleistungen, (self.leistung,))
        self.assertEqual(modul.pruefungsleistungen, (andere,))

    def test_semester_prueft_seine_nummer(self):
        self.assertEqual(Semester(6).nummer, 6)
        for nummer in (0, -1, True, False, 1.0, "1", None):
            with self.subTest(nummer=nummer):
                with self.assertRaises(ValueError):
                    Semester(nummer)

    def test_studiengang_prueft_seinen_optionalen_namen(self):
        self.assertIsNone(Studiengang().name)
        self.assertEqual(Studiengang(" informatik ").name, "informatik")
        for name in ("", " \t", 1, True, []):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    Studiengang(name)

    def test_sammlungen_sind_zwischen_instanzen_getrennt(self):
        anderer = Studiengang()
        semester = Semester(1)
        anderer.semester_hinzufuegen(semester)
        self.assertEqual(anderer.semester, (semester,))
        self.assertEqual(anderer.module, ())
        self.assertEqual(semester.module, ())
        self.assertEqual(self.zweites.module, ())
        self.assertEqual(self.erstes.module, (self.modul,))
        self.assertEqual(self.studium.semester, (self.erstes, self.zweites))

    def test_beide_zugriffe_liefern_dasselbe_modul(self):
        self.assertIs(self.studium.module[0], self.erstes.module[0])
        self.assertIs(self.modul.semester, self.erstes)
        self.erstes.module[0].pruefungsleistungen[0].aktualisieren(
            "projekt", 2.0, Leistungsstatus.bestanden
        )
        self.assertEqual(self.studium.module[0].pruefungsleistungen[0].note, 2.0)

    def test_semester_werden_nicht_doppelt_zugeordnet(self):
        anderer = Studiengang()
        with self.assertRaises(ValueError):
            anderer.semester_hinzufuegen(self.erstes)
        for semester in (self.erstes, Semester(1), None, 1):
            with self.subTest(semester=semester):
                with self.assertRaises(ValueError):
                    self.studium.semester_hinzufuegen(semester)
        self.assertEqual(anderer.semester, ())
        self.assertEqual(self.studium.semester, (self.erstes, self.zweites))

    def test_module_werden_nicht_doppelt_zugeordnet(self):
        anderer = Studiengang()
        semester = Semester(1)
        anderer.semester_hinzufuegen(semester)
        with self.assertRaises(ValueError):
            anderer.modul_hinzufuegen(self.modul, semester)
        for modul in (self.modul, None, "python"):
            with self.subTest(modul=modul):
                with self.assertRaises(ValueError):
                    self.studium.modul_hinzufuegen(modul, self.zweites)
        self.assertEqual(anderer.module, ())
        self.assertEqual(semester.module, ())
        self.assertEqual(self.studium.module, (self.modul,))
        self.assertIs(self.modul.semester, self.erstes)

    def test_fremdes_semester_verhindert_die_aufnahme(self):
        anderer = Studiengang()
        fremdes = Semester(1)
        anderer.semester_hinzufuegen(fremdes)
        modul = Modul("weiteres modul", 5, Pruefungsleistung("klausur"))
        for semester in (fremdes, Semester(3), None, 1):
            with self.subTest(semester=semester):
                with self.assertRaises(ValueError):
                    self.studium.modul_hinzufuegen(modul, semester)
                self.assertIsNone(modul.semester)
                self.assertEqual(self.studium.module, (self.modul,))
        self.studium.modul_hinzufuegen(modul, self.zweites)
        self.assertIs(modul.semester, self.zweites)
        self.assertEqual(self.zweites.module, (modul,))
        self.assertEqual(fremdes.module, ())

    def test_semesterwechsel_erhaelt_modul_und_leistung(self):
        anderes = Modul("weiteres modul", 5, Pruefungsleistung("klausur"))
        self.studium.modul_hinzufuegen(anderes, self.zweites)
        self.studium.modul_verschieben(self.modul, self.zweites)
        self.assertEqual(self.erstes.module, ())
        self.assertEqual(self.zweites.module, (anderes, self.modul))
        self.assertEqual(self.studium.module, (self.modul, anderes))
        self.assertIs(self.modul.semester, self.zweites)
        self.assertIs(self.zweites.module[1].pruefungsleistungen[0], self.leistung)
        self.assertEqual(self.leistung.note, 1.7)
        self.assertIs(self.leistung.status, Leistungsstatus.bestanden)
        self.studium.modul_verschieben(self.modul, self.zweites)
        self.assertEqual(self.zweites.module, (anderes, self.modul))

    def test_fehlerhafter_wechsel_laesst_zuordnung_unveraendert(self):
        anderer = Studiengang()
        fremdes = Semester(1)
        anderer.semester_hinzufuegen(fremdes)
        fremdes_modul = Modul("fremdes modul", 5, Pruefungsleistung("projekt"))
        anderer.modul_hinzufuegen(fremdes_modul, fremdes)
        freies_modul = Modul("freies modul", 5, Pruefungsleistung("projekt"))
        for modul, semester in (
            (self.modul, fremdes), (self.modul, None), (self.modul, Semester(3)),
            (fremdes_modul, self.zweites), (freies_modul, self.zweites),
            (None, self.zweites),
        ):
            with self.subTest(modul=modul, semester=semester):
                with self.assertRaises(ValueError):
                    self.studium.modul_verschieben(modul, semester)
                self.assertEqual(self.erstes.module, (self.modul,))
                self.assertEqual(self.zweites.module, ())
                self.assertEqual(self.studium.module, (self.modul,))
                self.assertIs(self.modul.semester, self.erstes)
                self.assertEqual(fremdes.module, (fremdes_modul,))
                self.assertIs(fremdes_modul.semester, fremdes)

    def test_belegtes_semester_wird_erst_nach_dem_wechsel_entfernt(self):
        with self.assertRaises(ValueError):
            self.studium.semester_entfernen(self.erstes)
        self.assertEqual(self.studium.semester, (self.erstes, self.zweites))
        self.assertEqual(self.erstes.module, (self.modul,))
        self.studium.modul_verschieben(self.modul, self.zweites)
        self.studium.semester_entfernen(self.erstes)
        self.assertEqual(self.studium.semester, (self.zweites,))
        self.assertEqual(self.studium.module, (self.modul,))
        self.assertIs(self.modul.semester, self.zweites)
        ersatz = Semester(1)
        self.studium.semester_hinzufuegen(ersatz)
        self.assertEqual(ersatz.module, ())

    def test_fremde_semester_werden_nicht_entfernt(self):
        anderer = Studiengang()
        fremdes = Semester(1)
        anderer.semester_hinzufuegen(fremdes)
        for semester in (fremdes, Semester(3), None, 1):
            with self.subTest(semester=semester):
                with self.assertRaises(ValueError):
                    self.studium.semester_entfernen(semester)
        self.assertEqual(self.studium.semester, (self.erstes, self.zweites))
        self.assertEqual(anderer.semester, (fremdes,))

    def test_oeffentliche_zugriffe_schuetzen_die_zuordnungen(self):
        for objekt, attribut, wert in (
            (self.modul, "titel", ""), (self.modul, "ects", -1),
            (self.modul, "semester", self.zweites),
            (self.modul, "pruefungsleistungen", []),
            (self.erstes, "nummer", 2), (self.erstes, "module", []),
            (self.studium, "name", ""), (self.studium, "semester", []),
            (self.studium, "module", []),
        ):
            with self.subTest(attribut=attribut):
                with self.assertRaises(AttributeError):
                    setattr(objekt, attribut, wert)
        for sammlung in (
            self.modul.pruefungsleistungen, self.erstes.module,
            self.studium.module, self.studium.semester,
        ):
            with self.subTest(sammlung=sammlung):
                with self.assertRaises(AttributeError):
                    sammlung.clear()

    def test_externe_referenz_haelt_die_leistung_erreichbar(self):
        leistung = Pruefungsleistung("projekt", 2.0, Leistungsstatus.bestanden)
        modul = Modul("python", 5, leistung)
        referenz = weakref.ref(leistung)
        del modul
        gc.collect()
        self.assertIs(referenz(), leistung)
        self.assertEqual(leistung.note, 2.0)
        del leistung
        gc.collect()
        self.assertIsNone(referenz())

    def test_studiendaten_behalten_ihre_semesterzuordnung(self):
        datei = (Path(__file__).resolve().parents[2]
                 / "Phase1" / "machbarkeit" / "studienstand.json")
        daten = json.loads(datei.read_text(encoding="utf-8"))["studiengang"]
        studium = Studiengang(daten["name"])
        semester = {}
        for eintrag in daten["semester"]:
            semester[eintrag["nummer"]] = Semester(eintrag["nummer"])
            studium.semester_hinzufuegen(semester[eintrag["nummer"]])
        for eintrag in daten["module"]:
            leistungen = [Pruefungsleistung(
                p["name"], p["note"], Leistungsstatus(p["status"])
            ) for p in eintrag["pruefungsleistungen"]]
            modul = Modul(eintrag["titel"], eintrag["ects"], leistungen[0])
            for leistung in leistungen[1:]:
                modul.leistung_hinzufuegen(leistung)
            studium.modul_hinzufuegen(modul, semester[eintrag["semester"]])
            self.assertEqual(modul.titel, eintrag["titel"])
            self.assertEqual(modul.ects, eintrag["ects"])
            self.assertEqual(modul.semester.nummer, eintrag["semester"])
            self.assertIs(modul, semester[eintrag["semester"]].module[-1])
        self.assertEqual(len(studium.module), 30)
        self.assertEqual(sum(len(s.module) for s in studium.semester), 30)
        self.assertEqual(
            {id(m) for m in studium.module},
            {id(m) for s in studium.semester for m in s.module},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
