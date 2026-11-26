"""objekte verbinden und das dashboard starten"""

from pathlib import Path
import tkinter as tk

from dashboard_controller import DashboardController
from dashboard_view import DashboardView
from json_repository import JsonRepository
from kennzahlen_service import KennzahlenService


class DashboardApp:
    def __init__(self, pfad: Path | None = None) -> None:
        pfad = pfad if pfad is not None else Path(__file__).parent / "daten" / "studienstand.json"
        repository = JsonRepository(pfad)
        service = KennzahlenService()
        controller = DashboardController(repository, service)
        self._view = DashboardView(controller, tk.Tk())

    def starten(self) -> None:
        self._view.starten()
