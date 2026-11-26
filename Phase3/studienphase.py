"""studienphase mit datum und studienmodell"""

from datetime import date
from enum import Enum


class Studienmodell(Enum):
    teilzeit = "teilzeit"
    vollzeit = "vollzeit"


class Studienphase:
    def __init__(self, beginn: date, modell: Studienmodell, vollzeitanteil: float | None) -> None:
        if type(beginn) is not date:
            raise ValueError("der beginn muss ein datum ohne uhrzeit sein")
        if not isinstance(modell, Studienmodell):
            raise ValueError("das modell muss ein studienmodell sein")
        if vollzeitanteil is not None:
            if type(vollzeitanteil) not in (int, float) or not 0.01 <= vollzeitanteil <= 1:
                raise ValueError("der vollzeitanteil muss zwischen 0,01 und 1 liegen")
        if modell is Studienmodell.vollzeit and vollzeitanteil != 1:
            raise ValueError("bei vollzeit muss der anteil 1 sein")
        if modell is Studienmodell.teilzeit and vollzeitanteil == 1:
            raise ValueError("bei teilzeit muss der anteil kleiner als 1 sein")

        self._beginn = beginn
        self._modell = modell
        self._vollzeitanteil = vollzeitanteil
        self._studiengang = None

    @property
    def beginn(self) -> date:
        return self._beginn

    @property
    def modell(self) -> Studienmodell:
        return self._modell

    @property
    def vollzeitanteil(self) -> float | None:
        return self._vollzeitanteil
