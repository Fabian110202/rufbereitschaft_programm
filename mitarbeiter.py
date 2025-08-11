import os
import traceback
import faulthandler

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QDialog,
    QLineEdit, QFormLayout, QDialogButtonBox,
    QColorDialog, QFrame, QDateEdit
)
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QHeaderView


# faulthandler direkt aktivieren (C-Level Tracebacks bei Crash)



class MitarbeiterWidget(QWidget):
    def __init__(self, datenbank):
        super().__init__()
        self.db = datenbank
        self.setLayout(QVBoxLayout())

        # Buttons
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("Hinzufügen")
        self.btn_edit = QPushButton("Bearbeiten")
        self.btn_delete = QPushButton("Löschen")

        self.btn_add.clicked.connect(self.hinzufuegen)
        self.btn_edit.clicked.connect(self.bearbeiten)
        self.btn_delete.clicked.connect(self.loeschen)

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)

        self.layout().addLayout(button_layout)

        # Tabelle
        self.tabelle = QTableWidget()
        self.tabelle.setColumnCount(4)
        self.tabelle.setHorizontalHeaderLabels(["ID", "Vorname", "Nachname", "Eintritt"])
        self.layout().addWidget(self.tabelle)

        # Mitarbeiter laden
        self.lade_mitarbeiter()

    def lade_mitarbeiter(self):
        self.daten = self.db.lade_mitarbeiter()
        self.aktualisiere_tabelle()

    def aktualisiere_tabelle(self):
        log_path = os.path.join(os.getcwd(), "debug_mitarbeiter.log")
        with open(log_path, "a", encoding="utf-8") as log:
            log.write("=== aktualisiere_tabelle START ===\n")
            try:
                self.tabelle.clearContents()
                self.tabelle.setRowCount(0)

                log.write(f"Anzahl datensätze: {len(self.daten)}\n")
                for i, mitarbeiter in enumerate(self.daten):
                    log.write(f"--- Datensatz {i} ---\n")
                    for k, v in mitarbeiter.items():
                        try:
                            log.write(f"  {k} -> repr: {repr(v)} | type: {type(v)}\n")
                        except Exception:
                            log.write(f"  {k} -> (could not repr) | type: {type(v)}\n")

                self.tabelle.setRowCount(len(self.daten))
                for row, mitarbeiter in enumerate(self.daten):
                    # ID
                    id_val = ""
                    try:
                        id_val = str(mitarbeiter.get("mitarbeiter_id", "") or "")
                    except Exception as e:
                        log.write(f"ID conversion error row {row}: {e}\n")

                    # Vorname
                    vorname_val = mitarbeiter.get("mitarbeiter_vorname") or ""

                    # Nachname
                    nachname_val = mitarbeiter.get("mitarbeiter_nachname") or ""

                    # Eintrittsdatum sicher formatieren
                    eintritt = mitarbeiter.get("mitarbeiter_eintritt")
                    try:
                        if hasattr(eintritt, "strftime"):  # datetime.date/datetime
                            eintritt_val = eintritt.strftime("%Y-%m-%d")
                        elif isinstance(eintritt, QDate):
                            eintritt_val = eintritt.toString("yyyy-MM-dd")
                        elif isinstance(eintritt, str):
                            eintritt_val = eintritt.strip()
                        else:
                            eintritt_val = ""
                    except Exception as e:
                        eintritt_val = ""
                        log.write(f"Datum format error row {row}: {e}\n")

                    # Items erstellen (nie None rein)
                    try:
                        id_item = QTableWidgetItem(id_val)
                        vorname_item = QTableWidgetItem(vorname_val)
                        nachname_item = QTableWidgetItem(nachname_val)
                        eintritt_item = QTableWidgetItem(eintritt_val)
                    except Exception as e:
                        log.write(f"QTableWidgetItem creation error row {row}: {e}\n")
                        continue


                    # Farbe setzen — falls Farbe gültig ist
                    farbwert = mitarbeiter.get("mitarbeiter_farbe")
                    if isinstance(farbwert, str):

                        farbwert = farbwert.strip()
                        if farbwert.startswith("#") and len(farbwert) == 7:
                            farbe = QColor(farbwert)
                            if farbe.isValid():
                                for item in [id_item, vorname_item, nachname_item, eintritt_item]:
                                    item.setBackground(farbe)

                    # Items in Tabelle setzen
                    try:
                        self.tabelle.setItem(row, 0, id_item)
                        self.tabelle.setItem(row, 1, vorname_item)
                        self.tabelle.setItem(row, 2, nachname_item)
                        self.tabelle.setItem(row, 3, eintritt_item)
                    except Exception as e:
                        log.write(f"setItem error row {row}: {e}\n")

                log.write("=== aktualisiere_tabelle ENDE erfolgreich ===\n")
            except Exception as e:
                log.write("!!! Ausnahme in aktualisiere_tabelle !!!\n")
                log.write(traceback.format_exc())
                log.write("=== aktualisiere_tabelle ENDE mit Exception ===\n")

    def hinzufuegen(self):
        dialog = MitarbeiterDialog()
        if dialog.exec_():
            daten = dialog.get_data()
            try:
                self.db.fuege_mitarbeiter_hinzu(
                    daten["vorname"],
                    daten["nachname"],
                    daten["eintritt"],
                    daten["farbe"]
                )
            except Exception:
                import traceback
                traceback.print_exc()
            self.lade_mitarbeiter()

    def bearbeiten(self):
        zeile = self.tabelle.currentRow()
        if zeile < 0:
            return
        daten_alt = self.daten[zeile]

        dialog = MitarbeiterDialog(daten_alt)
        if dialog.exec_():
            daten = dialog.get_data()
            try:
                self.db.aktualisiere_mitarbeiter(
                    daten_alt["mitarbeiter_id"],
                    daten["vorname"],
                    daten["nachname"],
                    daten["eintritt"],
                    daten["farbe"]
                )
            except Exception:
                import traceback
                traceback.print_exc()
            self.lade_mitarbeiter()

    def loeschen(self):
        zeile = self.tabelle.currentRow()
        if zeile < 0:
            return
        mitarbeiter_id = self.daten[zeile]["mitarbeiter_id"]
        self.db.loesche_mitarbeiter(mitarbeiter_id)
        self.lade_mitarbeiter()


class MitarbeiterDialog(QDialog):
    def __init__(self, daten=None):
        super().__init__()
        self.setWindowTitle("Mitarbeiter erfassen")
        self.setLayout(QFormLayout())

        self.vorname = QLineEdit()
        self.nachname = QLineEdit()
        self.eintritt = QDateEdit()
        self.eintritt.setCalendarPopup(True)
        self.eintritt.setDate(QDate.currentDate())

        # Farbe-Initialisierung und Color Picker Button mit Vorschau
        self.farbe = QColor("#ffffff")  # Standardfarbe
        self.btn_farbe = QPushButton("Farbe wählen")
        self.btn_farbe.clicked.connect(self.waehle_farbe)

        self.farbe_preview = QFrame()
        self.farbe_preview.setFixedSize(40, 20)
        self.farbe_preview.setStyleSheet(f"background-color: {self.farbe.name()}; border: 1px solid black;")

        farbe_layout = QHBoxLayout()
        farbe_layout.addWidget(self.btn_farbe)
        farbe_layout.addWidget(self.farbe_preview)

        self.layout().addRow("Vorname:", self.vorname)
        self.layout().addRow("Nachname:", self.nachname)
        self.layout().addRow("Eintritt:", self.eintritt)
        self.layout().addRow("Farbe:", farbe_layout)

        if daten:
            self.vorname.setText(daten.get("mitarbeiter_vorname", ""))
            self.nachname.setText(daten.get("mitarbeiter_nachname", ""))
            if daten.get("mitarbeiter_eintritt"):
                eintritt = daten["mitarbeiter_eintritt"]
                if isinstance(eintritt, QDate):
                    self.eintritt.setDate(eintritt)
                elif hasattr(eintritt, "year"):  # datetime.date oder datetime.datetime
                    self.eintritt.setDate(QDate(eintritt.year, eintritt.month, eintritt.day))
                elif isinstance(eintritt, str):
                    try:
                        y, m, d = map(int, eintritt.split("-"))
                        self.eintritt.setDate(QDate(y, m, d))
                    except ValueError:
                        pass
            if "mitarbeiter_farbe" in daten and daten["mitarbeiter_farbe"]:
                print("Dialog Farbe geladen:", daten["mitarbeiter_farbe"])
                self.farbe = QColor(daten["mitarbeiter_farbe"])
                self.farbe_preview.setStyleSheet(f"background-color: {self.farbe.name()}; border: 1px solid black;")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def waehle_farbe(self):
        farbe = QColorDialog.getColor(self.farbe, self, "Farbe auswählen")
        if farbe.isValid():
            self.farbe = farbe
            self.farbe_preview.setStyleSheet(f"background-color: {self.farbe.name()}; border: 1px solid black;")

    def get_data(self):
        return {
            "vorname": self.vorname.text(),
            "nachname": self.nachname.text(),
            "eintritt": self.eintritt.date().toPyDate(),
            "farbe": self.farbe.name()
        }
