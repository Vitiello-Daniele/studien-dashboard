"""modul mit eigenen prüfungsleistungen"""

from pruefungsleistung import Pruefungsleistung
from semester import Semester


class Modul:
    def __init__(self, titel: str, ects: int | None, pruefungsleistung: Pruefungsleistung) -> None:
        if not isinstance(titel, str) or not titel.strip():
            raise ValueError("das modul braucht einen titel")
        if ects is not None and (type(ects) is not int or ects <= 0):
            raise ValueError("ects müssen eine positive ganzzahl sein oder fehlen")

        self._titel = titel.strip()
        self._ects = ects
        self._pruefungsleistungen = []
        # die zuordnung folgt beim aufnehmen in den studiengang
        self._studiengang = None
        self._semester = None
        self.leistung_hinzufuegen(pruefungsleistung)

    @property
    def titel(self) -> str:
        return self._titel

    @property
    def ects(self) -> int | None:
        return self._ects

    @property
    def pruefungsleistungen(self) -> tuple[Pruefungsleistung, ...]:
        return tuple(self._pruefungsleistungen)

    @property
    def semester(self) -> Semester | None:
        return self._semester

    @property
    def abgeschlossen(self) -> bool:
        return all(p.abgeschlossen for p in self._pruefungsleistungen)

    def leistung_hinzufuegen(self, leistung: Pruefungsleistung) -> None:
        if not isinstance(leistung, Pruefungsleistung):
            raise ValueError("es muss eine prüfungsleistung angegeben werden")
        if leistung._modul is not None:
            raise ValueError("die prüfungsleistung gehört bereits zu einem modul")
        if any(p.name.casefold() == leistung.name.casefold() for p in self._pruefungsleistungen):
            raise ValueError("die prüfungsleistung ist im modul bereits vorhanden")

        self._pruefungsleistungen.append(leistung)
        leistung._modul = self
