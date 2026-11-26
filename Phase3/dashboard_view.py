"""tkinter-ansicht für kennzahlen, leistungen und studienplanung"""

from dataclasses import asdict
from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk

from dashboard_controller import DashboardController
from datenobjekte import (
    DashboardDaten,
    EinstellungenEingabe,
    Leistungsaktion,
    LeistungsAenderung,
    ModulAnzeige,
)
from pruefungsleistung import Leistungsstatus


def zahltext(wert, stellen=1):
    return "nicht verfügbar" if wert is None else f"{wert:.{stellen}f}".replace(".", ",")


def eingabe(rahmen, zeile, titel, variable, name):
    ttk.Label(rahmen, text=titel).grid(row=zeile, column=0, sticky="w", padx=(0, 16), pady=5)
    feld = ttk.Entry(rahmen, textvariable=variable, name=name, width=36)
    feld.grid(row=zeile, column=1, sticky="ew", pady=5)
    return feld


class DashboardView:
    def __init__(self, controller: DashboardController, fenster: tk.Tk) -> None:
        self._controller = controller
        self._fenster = fenster
        self._daten: DashboardDaten | None = None
        self._filter = tk.StringVar(value="Alle Semester")
        fenster.title("Mein Studien-Dashboard")
        fenster.geometry("1180x790")
        fenster.minsize(1000, 680)
        stil = ttk.Style(fenster)
        stil.configure("TButton", padding=(9, 5))
        stil.configure("Treeview", rowheight=27, font=("Segoe UI", 10))
        stil.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        stil.configure("Titel.TLabel", font=("Segoe UI", 18, "bold"))
        stil.configure("Wert.TLabel", font=("Segoe UI", 17, "bold"))
        stil.configure("Gut.TLabel", foreground="#237444", font=("Segoe UI", 12, "bold"))
        stil.configure("Schlecht.TLabel", foreground="#a52a2a", font=("Segoe UI", 12, "bold"))
        stil.configure("Neutral.TLabel", foreground="#444444", font=("Segoe UI", 12, "bold"))
        rahmen = ttk.Frame(fenster, padding=18)
        rahmen.pack(fill="both", expand=True)
        kopf = ttk.Frame(rahmen)
        kopf.pack(fill="x")
        self._titel = ttk.Label(kopf, text="Mein Studien-Dashboard", style="Titel.TLabel")
        self._titel.pack(side="left")
        ttk.Button(
            kopf, text="Gespeicherten Stand laden", command=self._neu_laden, name="laden"
        ).pack(side="right")
        self._datum = ttk.Label(rahmen)
        self._datum.pack(anchor="w", pady=(7, 14))
        karten = ttk.Frame(rahmen)
        karten.pack(fill="x", pady=(0, 12))
        karten.columnconfigure((0, 1, 2), weight=1, uniform="karte")
        self._karten = {}
        for i, titel in enumerate(("Studienfortschritt", "Notenziel", "Zeitplan")):
            karte = ttk.LabelFrame(karten, text=titel, padding=12)
            karte.grid(
                row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 5, 0 if i == 2 else 5)
            )
            wert = ttk.Label(karte, style="Wert.TLabel", text="noch nicht geladen", wraplength=270)
            wert.pack(anchor="w")
            detail = ttk.Label(karte, justify="left", wraplength=290)
            detail.pack(anchor="w", pady=(6, 0))
            self._karten[titel] = (wert, detail)
        self._fortschritt = ttk.Progressbar(karten.winfo_children()[0], maximum=100)
        self._fortschritt.pack(fill="x", pady=(12, 0))
        self._hinweise = ttk.Label(rahmen, wraplength=1080, foreground="#8b4b00")
        self._hinweise.pack(anchor="w")
        leiste = ttk.Frame(rahmen)
        leiste.pack(fill="x", pady=(10, 8))
        ttk.Label(leiste, text="Module und Prüfungsleistungen", font=("Segoe UI", 11, "bold")).pack(
            side="left"
        )
        self._semesterwahl = ttk.Combobox(
            leiste,
            textvariable=self._filter,
            state="readonly",
            width=18,
            values=["Alle Semester"],
            name="filter",
        )
        self._semesterwahl.pack(side="right")
        self._semesterwahl.bind("<<ComboboxSelected>>", lambda event: self._tabelle_fuellen())
        tabellenrahmen = ttk.Frame(rahmen)
        tabellenrahmen.pack(fill="both", expand=True)
        tabellenrahmen.columnconfigure(0, weight=1)
        tabellenrahmen.rowconfigure(0, weight=1)
        self._tabelle = ttk.Treeview(
            tabellenrahmen,
            columns=("ects", "note", "status"),
            selectmode="browse",
            show="tree headings",
            name="tabelle",
        )
        self._tabelle.heading("#0", text="Semester / Modul / Leistung")
        self._tabelle.column("#0", width=660, minwidth=430)
        for key, titel, breite in (
            ("ects", "ECTS", 65),
            ("note", "Note", 75),
            ("status", "Status", 150),
        ):
            self._tabelle.heading(key, text=titel)
            self._tabelle.column(key, width=breite, minwidth=breite, stretch=False)
        self._tabelle.tag_configure("semester", background="#e9eef2", font=("Segoe UI", 10, "bold"))
        self._tabelle.grid(row=0, column=0, sticky="nsew")
        vertikal = ttk.Scrollbar(tabellenrahmen, command=self._tabelle.yview)
        horizontal = ttk.Scrollbar(tabellenrahmen, orient="horizontal", command=self._tabelle.xview)
        self._tabelle.configure(yscrollcommand=vertikal.set, xscrollcommand=horizontal.set)
        vertikal.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self._tabelle.bind("<Double-1>", lambda event: self._leistung_dialog(True))
        self._tabelle.bind("<<TreeviewSelect>>", lambda event: self._auswahl_aktualisieren())
        unten = ttk.Frame(rahmen)
        # knöpfe und meldung behalten auch bei kleinem fenster ihren platz
        unten.pack(before=tabellenrahmen, side="bottom", fill="x", pady=(12, 0))
        self._aktionen = {}
        for name, titel, befehl in (
            ("ergaenzen", "Leistung ergänzen", lambda: self._leistung_dialog(False)),
            ("bearbeiten", "Leistung bearbeiten", lambda: self._leistung_dialog(True)),
            ("einstellungen", "Einstellungen", self._einstellungen_dialog),
            ("speichern", "Speichern", self._speichern),
        ):
            button = ttk.Button(unten, text=titel, command=befehl, name=name, state="disabled")
            button.pack(side="left", padx=(0, 8))
            self._aktionen[name] = button
        self._meldung = ttk.Label(rahmen)
        self._meldung.pack(before=unten, side="bottom", anchor="w", pady=(9, 0))
        fenster.protocol("WM_DELETE_WINDOW", self._schliessen)
        fenster.bind("<Control-s>", lambda event: self._speichern())

    def anzeigen(self, daten: DashboardDaten) -> None:
        """einen vollständigen anzeigestand ohne fachliche änderungen darstellen"""
        self._daten = daten
        self._titel.configure(text=daten.name or "Mein Studien-Dashboard")
        stand = daten.datenstand
        stand = stand.strftime("%d.%m.%Y") if stand else "nicht angegeben"
        self._datum.configure(
            text=f"Berechnung am {daten.stichtag:%d.%m.%Y}    Datenstand: {stand}"
        )
        wert, detail = self._karten["Studienfortschritt"]
        wert.configure(
            text=f"{zahltext(daten.kennzahlen.erreichte_ects, 0)} / {zahltext(daten.kennzahlen.gesamt_ects, 0)} ECTS"
        )
        detail.configure(
            text=f"{zahltext(daten.kennzahlen.fortschritt_prozent)} % des Studienziels\n"
            f"Erfasster Modulumfang: {zahltext(daten.kennzahlen.erfasste_ects, 0)} ECTS"
        )
        self._fortschritt["value"] = daten.kennzahlen.fortschritt_prozent or 0
        wert, detail = self._karten["Notenziel"]
        note = daten.kennzahlen.notenschnitt
        wert.configure(text=zahltext(note, 2), style="Wert.TLabel")
        status = (
            "Noch keine Noten"
            if note is None
            else "Ziel erreicht"
            if note <= daten.kennzahlen.zielnote
            else "Ziel noch nicht erreicht"
        )
        stil = (
            "Neutral.TLabel"
            if note is None
            else "Gut.TLabel"
            if note <= daten.kennzahlen.zielnote
            else "Schlecht.TLabel"
        )
        detail.configure(
            text=f"Ziel: {zahltext(daten.kennzahlen.zielnote)} oder besser\n{status}", style=stil
        )
        wert, detail = self._karten["Zeitplan"]
        status = daten.kennzahlen.zeitstatus.value
        stil = (
            "Schlecht.TLabel"
            if status == "hinter_dem_zeitplan"
            else "Gut.TLabel"
            if status in ("im_zeitplan", "zielumfang_erreicht")
            else "Neutral.TLabel"
        )
        bezeichnung = {
            "nicht_beurteilbar": "Nicht beurteilbar",
            "noch_nicht_begonnen": "Noch nicht begonnen",
            "zielumfang_erreicht": "Zielumfang erreicht",
            "im_zeitplan": "Im Zeitplan",
            "hinter_dem_zeitplan": "Hinter dem Zeitplan",
        }
        wert.configure(text=bezeichnung[status], style=stil)
        abschluss = daten.kennzahlen.geplanter_abschluss
        ende = abschluss.strftime("%d.%m.%Y") if abschluss else "nicht verfügbar"
        detail.configure(
            text=f"Soll: {zahltext(daten.kennzahlen.soll_ects)} ECTS\n"
            f"Abweichung: {zahltext(daten.kennzahlen.ects_abweichung)} ECTS\nGeplanter Abschluss: {ende}"
        )
        self._hinweise.configure(text="\n".join(daten.kennzahlen.hinweise))
        self._hinweise.pack_forget()
        if daten.kennzahlen.hinweise:
            self._hinweise.pack(before=self._semesterwahl.master, anchor="w")
        auswahl = ["Alle Semester"] + [f"Semester {s}" for s in daten.semester]
        self._semesterwahl.configure(values=auswahl)
        if self._filter.get() not in auswahl:
            self._filter.set("Alle Semester")
        self._tabelle_fuellen()
        for name, button in self._aktionen.items():
            button.configure(state="normal" if name != "bearbeiten" else "disabled")
        if not daten.semester:
            self._aktionen["ergaenzen"].configure(state="disabled")
        self._meldung.configure(
            text="Änderungen nicht gespeichert" if daten.geaendert else "Datei geladen"
        )

    def fehler_anzeigen(self, text: str) -> None:
        messagebox.showerror("Eingabe oder Datei prüfen", text, parent=self._fenster)

    def starten(self) -> None:
        self._neu_laden()
        self._fenster.mainloop()

    def _tabelle_fuellen(self) -> None:
        self._tabelle.delete(*self._tabelle.get_children())
        if self._daten is None:
            return
        for nummer in self._daten.semester:
            if self._filter.get() not in ("Alle Semester", f"Semester {nummer}"):
                continue
            semester_id = f"s_{nummer}"
            self._tabelle.insert(
                "", "end", iid=semester_id, text=f"Semester {nummer}", open=True, tags=("semester",)
            )
            for modul in sorted(self._daten.module, key=lambda m: m.titel.casefold()):
                if modul.semester != nummer:
                    continue
                leistungen = modul.leistungen
                note = (
                    zahltext(leistungen[0].note)
                    if len(leistungen) == 1 and leistungen[0].note is not None
                    else ""
                )
                status = (
                    leistungen[0].status.value.replace("_", " ")
                    if len(leistungen) == 1
                    else f"{len(leistungen)} Leistungen"
                )
                modul_id = f"m_{modul.index}"
                self._tabelle.insert(
                    semester_id,
                    "end",
                    iid=modul_id,
                    text=modul.titel,
                    open=True,
                    values=(modul.ects if modul.ects is not None else "", note, status),
                )
                if len(leistungen) > 1:
                    for p in leistungen:
                        self._tabelle.insert(
                            modul_id,
                            "end",
                            iid=f"p_{modul.index}_{p.index}",
                            text=p.name,
                            values=(
                                "",
                                zahltext(p.note) if p.note is not None else "",
                                p.status.value.replace("_", " "),
                            ),
                        )

    def _auswahl(self) -> tuple[ModulAnzeige, int] | None:
        auswahl = self._tabelle.selection()
        if not auswahl or self._daten is None:
            return None
        teile = auswahl[0].split("_")
        if teile[0] == "s":
            return None
        modul = next(m for m in self._daten.module if m.index == int(teile[1]))
        if teile[0] == "p":
            return modul, int(teile[2])
        return (modul, 0) if len(modul.leistungen) == 1 else None

    def _auswahl_aktualisieren(self) -> None:
        self._aktionen["bearbeiten"].configure(state="normal" if self._auswahl() else "disabled")

    def _neu_laden(self) -> None:
        if not self._aenderungen_klaeren():
            return
        try:
            self.anzeigen(self._controller.laden())
        except (OSError, ValueError) as fehler:
            self.fehler_anzeigen(str(fehler))

    def _speichern(self) -> bool:
        try:
            self._controller.speichern()
            self.anzeigen(self._controller.aktualisieren(date.today()))
            self._meldung.configure(text="Gespeichert")
            return True
        except (OSError, ValueError) as fehler:
            self.fehler_anzeigen(str(fehler))
            return False

    def _aenderungen_klaeren(self) -> bool:
        if not self._controller.geaendert:
            return True
        antwort = messagebox.askyesnocancel(
            "Änderungen speichern?",
            "Sollen die Änderungen gespeichert werden?",
            parent=self._fenster,
        )
        if antwort is None:
            return False
        return self._speichern() if antwort else True

    def _schliessen(self) -> None:
        if self._aenderungen_klaeren():
            self._fenster.destroy()

    def _dialog(self, name, titel):
        fenster = tk.Toplevel(self._fenster, name=name)
        fenster.title(titel)
        fenster.transient(self._fenster)
        fenster.resizable(False, False)
        fenster.grab_set()
        fenster.bind("<Escape>", lambda event: fenster.destroy())
        rahmen = ttk.Frame(fenster, padding=18)
        rahmen.pack(fill="both", expand=True)
        rahmen.columnconfigure(1, weight=1)
        return fenster, rahmen

    def _leistung_dialog(self, bearbeiten: bool) -> None:
        if self._daten is None:
            return
        auswahl = self._auswahl() if bearbeiten else None
        if bearbeiten and auswahl is None:
            return
        fenster, rahmen = self._dialog(
            "leistung", "Leistung bearbeiten" if bearbeiten else "Leistung ergänzen"
        )
        module = {m.titel: m for m in self._daten.module}
        alt = auswahl[0].leistungen[auswahl[1]] if auswahl else None
        werte = {
            key: tk.StringVar(fenster, value=value)
            for key, value in {
                "modul": auswahl[0].titel if auswahl else "Neues Modul",
                "titel": "",
                "ects": "5",
                "semester": str(auswahl[0].semester if auswahl else self._daten.semester[-1]),
                "name": alt.name if alt else "",
                "note": str(alt.note).replace(".", ",") if alt and alt.note is not None else "",
                "status": alt.status.value.replace("_", " ") if alt else "offen",
            }.items()
        }
        ttk.Label(rahmen, text="Modul").grid(row=0, column=0, sticky="w")
        modulwahl = ttk.Combobox(
            rahmen,
            name="modul",
            textvariable=werte["modul"],
            width=58,
            state="disabled" if bearbeiten else "readonly",
            values=["Neues Modul"] + sorted(module, key=str.casefold),
        )
        modulwahl.grid(row=0, column=1, sticky="ew", pady=5)
        neues_modul = ttk.Frame(rahmen)
        neues_modul.grid(row=1, column=0, columnspan=2, sticky="ew")
        neues_modul.columnconfigure(1, weight=1)
        eingabe(neues_modul, 0, "Neuer Modultitel", werte["titel"], "titel")
        eingabe(neues_modul, 1, "ECTS", werte["ects"], "ects")
        ttk.Label(rahmen, text="Semester").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            rahmen,
            textvariable=werte["semester"],
            values=self._daten.semester,
            state="readonly",
            name="semester",
        ).grid(row=2, column=1, sticky="ew", pady=5)
        eingabe(rahmen, 3, "Prüfungsleistung", werte["name"], "name")
        eingabe(rahmen, 4, "Note (optional)", werte["note"], "note")
        ttk.Label(rahmen, text="Status").grid(row=5, column=0, sticky="w")
        ttk.Combobox(
            rahmen,
            textvariable=werte["status"],
            values=[s.value.replace("_", " ") for s in Leistungsstatus],
            state="readonly",
            name="status",
        ).grid(row=5, column=1, sticky="ew", pady=5)

        def modul_waehlen(event=None):
            if not bearbeiten and modulwahl.current() == 0:
                neues_modul.grid()
            else:
                neues_modul.grid_remove()
                modul = module[werte["modul"].get()]
                werte["semester"].set(str(modul.semester))
                if not bearbeiten:
                    werte["name"].set("")

        def uebernehmen():
            modulname = werte["modul"].get()
            modul = None if not bearbeiten and modulwahl.current() == 0 else module[modulname]
            name = werte["name"].get()
            if not name.strip() and modul is None:
                name = werte["titel"].get()
            try:
                eingaben = LeistungsAenderung(
                    aktion=Leistungsaktion.bearbeiten
                    if bearbeiten
                    else Leistungsaktion.neues_modul
                    if modul is None
                    else Leistungsaktion.ergaenzen,
                    modul_index=modul.index if modul else None,
                    leistung_index=auswahl[1] if auswahl else None,
                    name=name,
                    note=werte["note"].get(),
                    status=Leistungsstatus(werte["status"].get().replace(" ", "_")),
                    semester=werte["semester"].get(),
                    titel=werte["titel"].get(),
                    ects=werte["ects"].get(),
                )
                self._controller.leistung_aendern(eingaben)
                self.anzeigen(self._controller.aktualisieren(date.today()))
                fenster.destroy()
            except ValueError as fehler:
                messagebox.showerror("Leistung prüfen", str(fehler), parent=fenster)

        modulwahl.bind("<<ComboboxSelected>>", modul_waehlen)
        modul_waehlen()
        self._dialog_knopfe(rahmen, 6, fenster, uebernehmen)

    def _einstellungen_dialog(self) -> None:
        if self._daten is None:
            return
        fenster, rahmen = self._dialog("einstellungen", "Einstellungen")
        werte = {
            key: tk.StringVar(fenster, value="" if value is None else str(value))
            for key, value in asdict(self._daten.planung).items()
            if key != "leistungsstand_vollstaendig"
        }
        vollstaendig = tk.BooleanVar(fenster, value=self._daten.planung.leistungsstand_vollstaendig)
        for i, (key, titel) in enumerate(
            (
                ("name", "Studiengang"),
                ("beginn", "Studienbeginn (JJJJ-MM-TT)"),
                ("gesamt_ects", "Gesamt-ECTS"),
                ("zielnote", "Zielnote"),
                ("vollzeitdauer_monate", "Vollzeitdauer (Monate)"),
            )
        ):
            eingabe(rahmen, i, titel, werte[key], key)
        ttk.Label(rahmen, text="Studienmodell").grid(row=5, column=0, sticky="w")
        modelle = ["vollzeit", "teilzeit", "mischmodell"]
        if werte["modell"].get() == "vorhandene phasen":
            modelle.append("vorhandene phasen")
        modellwahl = ttk.Combobox(
            rahmen, textvariable=werte["modell"], values=modelle, state="readonly", name="modell"
        )
        modellwahl.grid(row=5, column=1, sticky="ew", pady=5)
        teilzeit = eingabe(
            rahmen,
            6,
            "Gesamtdauer bei Teilzeit (Monate)",
            werte["teilzeitdauer_monate"],
            "teilzeitdauer_monate",
        )
        monate = eingabe(
            rahmen, 7, "Teilzeit am Anfang (Monate)", werte["teilzeitmonate"], "teilzeitmonate"
        )
        ttk.Checkbutton(
            rahmen,
            text="Alle bisherigen Leistungen sind erfasst",
            variable=vollstaendig,
            name="vollstaendig",
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=9)
        ttk.Label(
            rahmen,
            text="Fehlen bisherige Leistungen, ist keine verlässliche Bewertung des Zeitplans möglich.",
            wraplength=480,
            justify="left",
        ).grid(row=9, column=0, columnspan=2, sticky="w")

        def modell_waehlen(event=None):
            teilzeit.configure(
                state="normal"
                if werte["modell"].get() in ("teilzeit", "mischmodell")
                else "disabled"
            )
            monate.configure(
                state="normal" if werte["modell"].get() == "mischmodell" else "disabled"
            )

        def uebernehmen():
            eingaben = EinstellungenEingabe(
                name=werte["name"].get(),
                beginn=werte["beginn"].get(),
                vollzeitdauer_monate=werte["vollzeitdauer_monate"].get(),
                zielnote=werte["zielnote"].get(),
                gesamt_ects=werte["gesamt_ects"].get(),
                modell=werte["modell"].get(),
                teilzeitdauer_monate=werte["teilzeitdauer_monate"].get(),
                teilzeitmonate=werte["teilzeitmonate"].get(),
                leistungsstand_vollstaendig=vollstaendig.get(),
            )
            try:
                self._controller.einstellungen_aendern(eingaben)
                self.anzeigen(self._controller.aktualisieren(date.today()))
                fenster.destroy()
            except ValueError as fehler:
                messagebox.showerror("Einstellungen prüfen", str(fehler), parent=fenster)

        modellwahl.bind("<<ComboboxSelected>>", modell_waehlen)
        modell_waehlen()
        self._dialog_knopfe(rahmen, 10, fenster, uebernehmen)

    def _dialog_knopfe(self, rahmen, zeile, fenster, befehl):
        knopfe = ttk.Frame(rahmen)
        knopfe.grid(row=zeile, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(knopfe, text="Abbrechen", command=fenster.destroy, name="abbrechen").pack(
            side="left", padx=8
        )
        ttk.Button(knopfe, text="Übernehmen", command=befehl, name="uebernehmen").pack(side="left")
