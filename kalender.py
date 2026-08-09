import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, QLabel,
    QDialog, QComboBox, QDialogButtonBox, QMessageBox, QDateEdit, QCheckBox, QLineEdit,
    QToolButton
)
from PyQt5.QtGui import QIcon
from modern_theme import karte, deutsche_buttons
from PyQt5.QtCore import QDate, QTimer
from PyQt5.QtGui import QTextCharFormat, QColor, QBrush, QFont, QDoubleValidator


class KalenderWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db

        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(18, 18, 18, 18)
        aussen.setSpacing(14)

        self.kalender = QCalendarWidget()
        self.kalender.setGridVisible(False)
        self.kalender.setVerticalHeaderFormat(QCalendarWidget.ISOWeekNumbers)
        self.kalender.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self.kalender.clicked.connect(self.tag_geklickt)

        self.style_kalender()

        self.status_label = QLabel("Klicke auf einen Tag, um Rufbereitschaft einzutragen.")
        self.status_label.setObjectName("hinweis")

        legende_titel = QLabel("Legende")
        legende_titel.setObjectName("kartentitel")

        self.legende_layout = QVBoxLayout()
        self.legende_layout.setSpacing(6)

        self.legende_widget = karte(legende_titel, self.legende_layout)

        aussen.addWidget(karte(self.kalender, self.status_label))
        aussen.addWidget(self.legende_widget)

        self.mitarbeiter_liste = []
        self.mitarbeiter_farben = {}
        self.eintraege = {}

        self.lade_alle_eintraege()

    def lade_mitarbeiter_daten(self):
        """Mitarbeiter inkl. Farben neu aus der DB holen.

        Muss vor jeder Neudarstellung laufen, damit im Mitarbeiter-Tab angelegte
        oder geänderte Personen ohne Neustart im Kalender auftauchen.
        """
        self.mitarbeiter_liste = self.db.lade_mitarbeiter()

        # Dict: mitarbeiter_id -> Farbe (hex string)
        self.mitarbeiter_farben = {}
        for m in self.mitarbeiter_liste:
            farbe = m.get("mitarbeiter_farbe")
            if farbe and isinstance(farbe, str):
                self.mitarbeiter_farben[m["mitarbeiter_id"]] = farbe
            else:
                self.mitarbeiter_farben[m["mitarbeiter_id"]] = "#FFFFFF"  # default weiß

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

            # Farbfläche als kleiner Chip, Text daneben in normaler Schriftfarbe
            punkt = QLabel()
            punkt.setFixedSize(16, 16)
            punkt.setStyleSheet(
                f"background-color: {gemischte_farbe.name()};"
                "border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;"
            )

            beschriftung = QLabel(", ".join(namen))

            zeile = QHBoxLayout()
            zeile.setSpacing(10)
            zeile.addWidget(punkt)
            zeile.addWidget(beschriftung)
            zeile.addStretch()

            behaelter = QWidget()
            behaelter.setObjectName("transparent")
            behaelter.setLayout(zeile)
            self.legende_layout.addWidget(behaelter)

        # Legende unsichtbar machen, wenn keine Kombinationen vorliegen
        self.legende_widget.setVisible(bool(kombinationen))
    def style_kalender(self):
        self.kalender.setStyleSheet("""
            QCalendarWidget {
                background-color: #FFFFFF;
                border: none;
            }

            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E4E8EF;
                padding: 2px;
            }

            QCalendarWidget QToolButton {
                height: 30px;
                margin: 3px;
                padding: 4px 12px;
                color: #1F2937;
                background-color: transparent;
                border: none;
                border-radius: 7px;
                font-weight: 600;
            }

            QCalendarWidget QToolButton:hover {
                background-color: #EEF2F7;
            }

            QCalendarWidget QToolButton:pressed {
                background-color: #E0E7F0;
            }

            QCalendarWidget QMenu {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #E5E7EB;
            }

            QCalendarWidget QSpinBox {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 4px;
            }

            QCalendarWidget QAbstractItemView {
                background-color: #FFFFFF;
                alternate-background-color: #FFFFFF;
                color: #1F2937;
                selection-background-color: #2563EB;
                selection-color: #FFFFFF;
                outline: 0;
                border: none;
                font-size: 14px;
            }

            QCalendarWidget QAbstractItemView:disabled {
                color: #9CA3AF;
            }

            QCalendarWidget QHeaderView::section {
                background-color: #FFFFFF;
                color: #6B7280;
                padding: 8px;
                border: none;
                font-weight: 600;
                font-size: 12px;
            }
        """)

        # Die grünen System-Icons der Navigationspfeile passen nicht ins Theme;
        # durch schlichte Textpfeile ersetzen.
        for name, zeichen in (("qt_calendar_prevmonth", "‹"), ("qt_calendar_nextmonth", "›")):
            knopf = self.kalender.findChild(QToolButton, name)
            if knopf is not None:
                knopf.setIcon(QIcon())
                knopf.setText(zeichen)
                knopf.setStyleSheet("font-size: 20px; padding: 0 14px;")

        werktag_format = QTextCharFormat()
        werktag_format.setForeground(QBrush(QColor("#111827")))
        werktag_format.setFontWeight(QFont.DemiBold)

        wochenende_format = QTextCharFormat()
        wochenende_format.setForeground(QBrush(QColor("#B91C1C")))
        wochenende_format.setFontWeight(QFont.Bold)

        for tag in range(1, 6):
            self.kalender.setWeekdayTextFormat(tag, werktag_format)

        self.kalender.setWeekdayTextFormat(6, wochenende_format)
        self.kalender.setWeekdayTextFormat(7, wochenende_format)
    def kontrast_textfarbe(self, farbe):
        helligkeit = (farbe.red() * 299 + farbe.green() * 587 + farbe.blue() * 114) / 1000

        if helligkeit > 155:
            return QColor("#111827")

        return QColor("#FFFFFF")
    def lade_alle_eintraege(self):
        self.lade_mitarbeiter_daten()
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
            # Der Zeitraum ist im Dialog bereits validiert.
            dates = []
            current_date = mitarbeiter["start_datum"]
            while current_date <= mitarbeiter["end_datum"]:
                dates.append(current_date)
                current_date = current_date.addDays(1)

            try:
                for d in dates:
                    datum_str = d.toString("yyyy-MM-dd")
                    self.db.fuege_kalender_eintrag_hinzu(
                        datum_str, mitarbeiter["mitarbeiter_id"], mitarbeiter["individual_point"]
                    )
                    if mitarbeiter["mitarbeiter2_id"]:
                        self.db.fuege_kalender_eintrag_hinzu(
                            datum_str, mitarbeiter["mitarbeiter2_id"], mitarbeiter["individual_point"]
                        )
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Eintrag konnte nicht gespeichert werden:\n{e}")

            self.lade_alle_eintraege()
            anzahl = len(dates)
            self.status_label.setText(
                f"{anzahl} Tag{'e' if anzahl != 1 else ''} eingetragen "
                f"({dates[0].toString('dd.MM.yyyy')} – {dates[-1].toString('dd.MM.yyyy')})"
            )

    def update_tag_formatierung(self, datum):
        try:
            formatierung = QTextCharFormat()

            if datum in self.eintraege and self.eintraege[datum]:
                mitarbeiter_ids = [e["mitarbeiter_id"] for e in self.eintraege[datum]]
                farben = [self.mitarbeiter_farben.get(mid, "#FFFFFF") for mid in mitarbeiter_ids]
                farben_valid = [QColor(f) for f in farben if QColor(f).isValid()]

                namen = [e["name"] for e in self.eintraege[datum]]
                tooltip_text = "Mitarbeiter an diesem Tag:\n" + "\n".join(namen)
                formatierung.setToolTip(tooltip_text)

                if len(farben_valid) == 0:
                    hintergrund = QColor("#FFFFFF")

                elif len(farben_valid) == 1:
                    hintergrund = farben_valid[0]

                else:
                    total_r = 0
                    total_g = 0
                    total_b = 0

                    for qcolor in farben_valid:
                        total_r += qcolor.red()
                        total_g += qcolor.green()
                        total_b += qcolor.blue()

                    count = len(farben_valid)
                    hintergrund = QColor(
                        total_r // count,
                        total_g // count,
                        total_b // count
                    )

                formatierung.setBackground(QBrush(hintergrund))
                formatierung.setForeground(QBrush(self.kontrast_textfarbe(hintergrund)))
                formatierung.setFontWeight(QFont.Bold)

            else:
                formatierung.setBackground(QBrush(QColor("#FFFFFF")))
                formatierung.setForeground(QBrush(QColor("#111827")))
                formatierung.setToolTip("")

            self.kalender.setDateTextFormat(datum, formatierung)

        except Exception as e:
            print(f"Fehler bei update_tag_formatierung: {e}")


class EintragDialog(QDialog):
    def __init__(self, datum, mitarbeiter_liste, db, kalender_widget):
        super().__init__()
        self.kalender_widget = kalender_widget
        self.setWindowTitle(f"Rufbereitschaft am {datum.toString('dd.MM.yyyy')}")
        self.setMinimumWidth(360)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(24, 24, 24, 24)
        self.layout().setSpacing(10)
        self.start_datum = QDateEdit(datum)
        self.start_datum.setCalendarPopup(True)
        self.end_datum = QDateEdit(datum)
        self.end_datum.setCalendarPopup(True)
        self.individual_point = QLineEdit()
        self.individual_point.setPlaceholderText("leer = automatische Punkte")
        self.individual_point.setToolTip(
            "Optional. Überschreibt die automatisch berechneten Tagespunkte.\n"
            "Nur Zahlen, maximal zwei Nachkommastellen (z. B. 1,5)."
        )
        # Nur Zahlen zulassen; das Locale-Format des Validators akzeptiert Komma und Punkt.
        validator = QDoubleValidator(0.0, 999.0, 2, self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.individual_point.setValidator(validator)
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
        self.layout().addWidget(QLabel("Individuelle Punkte"))
        self.layout().addWidget(self.individual_point)
        self.checkbox.stateChanged.connect(self.toggle_extra_field)

        # Das zweite Combo erst als None setzen
        self.mitarbeiter_combo2 = None

        buttons = deutsche_buttons(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        datum_str = datum.toString("yyyy-MM-dd")

        if self.checkbox.isChecked():
            self.layout().addWidget(self.mitarbeiter_combo)

        eintraege = db.get_selected_kalender(datum_str, None)  # alle an dem Tag holen
        if eintraege:
            if len(eintraege) >= 1:
                self.individual_point.setText(str(eintraege[0].get("individuelle_punkte", "")))
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

    def parse_individuelle_punkte(self):
        """Eingabe der individuellen Punkte als Zahl zurückgeben.

        Rückgabe: (wert, fehlermeldung). Leere Eingabe bedeutet 0 = automatische
        Berechnung. Bei ungültiger Eingabe ist der Wert None.
        """
        text = self.individual_point.text().strip().replace(",", ".")
        if not text:
            return 0, None

        try:
            wert = float(text)
        except ValueError:
            return None, "Individuelle Punkte müssen eine Zahl sein (z. B. 1 oder 1,5)."

        if wert < 0:
            return None, "Individuelle Punkte dürfen nicht negativ sein."

        return wert, None

    def accept(self):
        punkte, fehler = self.parse_individuelle_punkte()
        if fehler:
            QMessageBox.warning(self, "Ungültige Eingabe", fehler)
            self.individual_point.setFocus()
            self.individual_point.selectAll()
            return

        if self.start_datum.date() > self.end_datum.date():
            QMessageBox.warning(
                self, "Ungültiger Zeitraum",
                "Das Datum unter „Von“ muss vor dem Datum unter „Bis“ liegen."
            )
            self.start_datum.setFocus()
            return

        if self.mitarbeiter_combo2 and self.checkbox.isChecked():
            if self.mitarbeiter_combo2.currentData() == self.mitarbeiter_combo.currentData():
                QMessageBox.warning(
                    self, "Ungültige Auswahl",
                    "Für einen geteilten Tag müssen zwei verschiedene Mitarbeiter gewählt werden."
                )
                return

        super().accept()

    def get_data(self):
        punkte, _ = self.parse_individuelle_punkte()
        return {
            "mitarbeiter_id": self.mitarbeiter_combo.currentData(),
            "name": self.mitarbeiter_combo.currentText(),
            "start_datum": self.start_datum.date(),
            "end_datum": self.end_datum.date(),
            "individual_point": punkte if punkte is not None else 0,
            "mitarbeiter2_id": self.mitarbeiter_combo2.currentData()
                if (self.mitarbeiter_combo2 and self.checkbox.isChecked()) else None
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

