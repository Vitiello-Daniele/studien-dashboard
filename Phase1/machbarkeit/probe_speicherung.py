"""schreiben und wiederladen der json-studiendaten ohne änderung der quelle"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from kennzahlen import STUDIENDATEI, lade_daten


def pruefe(datei=STUDIENDATEI):
    original_bytes = Path(datei).read_bytes()
    original = lade_daten(datei)
    with TemporaryDirectory(prefix="phase1_json_") as ordner:
        datei_test = Path(ordner) / "prüfung.json"
        with datei_test.open("x", encoding="utf-8") as ziel:
            json.dump(original, ziel, ensure_ascii=False, indent=2, allow_nan=False)
        assert lade_daten(datei_test) == original, "Der JSON-Rundlauf verändert die Daten."
    assert Path(datei).read_bytes() == original_bytes, "Die Quelldatei wurde verändert."
    print(f"JSON-Test bestanden: {Path(datei).name}; Quelle unverändert.")


if __name__ == "__main__":
    pruefe()
