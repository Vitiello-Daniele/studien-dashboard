"""referenzwerte, fehlende angaben und grenzen der zeitplanung"""

from dataclasses import replace
from datetime import date, timedelta
import unittest

from datenhilfe import STUDIENDATEI, modul, studium
from json_repository import JsonRepository
from kennzahlen_service import KennzahlenService, Zeitstatus
from pruefungsleistung import Leistungsstatus, Pruefungsleistung
from studienphase import Studienmodell, Studienphase


class KennzahlenTests(unittest.TestCase):
    def setUp(self):
        self.service = KennzahlenService()

    def test_abgleich_mit_den_referenzwerten_aus_phase_1(self):
        s = JsonRepository(STUDIENDATEI).laden()
        d = self.service.berechne(s, date(2026, 10, 9))
        self.assertEqual(d.erreichte_ects, 140)
        self.assertEqual(d.erfasste_ects, 150)
        self.assertAlmostEqual(d.notenschnitt, 51.4 / 27)
        self.assertAlmostEqual(d.soll_ects, 180 * 974 / 1096)
        self.assertAlmostEqual(d.ects_abweichung, 140 - 180 * 974 / 1096)
        self.assertEqual(d.geplanter_abschluss, date(2027, 2, 8))
        self.assertIs(d.zeitstatus, Zeitstatus.hinter_dem_zeitplan)

    def test_module_zaehlen_einmal_und_noten_ungewichtet(self):
        s = studium()
        m = modul(s, ects=10, note=1)
        m.leistung_hinzufuegen(Pruefungsleistung("Zweite Prüfung", 3, Leistungsstatus.bestanden))
        modul(s, "Anerkennung", 5, None, Leistungsstatus.anerkannt)
        modul(s, "Offen", 5, None, Leistungsstatus.offen)
        self.assertEqual(self.service.erreichte_ects(s), 15)
        self.assertEqual(self.service.notenschnitt(s), 2)

    def test_unbekannter_status_verhindert_nur_die_betroffenen_kennzahlen(self):
        s = studium()
        modul(s, status=Leistungsstatus.unbekannt)
        d = self.service.berechne(s, date(2025, 1, 1))
        self.assertIsNone(d.erreichte_ects)
        self.assertIsNone(d.ects_abweichung)
        self.assertIsNotNone(d.soll_ects)
        self.assertEqual(d.geplanter_abschluss, date(2027, 1, 1))
        self.assertIs(d.zeitstatus, Zeitstatus.nicht_beurteilbar)

    def test_fehlende_ects_eines_abgeschlossenen_moduls(self):
        s = studium()
        m = modul(s, ects=None, note=None, status=Leistungsstatus.offen)
        self.assertEqual(self.service.erreichte_ects(s), 0)
        m.pruefungsleistungen[0].aktualisieren(m.titel, None, Leistungsstatus.anerkannt)
        self.assertIsNone(self.service.erreichte_ects(s))
        self.assertIsNone(self.service.notenschnitt(s))

    def test_alle_fuenf_zeitstatus_und_ihre_prioritaet(self):
        s = studium()
        modul(s)
        self.assertIs(
            self.service.zeitstatus(s, date(2023, 12, 31)), Zeitstatus.noch_nicht_begonnen
        )
        self.assertIs(self.service.zeitstatus(s, date(2024, 1, 1)), Zeitstatus.im_zeitplan)
        self.assertIs(self.service.zeitstatus(s, date(2026, 1, 1)), Zeitstatus.hinter_dem_zeitplan)
        s.planung_aendern(replace(s.planung, gesamt_ects=5))
        self.assertIs(self.service.zeitstatus(s, date(2026, 1, 1)), Zeitstatus.zielumfang_erreicht)
        s.planung_aendern(replace(s.planung, leistungsstand_vollstaendig=False))
        self.assertIs(self.service.zeitstatus(s, date(2026, 1, 1)), Zeitstatus.nicht_beurteilbar)

    def test_fehlende_planung_erfindet_keine_werte(self):
        s = studium()
        s.planung_aendern(
            replace(
                s.planung, studienphasen=(Studienphase(s.beginn, Studienmodell.teilzeit, None),)
            )
        )
        self.assertIsNone(self.service.geplanter_abschluss(s))
        self.assertIsNone(self.service.soll_ects(s, date(2025, 1, 1)))
        s.planung_aendern(replace(s.planung, studienphasen=(), beginn=None))
        self.assertIs(self.service.zeitstatus(s, date(2025, 1, 1)), Zeitstatus.nicht_beurteilbar)

    def test_soll_ist_vor_beginn_null_und_nach_abschluss_begrenzt(self):
        s = studium()
        for tag, soll in (
            (date(2023, 1, 1), 0),
            (s.beginn, 0),
            (date(2027, 1, 1), 180),
            (date(2030, 1, 1), 180),
        ):
            with self.subTest(tag=tag):
                self.assertEqual(self.service.soll_ects(s, tag), soll)

    def test_schaltjahr_und_reine_teilzeit(self):
        s = studium()
        beginn = date(2024, 2, 29)
        s.planung_aendern(
            replace(
                s.planung,
                beginn=beginn,
                vollzeitdauer_monate=12,
                studienphasen=(Studienphase(beginn, Studienmodell.teilzeit, 0.5),),
            )
        )
        self.assertEqual(self.service.geplanter_abschluss(s), beginn + timedelta(days=730))
        self.assertAlmostEqual(self.service.soll_ects(s, beginn + timedelta(days=365)), 90)

    def test_mehrere_wechsel_und_angebrochener_abschlusstag(self):
        s = studium()
        s.planung_aendern(
            replace(
                s.planung,
                vollzeitdauer_monate=1,
                studienphasen=(
                    Studienphase(date(2024, 1, 1), Studienmodell.teilzeit, 0.5),
                    Studienphase(date(2024, 1, 11), Studienmodell.vollzeit, 1),
                    Studienphase(date(2024, 1, 21), Studienmodell.teilzeit, 0.75),
                ),
            )
        )
        self.assertEqual(self.service.geplanter_abschluss(s), date(2024, 2, 12))
        self.assertAlmostEqual(self.service.soll_ects(s, date(2024, 1, 21)), 180 * 15 / 31)
        self.assertEqual(self.service.soll_ects(s, date(2024, 2, 12)), 180)

    def test_berechnung_veraendert_keine_fachobjekte(self):
        s = studium()
        m = modul(s)
        vorher = (s.module, s.semester[0].module, s.studienphasen, m.pruefungsleistungen[0].note)
        self.service.berechne(s, date(2025, 1, 1))
        self.assertEqual(
            vorher, (s.module, s.semester[0].module, s.studienphasen, m.pruefungsleistungen[0].note)
        )

    def test_gleitkommafehler_verlaengert_den_plan_nicht_um_einen_tag(self):
        s = studium()
        s.planung_aendern(
            replace(
                s.planung,
                vollzeitdauer_monate=9,
                studienphasen=(
                    Studienphase(date(2024, 1, 1), Studienmodell.teilzeit, 9 / 35),
                    Studienphase(date(2025, 12, 1), Studienmodell.vollzeit, 1),
                ),
            )
        )
        self.assertEqual(
            self.service.geplanter_abschluss(s), date(2025, 12, 1) + timedelta(days=94)
        )

    def test_phase_nach_dem_abschluss_aendert_keinen_plantermin(self):
        s = studium()
        s.planung_aendern(
            replace(
                s.planung,
                studienphasen=(
                    s.studienphasen[0],
                    Studienphase(date(2030, 1, 1), Studienmodell.teilzeit, None),
                ),
            )
        )
        self.assertEqual(self.service.geplanter_abschluss(s), date(2027, 1, 1))
        self.assertAlmostEqual(self.service.soll_ects(s, date(2025, 1, 1)), 180 * 366 / 1096)
        self.assertNotIn(
            "Teilzeitumfang fehlt", self.service.berechne(s, date(2025, 1, 1)).hinweise
        )


if __name__ == "__main__":
    unittest.main()
