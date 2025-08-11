import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QCalendarWidget, QLabel,
    QDialog, QComboBox, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QTextCharFormat, QColor


class KalenderDB:
    def __init__(self, db_datei='kalender.db'):
        self.conn = sqlite3.connect(db_datei)
        self.conn.row_factory = sqlite3.Row  # Für dict-ähnliche Ergebnisse
        self.cursor = self.conn.cursor()

        # Foreign Keys in SQLite aktivieren
        self.cursor.execute("PRAGMA foreign_keys = ON;")

        # Tabellen anlegen, falls nicht existieren
        self.erstelle_tabellen()

    def erstelle_tabellen(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS mitarbeiter (
            mitarbeiter_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mitarbeiter_vorname TEXT,
            mitarbeiter_nachname TEXT,
            mitarbeiter_eintritt TEXT,
            mitarbeiter_farbe TEXT DEFAULT '#ffffff'
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS kalender_mitarbeiter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT NOT NULL,
            mitarbeiter_id INTEGER NOT NULL,
            erstellt_am TEXT DEFAULT CURRENT_TIMESTAMP,
            aktualisiert_am TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mitarbeiter_id) REFERENCES mitarbeiter(mitarbeiter_id)
        )
        """)
        self.conn.commit()

    def lade_mitarbeiter(self):
        self.cursor.execute("SELECT mitarbeiter_id, mitarbeiter_vorname, mitarbeiter_nachname, mitarbeiter_farbe FROM mitarbeiter")
        return [dict(row) for row in self.cursor.fetchall()]

    def lade_kalender_eintraege(self, datum_str):
        # datum_str im Format 'YYYY-MM-DD'
        self.cursor.execute("SELECT id, mitarbeiter_id FROM kalender_mitarbeiter WHERE datum = ?", (datum_str,))
        return [dict(row) for row in self.cursor.fetchall()]

    def fuege_kalender_eintrag_hinzu(self, datum_str, mitarbeiter_id):
        self.cursor.execute(
            "INSERT INTO kalender_mitarbeiter (datum, mitarbeiter_id) VALUES (?, ?)",
            (datum_str, mitarbeiter_id)
        )
        self.conn.commit()

    def loesche_kalender_eintrag(self, kalender_id):
        self.cursor.execute("DELETE FROM kalender_mitarbeiter WHERE id = ?", (kalender_id,))
        self.conn.commit()

    def schliesse_verbindung(self):
        self.cursor.close()
        self.conn.close()


class KalenderWidget(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setLayout(QVBoxLayout())

        self.kalender = QCalendarWidget()
        self.kalender.setGridVisible(True)
        self.kalender.clicked.connect(self.tag_geklickt)
        self.layout().addWidget(self.kalender)

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

    def aktualisiere_alle_farbungen(self):
        for datum in self.eintraege:
            self.update_tag_formatierung(datum)

    def tag_geklickt(self, datum):
        self.status_label.setText(f"Ausgewählt: {datum.toString('dd.MM.yyyy')}")
        dialog = EintragDialog(datum, self.mitarbeiter_liste)

        if dialog.exec_():
            mitarbeiter = dialog.get_data()
            if not mitarbeiter["mitarbeiter_id"]:
                QMessageBox.warning(self, "Fehler", "Ungültiger Mitarbeiter ausgewählt.")
                return

            eintraege_heute = self.eintraege.get(datum, [])
            if any(e["mitarbeiter_id"] == mitarbeiter["mitarbeiter_id"] for e in eintraege_heute):
                QMessageBox.information(self, "Hinweis", f"{mitarbeiter['name']} ist bereits eingetragen.")
                return

            datum_str = datum.toString("yyyy-MM-dd")
            self.db.fuege_kalender_eintrag_hinzu(datum_str, mitarbeiter["mitarbeiter_id"])
            self.lade_alle_eintraege()

    def update_tag_formatierung(self, datum):
        try:
            formatierung = QTextCharFormat()

            if datum in self.eintraege and self.eintraege[datum]:
                erster_mitarbeiter_id = self.eintraege[datum][0]["mitarbeiter_id"]

                farbe_hex = self.mitarbeiter_farben.get(erster_mitarbeiter_id, "#FFFFFF")
                farbe = QColor(farbe_hex)
                if not farbe.isValid():
                    farbe = QColor("#FFFFFF")

                formatierung.setBackground(farbe)

                namen = [e["name"] for e in self.eintraege[datum]]
                tooltip_text = "Mitarbeiter an diesem Tag:\n" + "\n".join(namen)
                formatierung.setToolTip(tooltip_text)
            else:
                formatierung.setBackground(QColor("white"))
                formatierung.setToolTip("")

            self.kalender.setDateTextFormat(datum, formatierung)

        except Exception as e:
            print(f"Fehler bei update_tag_formatierung: {e}")


class EintragDialog(QDialog):
    def __init__(self, datum, mitarbeiter_liste):
        super().__init__()
        self.setWindowTitle(f"Mitarbeiter auswählen für {datum.toString('dd.MM.yyyy')}")
        self.setMinimumWidth(300)
        self.setLayout(QVBoxLayout())

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

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def get_data(self):
        return {
            "mitarbeiter_id": self.mitarbeiter_combo.currentData(),
            "name": self.mitarbeiter_combo.currentText()
        }
