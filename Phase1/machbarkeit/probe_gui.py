"""json-studiendaten mit ihrer modul- und kursstruktur in tkinter anzeigen"""

from datetime import date
import tkinter as tk
from tkinter import ttk

from kennzahlen import berechne, lade_daten


def baue_fenster(fenster, daten):
    fenster.title("Phase 1: Studien-Dashboard")
    fenster.geometry("1120x750")
    fenster.minsize(900, 650)
    rahmen = ttk.Frame(fenster, padding=18)
    rahmen.pack(fill="both", expand=True)
    ttk.Label(rahmen, text="Studien-Dashboard", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 10))

    eingaben = ttk.Frame(rahmen)
    eingaben.pack(fill="x")
    ttk.Label(eingaben, text="Stichtag (JJJJ-MM-TT):").pack(side="left")
    stichtag = ttk.Entry(eingaben, width=14)
    stichtag.insert(0, daten["herkunft"].get("stand", date.today().isoformat()))
    stichtag.pack(side="left", padx=8)
    aktualisieren = ttk.Button(eingaben, text="Anzeigen")
    aktualisieren.pack(side="left")
    datenstand = daten["herkunft"].get("stand", "nicht angegeben")
    ttk.Label(eingaben, text=f"Datenstand: {datenstand}").pack(side="right")

    meldung = ttk.Label(rahmen, wraplength=1040)
    meldung.pack(anchor="w", pady=(10, 6))
    karten = ttk.Frame(rahmen)
    karten.pack(fill="x", pady=(2, 12))
    werte = {}
    for titel in ("Studienfortschritt", "Notenziel", "Zeitplan"):
        karte = ttk.LabelFrame(karten, text=titel, padding=10)
        karte.pack(side="left", fill="both", expand=True, padx=(0, 8))
        label = ttk.Label(karte, text="", wraplength=290, justify="left")
        label.pack(anchor="w")
        werte[titel] = label

    tabellenrahmen = ttk.Frame(rahmen)
    tabellenrahmen.pack(fill="both", expand=True)
    tabellenrahmen.columnconfigure(0, weight=1)
    tabellenrahmen.rowconfigure(0, weight=1)
    tabelle = ttk.Treeview(tabellenrahmen, columns=("ects", "note", "status"), show="tree headings", height=12)
    tabelle.heading("#0", text="Modul / Kurs")
    tabelle.column("#0", width=530, minwidth=530)
    for name, titel, breite in [("ects", "ECTS", 65), ("note", "Note", 65), ("status", "Status", 160)]:
        tabelle.heading(name, text=titel)
        tabelle.column(name, width=breite, minwidth=breite, stretch=False)
    vertikal = ttk.Scrollbar(tabellenrahmen, orient="vertical", command=tabelle.yview)
    horizontal = ttk.Scrollbar(tabellenrahmen, orient="horizontal", command=tabelle.xview)
    tabelle.configure(yscrollcommand=vertikal.set, xscrollcommand=horizontal.set)
    tabelle.grid(row=0, column=0, sticky="nsew")
    vertikal.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")

    def zeige():
        try:
            tag = date.fromisoformat(stichtag.get().strip())
            ergebnis = berechne(daten, tag)
        except ValueError as error:
            meldung.config(text=f"Eingabe prüfen: {error}")
            return
        studium = daten["studiengang"]
        meldung.config(text="")
        erworben = "unbekannt" if ergebnis["erworbene_ects"] is None else f"{ergebnis['erworbene_ects']:g}"
        gesamt = "nicht angegeben" if studium["gesamt_ects"] is None else f"{studium['gesamt_ects']:g}"
        fortschritt = f"{erworben} von {gesamt} ECTS"
        if ergebnis["erworbene_ects"] is not None and studium["gesamt_ects"] is not None:
            prozent = f"{100 * ergebnis['erworbene_ects'] / studium['gesamt_ects']:.1f}".replace(".", ",")
            fortschritt += f"\n{prozent} %"
        werte["Studienfortschritt"].config(text=fortschritt)
        note = ergebnis["notenschnitt"]
        schnitt = "nicht berechenbar" if note is None else f"{note:.2f}".replace(".", ",")
        ziel = f"{studium['zielnote']:.1f}".replace(".", ",")
        werte["Notenziel"].config(text=f"Ungewichteter Schnitt: {schnitt}\nZiel: {ziel} oder besser")
        zeittext = ergebnis["zeitstatus"]
        if ergebnis["soll_ects"] is None:
            zeittext += "\n" + "; ".join(ergebnis["zeitplan_hinweise"])
        else:
            abweichung = f"{ergebnis['abweichung_ects']:+.1f}".replace(".", ",")
            zeittext += f"\nAbweichung: {abweichung} ECTS"
        if ergebnis["zieldatum"] is not None:
            zeittext += f"\nGeplanter Abschluss: {ergebnis['zieldatum']:%d.%m.%Y}"
        werte["Zeitplan"].config(text=zeittext)
        tabelle.delete(*tabelle.get_children())
        for modul in ergebnis["module"]:
            ects = "" if modul["ects"] is None else f"{modul['ects']:g}"
            leistungen = modul["pruefungsleistungen"]
            if len(leistungen) == 1:
                pruefung = leistungen[0]
                note = "" if pruefung["note"] is None else f"{pruefung['note']:.1f}".replace(".", ",")
                tabelle.insert("", "end", text=modul["titel"], values=(ects, note, pruefung["status"].replace("_", " ")))
            else:
                parent = tabelle.insert("", "end", text=modul["titel"], values=(ects, "", f"{len(leistungen)} Kurse"), open=True)
                for pruefung in leistungen:
                    note = "" if pruefung["note"] is None else f"{pruefung['note']:.1f}".replace(".", ",")
                    tabelle.insert(parent, "end", text=pruefung["name"], values=("", note, pruefung["status"].replace("_", " ")))

    aktualisieren.config(command=zeige)
    stichtag.bind("<Return>", lambda event: zeige())
    zeige()
    return {"stichtag": stichtag, "button": aktualisieren, "meldung": meldung, "fortschritt": werte["Studienfortschritt"], "zeitplan": werte["Zeitplan"], "notenziel": werte["Notenziel"], "tabelle": tabelle}


if __name__ == "__main__":
    try:
        daten = lade_daten()
    except (OSError, ValueError) as error:
        raise SystemExit(f"Studiendaten konnten nicht geladen werden: {error}")
    root = tk.Tk()
    baue_fenster(root, daten)
    root.mainloop()
