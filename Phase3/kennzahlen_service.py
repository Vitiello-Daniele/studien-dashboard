"""kennzahlen aus dem studiengang ohne zustandsänderung"""

from datetime import date, timedelta
from math import ceil, isclose

from datenobjekte import Kennzahlen, Zeitstatus
from pruefungsleistung import Leistungsstatus
from studiengang import Studiengang
from zeitrechnung import monate_addieren


class KennzahlenService:
    def erreichte_ects(self, s: Studiengang) -> int | None:
        if any(
            p.status is Leistungsstatus.unbekannt for m in s.module for p in m.pruefungsleistungen
        ):
            return None
        fertig = [m for m in s.module if m.abgeschlossen]
        if any(m.ects is None for m in fertig):
            return None
        return sum(m.ects for m in fertig)

    def notenschnitt(self, s: Studiengang) -> float | None:
        noten = [p.note for m in s.module for p in m.pruefungsleistungen if p.note is not None]
        return sum(noten) / len(noten) if noten else None

    def geplanter_abschluss(self, s: Studiengang) -> date | None:
        if s.beginn is None or not s.studienphasen:
            return None
        # die vollzeitdauer ergibt das gemeinsame tagesbudget aller phasen
        rest = (monate_addieren(s.beginn, s.vollzeitdauer_monate) - s.beginn).days
        for index, phase in enumerate(s.studienphasen):
            if phase.vollzeitanteil is None:
                return None
            if index + 1 < len(s.studienphasen):
                ende = s.studienphasen[index + 1].beginn
                # teilzeittage verbrauchen nur ihren vollzeitanteil vom restbudget
                kapazitaet = (ende - phase.beginn).days * phase.vollzeitanteil
                if rest > kapazitaet:
                    rest -= kapazitaet
                    continue
            try:
                tage = rest / phase.vollzeitanteil
                # kleine gleitkommafehler dürfen keinen zusätzlichen tag ergeben
                if isclose(tage, round(tage), rel_tol=1e-12, abs_tol=1e-9):
                    tage = round(tage)
                return phase.beginn + timedelta(days=ceil(tage))
            except OverflowError:
                return None

    def soll_ects(self, s: Studiengang, t: date) -> float | None:
        if type(t) is not date:
            raise ValueError("der stichtag muss ein datum ohne uhrzeit sein")
        abschluss = self.geplanter_abschluss(s)
        if s.gesamt_ects is None or abschluss is None:
            return None
        if t >= abschluss:
            return float(s.gesamt_ects)
        bis = min(t, abschluss)
        tage = 0.0
        for index, phase in enumerate(s.studienphasen):
            if phase.beginn >= bis:
                break
            ende = (
                min(bis, s.studienphasen[index + 1].beginn)
                if index + 1 < len(s.studienphasen)
                else bis
            )
            tage += max(0, (ende - phase.beginn).days) * phase.vollzeitanteil
        budget = (monate_addieren(s.beginn, s.vollzeitdauer_monate) - s.beginn).days
        # soll-ects entsprechen dem bis zum stichtag verbrauchten budgetanteil
        return s.gesamt_ects * min(1.0, tage / budget)

    def ects_abweichung(self, s: Studiengang, t: date) -> float | None:
        erreicht, soll = self.erreichte_ects(s), self.soll_ects(s, t)
        return erreicht - soll if erreicht is not None and soll is not None else None

    def zeitstatus(self, s: Studiengang, t: date) -> Zeitstatus:
        abweichung = self.ects_abweichung(s, t)
        if abweichung is None or not s.leistungsstand_vollstaendig:
            return Zeitstatus.nicht_beurteilbar
        if t < s.beginn:
            return Zeitstatus.noch_nicht_begonnen
        if self.erreichte_ects(s) >= s.gesamt_ects:
            return Zeitstatus.zielumfang_erreicht
        return Zeitstatus.im_zeitplan if abweichung >= -1e-9 else Zeitstatus.hinter_dem_zeitplan

    def berechne(self, s: Studiengang, t: date) -> Kennzahlen:
        """einzelwerte für denselben stichtag zusammenfassen"""
        erreicht = self.erreichte_ects(s)
        hinweise = []
        if s.beginn is None:
            hinweise.append("Studienbeginn fehlt")
        if s.gesamt_ects is None:
            hinweise.append("Gesamt-ECTS fehlen")
        if erreicht is None:
            hinweise.append("Leistungsstatus oder ECTS fehlen")
        if not s.leistungsstand_vollstaendig:
            hinweise.append("Leistungsstand ist nicht vollständig bestätigt")
        if not s.studienphasen:
            hinweise.append("Studienmodell fehlt")
        elif self.geplanter_abschluss(s) is None:
            if any(p.vollzeitanteil is None for p in s.studienphasen):
                hinweise.append("Teilzeitumfang fehlt")
            elif s.beginn is not None:
                hinweise.append("Plantermin liegt außerhalb des Datumsbereichs")
        return Kennzahlen(
            erreichte_ects=erreicht,
            soll_ects=self.soll_ects(s, t),
            ects_abweichung=self.ects_abweichung(s, t),
            geplanter_abschluss=self.geplanter_abschluss(s),
            zeitstatus=self.zeitstatus(s, t),
            notenschnitt=self.notenschnitt(s),
            gesamt_ects=s.gesamt_ects,
            zielnote=s.zielnote,
            fortschritt_prozent=100 * erreicht / s.gesamt_ects
            if erreicht is not None and s.gesamt_ects
            else None,
            erfasste_ects=sum(m.ects for m in s.module)
            if all(m.ects is not None for m in s.module)
            else None,
            hinweise=tuple(hinweise),
        )
