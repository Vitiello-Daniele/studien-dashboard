"""studiengang mit gemeinsam verwalteten zuordnungen"""

from modul import Modul
from semester import Semester


class Studiengang:
    def __init__(self, name: str | None = None) -> None:
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("der name muss text enthalten oder fehlen")

        self._name = name.strip() if name is not None else None
        self._semester = []
        self._module = []

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def semester(self) -> tuple[Semester, ...]:
        return tuple(self._semester)

    @property
    def module(self) -> tuple[Modul, ...]:
        return tuple(self._module)

    def semester_hinzufuegen(self, semester: Semester) -> None:
        if not isinstance(semester, Semester):
            raise ValueError("es muss ein semester angegeben werden")
        if semester._studiengang is not None:
            raise ValueError("das semester gehört bereits zu einem studiengang")
        if any(vorhanden.nummer == semester.nummer for vorhanden in self._semester):
            raise ValueError("die semesternummer ist bereits vergeben")

        self._semester.append(semester)
        semester._studiengang = self

    def modul_hinzufuegen(self, modul: Modul, semester: Semester) -> None:
        if not isinstance(modul, Modul):
            raise ValueError("es muss ein modul angegeben werden")
        if modul._studiengang is not None:
            raise ValueError("das modul gehört bereits zu einem studiengang")
        if not isinstance(semester, Semester) or semester._studiengang is not self:
            raise ValueError("das semester gehört nicht zu diesem studiengang")

        # erst nach allen prüfungen beide zugriffswege gemeinsam zuordnen
        self._module.append(modul)
        semester._module.append(modul)
        modul._studiengang = self
        modul._semester = semester

    def modul_verschieben(self, modul: Modul, semester: Semester) -> None:
        if not isinstance(modul, Modul) or modul._studiengang is not self:
            raise ValueError("das modul gehört nicht zu diesem studiengang")
        if not isinstance(semester, Semester) or semester._studiengang is not self:
            raise ValueError("das semester gehört nicht zu diesem studiengang")
        if modul.semester is semester:
            return

        modul._semester._module.remove(modul)
        semester._module.append(modul)
        modul._semester = semester

    def semester_entfernen(self, semester: Semester) -> None:
        if not isinstance(semester, Semester) or semester._studiengang is not self:
            raise ValueError("das semester gehört nicht zu diesem studiengang")
        if semester.module:
            raise ValueError("die module müssen zuerst einem anderen semester zugeordnet werden")

        self._semester.remove(semester)
        semester._studiengang = None
