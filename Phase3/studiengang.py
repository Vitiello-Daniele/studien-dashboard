"""studiengang mit gemeinsam verwalteten zuordnungen"""

from datetime import date

from datenobjekte import Studienplanung
from modul import Modul
from semester import Semester
from studienphase import Studienphase
from zeitrechnung import monate_addieren


class Studiengang:
    def __init__(self, name: str | None = None) -> None:
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("der name muss text enthalten oder fehlen")

        self._name = name.strip() if name is not None else None
        self._semester = []
        self._module = []
        self._beginn = None
        self._vollzeitdauer_monate = 36
        self._zielnote = 2.0
        self._gesamt_ects = None
        self._leistungsstand_vollstaendig = False
        self._studienphasen = ()

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def semester(self) -> tuple[Semester, ...]:
        return tuple(self._semester)

    @property
    def module(self) -> tuple[Modul, ...]:
        return tuple(self._module)

    @property
    def beginn(self) -> date | None:
        return self._beginn

    @property
    def vollzeitdauer_monate(self) -> int:
        return self._vollzeitdauer_monate

    @property
    def zielnote(self) -> float:
        return self._zielnote

    @property
    def gesamt_ects(self) -> int | None:
        return self._gesamt_ects

    @property
    def leistungsstand_vollstaendig(self) -> bool:
        return self._leistungsstand_vollstaendig

    @property
    def studienphasen(self) -> tuple[Studienphase, ...]:
        return self._studienphasen

    @property
    def planung(self) -> Studienplanung:
        return Studienplanung(
            self.name,
            self.beginn,
            self.vollzeitdauer_monate,
            self.zielnote,
            self.gesamt_ects,
            self.leistungsstand_vollstaendig,
            self.studienphasen,
        )

    def planung_aendern(self, werte: Studienplanung) -> None:
        """vollständige planung erst nach allen prüfungen übernehmen"""
        if not isinstance(werte, Studienplanung):
            raise ValueError("die planung muss als studienplanung vorliegen")
        name = werte.name
        beginn = werte.beginn
        dauer = werte.vollzeitdauer_monate
        ziel = werte.zielnote
        ects = werte.gesamt_ects
        vollstaendig = werte.leistungsstand_vollstaendig
        phasen = werte.studienphasen
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("der studiengangsname muss text enthalten oder fehlen")
        if beginn is not None and type(beginn) is not date:
            raise ValueError("der studienbeginn muss ein datum sein oder fehlen")
        if type(dauer) is not int or dauer <= 0:
            raise ValueError("die vollzeitdauer muss eine positive ganze monatszahl sein")
        if beginn is not None:
            monate_addieren(beginn, dauer)
        if type(ziel) not in (int, float) or not 1 <= ziel <= 5:
            raise ValueError("die zielnote muss zwischen 1 und 5 liegen")
        if ects is not None and (type(ects) is not int or ects <= 0):
            raise ValueError("gesamt-ects müssen eine positive ganzzahl sein oder fehlen")
        if ects is not None and sum(m.ects or 0 for m in self.module) > ects:
            raise ValueError("die erfassten modul-ects überschreiten das gesamtziel")
        if type(vollstaendig) is not bool:
            raise ValueError("die vollständigkeit muss wahr oder falsch sein")
        if not isinstance(phasen, tuple) or any(not isinstance(p, Studienphase) for p in phasen):
            raise ValueError("studienphasen müssen als tupel von studienphasen vorliegen")
        if phasen and (beginn is None or phasen[0].beginn != beginn):
            raise ValueError("die erste studienphase muss am studienbeginn anfangen")
        if any(a.beginn >= b.beginn for a, b in zip(phasen, phasen[1:])):
            raise ValueError("studienphasen müssen zeitlich aufsteigend und eindeutig sein")
        if any(p._studiengang is not None and p._studiengang is not self for p in phasen):
            raise ValueError("die studienphase gehört bereits zu einem anderen studiengang")

        for phase in self._studienphasen:
            if phase not in phasen:
                phase._studiengang = None
        for phase in phasen:
            phase._studiengang = self

        self._name = name.strip() if name is not None else None
        self._beginn = beginn
        self._vollzeitdauer_monate = dauer
        self._zielnote = ziel
        self._gesamt_ects = ects
        self._leistungsstand_vollstaendig = vollstaendig
        self._studienphasen = tuple(phasen)

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
        if any(m.titel.casefold() == modul.titel.casefold() for m in self.module):
            raise ValueError("das modul ist bereits erfasst")
        if self.gesamt_ects is not None:
            umfang = sum(m.ects or 0 for m in self.module) + (modul.ects or 0)
            if umfang > self.gesamt_ects:
                raise ValueError("die erfassten modul-ects überschreiten das gesamtziel")

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
