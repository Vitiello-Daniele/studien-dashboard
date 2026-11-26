"""benannte daten für eingaben, planung und anzeige"""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from pruefungsleistung import Leistungsstatus
from studienphase import Studienphase


class Leistungsaktion(Enum):
    neues_modul = "neues_modul"
    ergaenzen = "ergaenzen"
    bearbeiten = "bearbeiten"


class Zeitstatus(Enum):
    nicht_beurteilbar = "nicht_beurteilbar"
    noch_nicht_begonnen = "noch_nicht_begonnen"
    zielumfang_erreicht = "zielumfang_erreicht"
    im_zeitplan = "im_zeitplan"
    hinter_dem_zeitplan = "hinter_dem_zeitplan"


@dataclass(frozen=True)
class LeistungsAenderung:
    """aktion und listenpositionen ab null im aktuell geladenen studiengang"""

    aktion: Leistungsaktion
    name: str
    note: str
    status: Leistungsstatus
    semester: str
    modul_index: int | None = None
    leistung_index: int | None = None
    titel: str = ""
    ects: str = ""


@dataclass(frozen=True)
class EinstellungenEingabe:
    """dialogtexte vor der umwandlung in fachliche werte"""

    name: str
    beginn: str
    vollzeitdauer_monate: str
    zielnote: str
    gesamt_ects: str
    modell: str
    teilzeitdauer_monate: str
    teilzeitmonate: str
    leistungsstand_vollstaendig: bool


@dataclass(frozen=True)
class Studienplanung:
    """vollständige planung zur gemeinsamen fachlichen prüfung"""

    name: str | None = None
    beginn: date | None = None
    vollzeitdauer_monate: int = 36
    zielnote: float = 2.0
    gesamt_ects: int | None = None
    leistungsstand_vollstaendig: bool = False
    studienphasen: tuple[Studienphase, ...] = ()


@dataclass(frozen=True)
class LeistungsAnzeige:
    """leistung mit ihrer position innerhalb des moduls"""

    index: int
    name: str
    note: float | None
    status: Leistungsstatus


@dataclass(frozen=True)
class ModulAnzeige:
    """modul mit seiner position im studiengang und seinen leistungen"""

    index: int
    titel: str
    ects: int | None
    semester: int
    leistungen: tuple[LeistungsAnzeige, ...]


@dataclass(frozen=True)
class Kennzahlen:
    """berechnete werte ohne veränderbare fachobjekte"""

    erreichte_ects: int | None
    soll_ects: float | None
    ects_abweichung: float | None
    geplanter_abschluss: date | None
    zeitstatus: Zeitstatus
    notenschnitt: float | None
    gesamt_ects: int | None
    zielnote: float
    fortschritt_prozent: float | None
    erfasste_ects: int | None
    hinweise: tuple[str, ...]


@dataclass(frozen=True)
class DashboardDaten:
    """zusammengehöriger anzeigestand nach dem laden oder einer änderung"""

    name: str | None
    stichtag: date
    datenstand: date | None
    geaendert: bool
    semester: tuple[int, ...]
    module: tuple[ModulAnzeige, ...]
    planung: EinstellungenEingabe
    kennzahlen: Kennzahlen
