"""kalendermonate mit passenden monatsenden"""

from calendar import monthrange
from datetime import date


def monate_addieren(beginn: date, monate: int) -> date:
    if type(beginn) is not date or type(monate) is not int or monate < 0:
        raise ValueError("datum und nicht negative ganze monate angeben")
    jahr, monat = divmod(beginn.year * 12 + beginn.month - 1 + monate, 12)
    if not 1 <= jahr <= 9999:
        raise ValueError("die dauer liegt außerhalb des darstellbaren datumsbereichs")
    # fehlende tage auf das letzte gültige datum des zielmonats begrenzen
    tag = min(beginn.day, monthrange(jahr, monat + 1)[1])
    return date(jahr, monat + 1, tag)
