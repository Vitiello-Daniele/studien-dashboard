"""vollständige dateien, gemeinsame referenzen und sichere fehlerfälle"""

from dataclasses import replace
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from datenhilfe import dateidaten
from json_repository import JsonRepository


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pfad = Path(self.temp.name) / "studiendaten.json"
        self.daten = dateidaten()
        self.schreiben(self.daten)
        self.repo = JsonRepository(self.pfad)

    def schreiben(self, daten):
        self.pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")

    def test_alle_werte_und_referenzen_bleiben_beim_rundlauf_erhalten(self):
        s = self.repo.laden()
        self.repo.speichern(s)
        neu = self.repo.laden()
        self.assertEqual(len(neu.module), 30)
        gespeichert = json.loads(self.pfad.read_text(encoding="utf-8"))["studiengang"]
        self.assertEqual(gespeichert, self.daten["studiengang"])
        for m in neu.module:
            self.assertTrue(any(m is anderes for anderes in m.semester.module))
        self.assertIsNot(s.module[0], neu.module[0])

    def test_alte_jahresdauer_wird_in_monate_umgewandelt(self):
        self.daten["studiengang"]["vollzeitdauer_jahre"] = 3
        del self.daten["studiengang"]["vollzeitdauer_monate"]
        self.schreiben(self.daten)
        s = self.repo.laden()
        self.assertEqual(s.vollzeitdauer_monate, 36)
        self.repo.speichern(s)
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        self.assertNotIn("vollzeitdauer_jahre", daten["studiengang"])

    def test_fachlich_ungueltige_dateien_werden_abgewiesen(self):
        for aenderung in (
            lambda s: s["module"].append(deepcopy(s["module"][0])),
            lambda s: s["module"][0].update(semester=9),
            lambda s: s["module"][0].update(semester=True),
            lambda s: s["module"][0].update(pruefungsleistungen=[]),
            lambda s: s["module"][0]["pruefungsleistungen"][0].update(note=float("nan")),
            lambda s: s["module"][0]["pruefungsleistungen"][0].update(status="fertig"),
            lambda s: s["studienphasen"].reverse(),
            lambda s: s.update(leistungsstand_vollstaendig="ja"),
            lambda s: s.update(gesamt_ects=100),
            lambda s: s.update(semester=None),
        ):
            daten = deepcopy(self.daten)
            aenderung(daten["studiengang"])
            self.schreiben(daten)
            with self.subTest(daten=daten["studiengang"]), self.assertRaises(ValueError):
                self.repo.laden()

    def test_fehlerhafte_struktur_und_beschaedigte_datei(self):
        self.repo.laden()
        datenstand = self.repo.datenstand
        ohne_titel = deepcopy(self.daten)
        del ohne_titel["studiengang"]["module"][0]["titel"]
        for inhalt, meldung in (
            (b"{", "kein gültiges json.*zeile 1"),
            (b"\xff", "utf-8"),
            (b"null", "falsch aufgebaut"),
            (b"[]", "falsch aufgebaut"),
            (b"{}", "feld fehlt.*studiengang"),
            (b'{"studiengang": 12}', "falsch aufgebaut"),
            (b'{"studiengang": {}, "studiengang": {}}', "doppelter eintrag"),
            (json.dumps(ohne_titel).encode("utf-8"), "feld fehlt.*titel"),
        ):
            self.pfad.write_bytes(inhalt)
            with self.subTest(meldung=meldung), self.assertRaisesRegex(ValueError, meldung):
                self.repo.laden()
            self.assertEqual(self.pfad.read_bytes(), inhalt)
            self.assertEqual(self.repo.datenstand, datenstand)

    def test_schreibfehler_erhaelt_datei_und_entfernt_temporaere_reste(self):
        s = self.repo.laden()
        alt = self.pfad.read_bytes()
        with patch("json_repository.json.dump", side_effect=OSError("datenträger voll")):
            with self.assertRaises(OSError):
                self.repo.speichern(s)
        self.assertEqual(self.pfad.read_bytes(), alt)
        self.assertEqual(list(self.pfad.parent.iterdir()), [self.pfad])

    def test_gesperrte_zieldatei_bleibt_erhalten(self):
        s = self.repo.laden()
        alt = self.pfad.read_bytes()
        with patch("json_repository.os.replace", side_effect=PermissionError("datei gesperrt")):
            with self.assertRaises(PermissionError):
                self.repo.speichern(s)
        self.assertEqual(self.pfad.read_bytes(), alt)
        self.assertEqual(list(self.pfad.parent.iterdir()), [self.pfad])

    def test_herkunft_bleibt_erhalten_und_boolesche_jahresdauer_ist_ungueltig(self):
        self.daten["herkunft"]["quelle"] = "eigene liste"
        self.schreiben(self.daten)
        self.repo.speichern(self.repo.laden())
        self.assertEqual(
            json.loads(self.pfad.read_text(encoding="utf-8"))["herkunft"]["quelle"], "eigene liste"
        )
        self.daten["studiengang"].pop("vollzeitdauer_monate")
        self.daten["studiengang"]["vollzeitdauer_jahre"] = True
        self.schreiben(self.daten)
        with self.assertRaises(ValueError):
            self.repo.laden()

    def test_zweite_instanz_darf_neueren_dateistand_nicht_ueberschreiben(self):
        s = self.repo.laden()
        zweite = JsonRepository(self.pfad)
        anderer_stand = zweite.laden()
        anderer_stand.planung_aendern(replace(anderer_stand.planung, name="Geändert"))
        zweite.speichern(anderer_stand)
        neuer_inhalt = self.pfad.read_bytes()
        with self.assertRaises(ValueError):
            self.repo.speichern(s)
        self.assertEqual(self.pfad.read_bytes(), neuer_inhalt)


if __name__ == "__main__":
    unittest.main()
