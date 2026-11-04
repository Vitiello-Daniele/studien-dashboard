"""datenübergang zwischen fachobjekten und einer temporären json-datei"""

from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pruefungsleistung import Leistungsstatus, Pruefungsleistung
from studienphase import Studienmodell, Studienphase


def als_daten(leistung: Pruefungsleistung, phase: Studienphase) -> dict:
    return {
        "pruefungsleistung": {
            "name": leistung.name,
            "note": leistung.note,
            "status": leistung.status.value,
        },
        "studienphase": {
            "beginn": phase.beginn.isoformat(),
            "modell": phase.modell.value,
            "vollzeitanteil": phase.vollzeitanteil,
        },
    }


def aus_daten(daten: dict) -> tuple[Pruefungsleistung, Studienphase]:
    try:
        leistung = daten["pruefungsleistung"]
        phase = daten["studienphase"]
        return (
            Pruefungsleistung(
                leistung["name"], leistung["note"], Leistungsstatus(leistung["status"])
            ),
            Studienphase(
                date.fromisoformat(phase["beginn"]),
                Studienmodell(phase["modell"]),
                phase["vollzeitanteil"],
            ),
        )
    except (KeyError, TypeError, ValueError) as fehler:
        raise ValueError("die json-angaben sind unvollständig oder ungültig") from fehler


def rundlauf(
    leistung: Pruefungsleistung, phase: Studienphase
) -> tuple[Pruefungsleistung, Studienphase]:
    daten = als_daten(leistung, phase)
    with TemporaryDirectory(prefix="phase2_json_") as ordner:
        datei = Path(ordner) / "probe.json"
        with datei.open("x", encoding="utf-8") as ziel:
            json.dump(daten, ziel, ensure_ascii=False, indent=2, allow_nan=False)
        with datei.open(encoding="utf-8") as quelle:
            return aus_daten(json.load(quelle))


if __name__ == "__main__":
    leistung = Pruefungsleistung("prüfung", status=Leistungsstatus.eingebucht)
    phase = Studienphase(date(2024, 1, 1), Studienmodell.teilzeit, 0.75)
    geladen = rundlauf(leistung, phase)
    assert als_daten(*geladen) == als_daten(leistung, phase)
    print("[ok] name, note, status, datum, modell und anteil bleiben erhalten")
    print("[ok] die temporäre datei wurde wieder entfernt")
