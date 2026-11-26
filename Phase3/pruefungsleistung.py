"""prüfungsleistung mit geprüften eingaben"""

from enum import Enum


class Leistungsstatus(Enum):
    unbekannt = "unbekannt"
    offen = "offen"
    eingebucht = "eingebucht"
    bestanden = "bestanden"
    anerkannt = "anerkannt"
    nicht_bestanden = "nicht_bestanden"


class Pruefungsleistung:
    def __init__(
        self,
        name: str,
        note: float | None = None,
        status: Leistungsstatus = Leistungsstatus.unbekannt,
    ) -> None:
        self._modul = None
        self.aktualisieren(name, note, status)

    @property
    def name(self) -> str:
        return self._name

    @property
    def note(self) -> float | None:
        return self._note

    @property
    def status(self) -> Leistungsstatus:
        return self._status

    @property
    def abgeschlossen(self) -> bool:
        return self._status in (Leistungsstatus.bestanden, Leistungsstatus.anerkannt)

    def aktualisieren(self, name: str, note: float | None, status: Leistungsstatus) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("die prüfungsleistung braucht einen namen")
        if not isinstance(status, Leistungsstatus):
            raise ValueError("der status muss ein leistungsstatus sein")
        if note is not None:
            if type(note) not in (int, float) or not 1 <= note <= 5:
                raise ValueError("die note muss zwischen 1 und 5 liegen oder fehlen")
        if self._modul is not None and any(
            p is not self and p.name.casefold() == name.strip().casefold()
            for p in self._modul.pruefungsleistungen
        ):
            raise ValueError("die prüfungsleistung ist im modul bereits vorhanden")

        # erst nach allen prüfungen ändern, damit bei fehlern der alte stand bleibt
        self._name = name.strip()
        self._note = note
        self._status = status
