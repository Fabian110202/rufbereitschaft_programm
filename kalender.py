import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QCalendarWidget, QLabel,
    QDialog, QComboBox, QDialogButtonBox, QMessageBox, QDateEdit, QCheckBox, QLineEdit
)
from PyQt5.QtCore import QDate, QTimer
from PyQt5.QtGui import QTextCharFormat, QColor, QLinearGradient, QBrush


class KalenderWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setLayout(QVBoxLayout())

        self.kalender = QCalendarWidget()
        self.kalender.setGridVisible(True)
        self.kalender.clicked.connect(self.tag_geklickt)
        self.layout().addWidget(self.kalender)
        self.legende_widget = QWidget()
        self.legende_layout = QVBoxLayout()
        self.legende_widget.setLayout(self.legende_layout)
        self.layout().addWidget(self.legende_widget)

        self.status_label = QLabel("Wähle ein Datum.")
        self.layout().addWidget(self.status_label)

        # Mitarbeiter laden inkl. Farbe
        self.mitarbeiter_liste = self.db.lade_mitarbeiter()

        # Dict: mitarbeiter_id -> Farbe (hex string)
        self.mitarbeiter_farben = {}
        for m in self.mitarbeiter_liste:
            farbe = m.get("mitarbeiter_farbe")
            if farbe and isinstance(farbe, str):
                self.mitarbeiter_farben[m["mitarbeiter_id"]] = farbe
            else:
                self.mitarbeiter_farben[m["mitarbeiter_id"]] = "#FFFFFF"  # default weiß

        self.eintraege = {}

        self.lade_alle_eintraege()

    def aktualisiere_legende(self):
        # Alle vorhandenen Widgets aus dem Legenden-Layout entfernen
        while self.legende_layout.count():
            item = self.legende_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Kombinationen von Mitarbeitern finden
        kombinationen = {}
        for eintraege_tag in self.eintraege.values():
            mitarbeiter_ids = tuple(sorted([e["mitarbeiter_id"] for e in eintraege_tag]))
            if mitarbeiter_ids not in kombinationen:
                namen = [e["name"] for e in eintraege_tag]
                kombinationen[mitarbeiter_ids] = namen

        # Legende für jede Kombination erstellen
        for ids, namen in kombinationen.items():
            farben_valid = [QColor(self.mitarbeiter_farben.get(mid)) for mid in ids if
                            QColor(self.mitarbeiter_farben.get(mid)).isValid()]

            gemischte_farbe = QColor("white")
            if len(farben_valid) == 1:
                gemischte_farbe = farben_valid[0]
            elif len(farben_valid) > 1:
                total_r, total_g, total_b = 0, 0, 0
                for qcolor in farben_valid:
                    total_r += qcolor.red()
                    total_g += qcolor.green()
                    total_b += qcolor.blue()
                count = len(farben_valid)
                gemischte_farbe = QColor(total_r // count, total_g // count, total_b // count)

            legenden_eintrag = QLabel()
            style = f"background-color: {gemischte_farbe.name()}; border: 1px solid black;"
            legenden_eintrag.setStyleSheet(style)
            legenden_eintrag.setText(f"  {', '.join(namen)}")
            self.legende_layout.addWidget(legenden_eintrag)

        # Legende unsichtbar machen, wenn keine Kombinationen vorliegen
        self.legende_widget.setVisible(bool(kombinationen))
    def lade_alle_eintraege(self):
        self.eintraege.clear()
        # Korrigierte SQL mit String-Verkettung in SQLite
        self.db.cursor.execute("""
            SELECT k.id,
                   k.datum,
                   k.mitarbeiter_id,
                   m.mitarbeiter_vorname || ' ' || m.mitarbeiter_nachname AS name
            FROM kalender_mitarbeiter k
            JOIN mitarbeiter m ON k.mitarbeiter_id = m.mitarbeiter_id
        """)
        daten = self.db.cursor.fetchall()

        for eintrag in daten:
            datum_str = eintrag["datum"]
            # Datum als QDate parsen (aus String 'YYYY-MM-DD')
            try:
                datum_dt = datetime.strptime(datum_str, "%Y-%m-%d").date()
                qdatum = QDate(datum_dt.year, datum_dt.month, datum_dt.day)
            except Exception as e:
                print(f"Fehler beim Parsen des Datums '{datum_str}': {e}")
                continue

            if qdatum not in self.eintraege:
                self.eintraege[qdatum] = []

            self.eintraege[qdatum].append({
                "kalender_id": eintrag["id"],
                "mitarbeiter_id": int(eintrag["mitarbeiter_id"]),
                "name": eintrag["name"]
            })

        self.aktualisiere_alle_farbungen()
        self.aktualisiere_legende()

    def aktualisiere_alle_farbungen(self):
        self.kalender.setDateTextFormat(QDate(), QTextCharFormat())  # Alle Formate zurücksetzen
        for datum in self.eintraege:
            self.update_tag_formatierung(datum)

    def tag_geklickt(self, datum):
        self.status_label.setText(f"Ausgewählt: {datum.toString('dd.MM.yyyy')}")
        dialog = EintragDialog(datum, self.mitarbeiter_liste, self.db, kalender_widget=self)

        if dialog.exec_():
            mitarbeiter = dialog.get_data()
            if not mitarbeiter["mitarbeiter_id"]:
                QMessageBox.warning(self, "Fehler", "Ungültiger Mitarbeiter ausgewählt.")
                return

            eintraege_heute = self.eintraege.get(datum, [])
            if any(e["mitarbeiter_id"] == mitarbeiter["mitarbeiter_id"] for e in eintraege_heute):
                QMessageBox.information(self, "Hinweis", f"{mitarbeiter['name']} ist bereits eingetragen.")
                return
            if mitarbeiter["start_datum"] > mitarbeiter["end_datum"]:
                QMessageBox.information(self, "Hinweis", "Datum von vor dem Datum bis liegen")

            dates =[]
            current_date = mitarbeiter["start_datum"]

            while current_date <=  mitarbeiter["end_datum"]:
                dates.append(current_date)
                current_date = current_date.addDays(1)

            for d in dates:
                if not mitarbeiter["mitarbeiter2_id"]:
                    self.db.fuege_kalender_eintrag_hinzu(d.toString("yyyy-MM-dd"), mitarbeiter["mitarbeiter_id"])
                else:
                    self.db.fuege_kalender_eintrag_hinzu(d.toString("yyyy-MM-dd"), mitarbeiter["mitarbeiter_id"])
                    self.db.fuege_kalender_eintrag_hinzu(d.toString("yyyy-MM-dd"), mitarbeiter["mitarbeiter2_id"])
            self.lade_alle_eintraege()

    def update_tag_formatierung(self, datum):
        try:
            formatierung = QTextCharFormat()

            if datum in self.eintraege and self.eintraege[datum]:
                mitarbeiter_ids = [e["mitarbeiter_id"] for e in self.eintraege[datum]]
                farben = [self.mitarbeiter_farben.get(mid, "#FFFFFF") for mid in mitarbeiter_ids]

                # Gültigkeit der Farben prüfen und ggf. auf Weiß zurücksetzen
                farben_valid = [QColor(f) for f in farben if QColor(f).isValid()]

                # Tooltip mit allen Namen
                namen = [e["name"] for e in self.eintraege[datum]]
                tooltip_text = "Mitarbeiter an diesem Tag:\n" + "\n".join(namen)
                formatierung.setToolTip(tooltip_text)

                if len(farben_valid) == 0:
                    # Keine gültigen Farben gefunden
                    formatierung.setBackground(QColor("white"))

                elif len(farben_valid) == 1:
                    # Nur eine Farbe, diese direkt verwenden
                    formatierung.setBackground(farben_valid[0])

                else:
                    # Mehrere Farben: RGB-Werte mischen
                    total_r, total_g, total_b = 0, 0, 0
                    for qcolor in farben_valid:
                        total_r += qcolor.red()
                        total_g += qcolor.green()
                        total_b += qcolor.blue()

                    count = len(farben_valid)
                    avg_r = total_r // count
                    avg_g = total_g // count
                    avg_b = total_b // count

                    mixed_color = QColor(avg_r, avg_g, avg_b)
                    formatierung.setBackground(mixed_color)

            else:
                # Standard-Formatierung, wenn keine Einträge vorhanden sind
                formatierung.setBackground(QColor("white"))
                formatierung.setToolTip("")

            self.kalender.setDateTextFormat(datum, formatierung)

        except Exception as e:
            print(f"Fehler bei update_tag_formatierung: {e}")


class EintragDialog(QDialog):
    def __init__(self, datum, mitarbeiter_liste, db, kalender_widget):
        super().__init__()
        self.kalender_widget = kalender_widget
        self.setWindowTitle(f"Mitarbeiter auswählen für {datum.toString('dd.MM.yyyy')}")
        self.setMinimumWidth(300)
        self.setLayout(QVBoxLayout())
        self.start_datum = QDateEdit(datum)
        self.start_datum.setCalendarPopup(True)
        self.end_datum = QDateEdit(datum)
        self.end_datum.setCalendarPopup(True)
        self.db = db

        self.mitarbeiter_combo = QComboBox()
        for m in mitarbeiter_liste:
            try:
                if m["mitarbeiter_id"] is not None:
                    name = f"{m['mitarbeiter_vorname']} {m['mitarbeiter_nachname']}"
                    self.mitarbeiter_combo.addItem(name, m["mitarbeiter_id"])
            except Exception as e:
                print(f"Fehler beim Hinzufügen von Mitarbeiter: {e}")

        self.layout().addWidget(QLabel("Mitarbeiter:"))
        self.layout().addWidget(self.mitarbeiter_combo)
        self.layout().addWidget(QLabel("Von:"))
        self.layout().addWidget(self.start_datum)
        self.layout().addWidget(QLabel("Bis:"))
        self.layout().addWidget(self.end_datum)
        self.checkbox = QCheckBox("Tag geteilt")
        self.checkbox.setChecked(False)
        self.layout().addWidget(self.checkbox)
        self.checkbox.stateChanged.connect(self.toggle_extra_field)

        # Das zweite Combo erst als None setzen
        self.mitarbeiter_combo2 = None

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        datum_str = datum.toString("yyyy-MM-dd")

        if self.checkbox.isChecked():
            self.layout().addWidget(self.mitarbeiter_combo)

        eintraege = db.get_selected_kalender(datum_str, None)  # alle an dem Tag holen
        if eintraege:
            if len(eintraege) >= 1:
                self.mitarbeiter_combo.setCurrentIndex(
                    self.mitarbeiter_combo.findData(eintraege[0]["mitarbeiter_id"])
                )
            if len(eintraege) >= 2:
                # Checkbox aktivieren und zweites Feld anzeigen
                self.checkbox.setChecked(True)
                self.toggle_extra_field(2)
                self.mitarbeiter_combo2.setCurrentIndex(
                    self.mitarbeiter_combo2.findData(eintraege[1]["mitarbeiter_id"])
                )

        if self.db.isExisting(datum_str):
            delete_button = buttons.addButton("Löschen", QDialogButtonBox.DestructiveRole)
            delete_button.clicked.connect(self.loesche_eintrag)

        self.layout().addWidget(buttons)

    def get_data(self):
        return {
            "mitarbeiter_id": self.mitarbeiter_combo.currentData(),
            "name": self.mitarbeiter_combo.currentText(),
            "start_datum": self.start_datum.date(),
            "end_datum": self.end_datum.date(),
            "mitarbeiter2_id": self.mitarbeiter_combo2.currentData() if self.mitarbeiter_combo2 else None
        }

    def toggle_extra_field(self, state):
        if state == 2:  # checked
            if self.mitarbeiter_combo2 is None:
                self.mitarbeiter_combo2 = QComboBox()
                for m in self.db.lade_mitarbeiter():  # oder übergebenes mitarbeiter_liste
                    if m["mitarbeiter_id"] is not None:
                        name = f"{m['mitarbeiter_vorname']} {m['mitarbeiter_nachname']}"
                        self.mitarbeiter_combo2.addItem(name, m["mitarbeiter_id"])
                self.layout().addWidget(QLabel("Mitarbeiter 2:"))
                self.layout().addWidget(self.mitarbeiter_combo2)
            self.mitarbeiter_combo2.show()
        else:
            if self.mitarbeiter_combo2:
                self.mitarbeiter_combo2.hide()

    def loesche_eintrag(self):
        mitarbeiter_id = self.mitarbeiter_combo.currentData()
        datum_str = self.start_datum.date().toString("yyyy-MM-dd")

        try:
            eintraege = self.db.get_selected_kalender(datum_str, mitarbeiter_id)

            if not eintraege:
                QMessageBox.information(self, "Info", "Kein Eintrag zum Löschen gefunden.")
                return

            reply = QMessageBox.question(
                self, "Löschen bestätigen",
                f"Eintrag von {self.mitarbeiter_combo.currentText()} am {datum_str} löschen?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                for eintrag in eintraege:
                    self.db.loesche_kalender_eintrag(eintrag["id"])

                QMessageBox.information(self, "Erfolg", "Eintrag gelöscht.")

                # Statt self.parent().lade_alle_eintraege()
                if self.kalender_widget:
                    self.kalender_widget.lade_alle_eintraege()
                    self.kalender_widget.aktualisiere_alle_farbungen()
                if not self.kalender_widget:
                    print("Warnung: Kalender-Widget nicht gesetzt")

                QTimer.singleShot(0, lambda: self.kalender_widget.lade_alle_eintraege())
                self.close()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Löschen fehlgeschlagen:\n{e}")

