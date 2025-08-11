from datetime import datetime, timedelta
from PyQt5 import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QLabel, QDateEdit, QPushButton
)
from PyQt5.QtCore import QDate

from feiertagsAPI import FeiertageAPI


class SollIstWidget(QWidget):
    def __init__(self, datenbank):
        super().__init__()
        self.db = datenbank

        self.setLayout(QVBoxLayout())

        # Filter-Layout (Start- und Enddatum)
        filter_layout = QHBoxLayout()
        self.layout().addLayout(filter_layout)

        filter_layout.addWidget(QLabel("Von:"))
        self.start_datum = QDateEdit()
        self.start_datum.setCalendarPopup(True)
        self.start_datum.setDate(QDate.currentDate().addMonths(-1))  # default: vor 1 Monat
        filter_layout.addWidget(self.start_datum)

        filter_layout.addWidget(QLabel("Bis:"))
        self.end_datum = QDateEdit()
        self.end_datum.setCalendarPopup(True)
        self.end_datum.setDate(QDate.currentDate())
        filter_layout.addWidget(self.end_datum)

        self.btn_aktualisieren = QPushButton("Aktualisieren")
        filter_layout.addWidget(self.btn_aktualisieren)

        self.tabelle = QTableWidget()
        self.layout().addWidget(self.tabelle)

        self.btn_aktualisieren.clicked.connect(self.lade_und_zeige_daten)

        # Daten direkt laden
        self.lade_und_zeige_daten()

    def ist_aktiv_im_zeitraum(self, mitarbeiter, start_dt, end_dt):
        # Mitarbeiter gilt als aktiv, wenn sein Eintrittsdatum <= Enddatum des Filters
        eintritt = mitarbeiter.get("mitarbeiter_eintritt")
        if isinstance(eintritt, str):
            eintritt = datetime.strptime(eintritt, "%Y-%m-%d").date()
        elif isinstance(eintritt, datetime):
            eintritt = eintritt.date()  # datetime -> date

        # Enddatum auf date (falls datetime)
        if isinstance(end_dt, datetime):
            end_dt = end_dt.date()

        return eintritt <= end_dt

    def tage_im_zeitraum(self, start_dt, end_dt):
        # Erzeuge Liste aller Tage im Zeitraum inkl. Enddatum
        tage = []
        aktueller_tag = start_dt
        while aktueller_tag <= end_dt:
            tage.append(aktueller_tag)
            aktueller_tag += timedelta(days=1)
        return tage

    def punkte_pro_tag(self, datum):
        datum_str = datum.strftime("%Y-%m-%d")
        tag = datum.weekday()
        if FeiertageAPI.is_feiertag_in_land(datum_str):
            return 3
        elif tag >= 5:  # Samstag (5), Sonntag (6)
            return 2
        else:
            return 1

    def gesamt_soll_punkte_im_zeitraum(self, start_dt, end_dt):
        tage = self.tage_im_zeitraum(start_dt, end_dt)
        gesamt = 0
        for tag in tage:
            gesamt += self.punkte_pro_tag(tag)
        return gesamt

    def lade_arbeitstage_je_mitarbeiter_im_zeitraum(self, start_dt, end_dt):
        query = """
                SELECT mitarbeiter_id, datum \
                FROM kalender_mitarbeiter
                WHERE datum BETWEEN ? AND ? \
                """
        self.db.cursor.execute(query, (start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")))
        ergebnis = self.db.cursor.fetchall()

        arbeitstage = {}
        for row in ergebnis:
            mid = row['mitarbeiter_id']
            datum = row['datum']
            if not isinstance(datum, str):
                datum = datum.strftime('%Y-%m-%d')
            arbeitstage.setdefault(mid, []).append(datum)
        return arbeitstage

    def punkte_gesamt_je_mitarbeiter(self, arbeitstage):
        mitarbeiter_punkte = {}
        for mid, daten in arbeitstage.items():
            gesamt = 0
            for datum in daten:
                gesamt += self.punkte_berechnen(datum)
            mitarbeiter_punkte[mid] = gesamt
        return mitarbeiter_punkte

    def punkte_berechnen(self, datum_str):
        dt = datetime.strptime(datum_str, "%Y-%m-%d")
        tag = dt.weekday()
        if FeiertageAPI.is_feiertag_in_land(datum_str):
            return 3
        elif tag >= 5:
            return 2
        else:
            return 1

    def lade_und_zeige_daten(self):
        start_qdate = self.start_datum.date()
        end_qdate = self.end_datum.date()
        start_dt = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day()).date()
        end_dt = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day()).date()

        mitarbeiter_liste = self.db.lade_mitarbeiter()

        aktive_mitarbeiter = []
        mitarbeiter_soll_punkte = {}

        for mitarbeiter in mitarbeiter_liste:
            eintritt = mitarbeiter.get("mitarbeiter_eintritt")
            if isinstance(eintritt, str):
                eintritt = datetime.strptime(eintritt, "%Y-%m-%d").date()
            elif isinstance(eintritt, datetime):
                eintritt = eintritt.date()

            # Mitarbeiter nur zählen, wenn Eintritt vor oder gleich Enddatum Filter
            if eintritt <= end_dt:
                aktive_mitarbeiter.append(mitarbeiter)

                # Individueller Sollzeitraum pro Mitarbeiter: max(Eintritt, Filter-Start) bis Filter-Ende
                mitarbeiter_start = max(eintritt, start_dt)
                mitarbeiter_end = end_dt

                soll = self.gesamt_soll_punkte_im_zeitraum(mitarbeiter_start, mitarbeiter_end)
                mitarbeiter_soll_punkte[mitarbeiter['mitarbeiter_id']] = soll

        anzahl_aktive = len(aktive_mitarbeiter)

        if anzahl_aktive == 0:
            self.tabelle.clear()
            self.tabelle.setRowCount(0)
            self.tabelle.setColumnCount(0)
            return

        arbeitstage = self.lade_arbeitstage_je_mitarbeiter_im_zeitraum(start_dt, end_dt)
        mitarbeiter_punkte = self.punkte_gesamt_je_mitarbeiter(arbeitstage)

        self.tabelle.clear()
        self.tabelle.setColumnCount(6)
        self.tabelle.setHorizontalHeaderLabels([
            "ID", "Vorname", "Nachname", "Soll Punkte", "Ist Punkte", "Differenz"
        ])
        self.tabelle.setRowCount(anzahl_aktive)

        for row, mitarbeiter in enumerate(aktive_mitarbeiter):
            mid = mitarbeiter.get("mitarbeiter_id")
            vorname = mitarbeiter.get("mitarbeiter_vorname", "")
            nachname = mitarbeiter.get("mitarbeiter_nachname", "")

            soll = mitarbeiter_soll_punkte.get(mid, 0)
            ist = mitarbeiter_punkte.get(mid, 0)
            diff = ist - soll

            self.tabelle.setItem(row, 0, QTableWidgetItem(str(mid)))
            self.tabelle.setItem(row, 1, QTableWidgetItem(vorname))
            self.tabelle.setItem(row, 2, QTableWidgetItem(nachname))
            self.tabelle.setItem(row, 3, QTableWidgetItem(f"{soll:.2f}"))
            self.tabelle.setItem(row, 4, QTableWidgetItem(str(ist)))
            diff_item = QTableWidgetItem(f"{diff:.2f}")
            if diff < 0:
                diff_item.setForeground(Qt.Qt.red)
            elif diff > 0:
                diff_item.setForeground(Qt.Qt.darkGreen)
            self.tabelle.setItem(row, 5, diff_item)

