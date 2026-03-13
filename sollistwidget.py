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

    def punkte_soll_pro_tag(self, datum):
        """Punkte, die theoretisch an einem Tag anfallen."""
        datum_str = datum.strftime("%Y-%m-%d")
        tag = datum.weekday()
        if FeiertageAPI.is_feiertag_in_land(datum_str):
            return 3
        elif tag >= 4 and datum > QDate(2026,3, 1): #Samstag oder Sonntag oder Freitag (Änderung gültig ab 01.03.2026)
           return 2
        elif tag >= 5 and datum < QDate(2026,3,1): #Samstag oder Sonntag vor der Änderung
            return 2
        else:
            return 1

    def punkte_ist_pro_tag(self, datum_str):
        print("start")
        dt = datetime.strptime(datum_str, "%Y-%m-%d")
        print("nach datetime")

        tag = dt.weekday()
        stichtag = datetime(2026, 3, 1)

        query_count = """
            SELECT COUNT(*)
            FROM kalender_mitarbeiter
            WHERE datum = ?
        """

        query_individuell = """
            SELECT individuelle_punkte
            FROM kalender_mitarbeiter
            WHERE datum = ? 
              AND individuelle_punkte IS NOT NULL
            LIMIT 1
        """

        print("vor query_count")
        self.db.cursor.execute(query_count, (datum_str,))
        row = self.db.cursor.fetchone()
        count = row[0] if row else 0
        print("nach query_count", count)

        print("vor query_individuell")
        self.db.cursor.execute(query_individuell, (datum_str,))
        row = self.db.cursor.fetchone()
        print("row type:", type(row))

        if row and row[0] is not None:
            try:
                individuelle_punkte = float(row[0])
            except (ValueError, TypeError) as e:
                print("Fehler bei individuelle_punkte:", row[0], type(row[0]), e)
                individuelle_punkte = 0
        else:
            individuelle_punkte = 0

        print(individuelle_punkte)

        mehrfach_belegt = count > 1
        hat_individuelle_punkte = individuelle_punkte is not None and individuelle_punkte > 0

        print("vor feiertag")
        ist_feiertag = FeiertageAPI.is_feiertag_in_land(datum_str)
        print("nach feiertag", ist_feiertag)

        if ist_feiertag:
            return individuelle_punkte if hat_individuelle_punkte else 3

        if hat_individuelle_punkte:
            return individuelle_punkte / 2 if mehrfach_belegt else individuelle_punkte

        if dt >= stichtag:
            ist_zwei_punkte_tag = tag >= 4
        else:
            ist_zwei_punkte_tag = tag >= 5

        if ist_zwei_punkte_tag:
            return 1 if mehrfach_belegt else 2

        return 1

    def gesamt_soll_punkte_im_zeitraum(self, start_dt, end_dt):
        tage = self.tage_im_zeitraum(start_dt, end_dt)
        print(len(tage))
        gesamt = 0
        for tag in tage:
            print(self.punkte_soll_pro_tag(tag))
            gesamt += self.punkte_soll_pro_tag(tag)
        return gesamt

    def verteile_sollpunkte_auf_mitarbeiter(self, start_dt, end_dt, aktive_mitarbeiter, ignored_ids=None):
        if ignored_ids is None:
            ignored_ids = []

        # Eintrittsdaten vorbereiten
        def norm_d(d):
            if isinstance(d, str):
                return datetime.strptime(d, "%Y-%m-%d").date()
            if isinstance(d, datetime):
                return d.date()
            return d

        eintritt_map = {}
        for m in aktive_mitarbeiter:
            e = norm_d(m.get("mitarbeiter_eintritt"))
            eintritt_map[m["mitarbeiter_id"]] = max(e, start_dt)

        # Startwerte
        soll = {m["mitarbeiter_id"]: 0.0 for m in aktive_mitarbeiter}

        # Tag für Tag verteilen
        d = start_dt
        while d <= end_dt:
            pts = self.punkte_soll_pro_tag(d)  # Tagespunkte (1/2/3)

            # --- Abzug: falls Ignorierte an dem Tag eingetragen sind
            dstr = d.strftime("%Y-%m-%d")
            query = """
                    SELECT DISTINCT mitarbeiter_id
                    FROM kalender_mitarbeiter
                    WHERE datum = ? \
                    """
            self.db.cursor.execute(query, (dstr,))
            eintraege = [row[0] for row in self.db.cursor.fetchall()]
            if any(mid in ignored_ids for mid in eintraege):
                # -> Punkte dieses Tages nicht mehr verteilen
                pts = 0

            # Wer ist an diesem Tag aktiv?
            eligible = [m["mitarbeiter_id"] for m in aktive_mitarbeiter if eintritt_map[m["mitarbeiter_id"]] <= d]
            n = len(eligible)
            if n > 0 and pts > 0:
                share = pts / n
                for mid in eligible:
                    soll[mid] += share

            d += timedelta(days=1)

        return soll  # dict: {mid: soll_float}

    def lade_arbeitstage_je_mitarbeiter_im_zeitraum(self, start_dt, end_dt):
        query = """
                SELECT km.mitarbeiter_id, datum \
                FROM kalender_mitarbeiter km
                JOIN mitarbeiter m ON km.mitarbeiter_id = m.mitarbeiter_id
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
                gesamt += self.punkte_ist_pro_tag(datum)
            mitarbeiter_punkte[mid] = gesamt
        return mitarbeiter_punkte

    def punkte_berechnen(self, datum_str):
        dt = datetime.strptime(datum_str, "%Y-%m-%d")
        tag = dt.weekday()
        query = """
                SELECT count(*) as count\
                FROM kalender_mitarbeiter km
                WHERE datum = ? \
                """
        self.db.cursor.execute(query, (datum_str,))
        row = self.db.cursor.fetchone()
        count = row[0] if row else 0

        if FeiertageAPI.is_feiertag_in_land(datum_str):
            return 3
        elif tag >= 5:
            return 1 if count > 1 else 2
        else:
            return 1

    def lade_und_zeige_daten(self):
        start_qdate = self.start_datum.date()
        end_qdate = self.end_datum.date()
        start_dt = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day()).date()
        end_dt = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day()).date()

        mitarbeiter_liste = self.db.lade_mitarbeiter()

        # aktive Mitarbeiter (Eintritt <= Enddatum, nicht ignoriert)
        aktive_mitarbeiter = []
        for m in mitarbeiter_liste:
            if m["mitarbeiter_ignorieren"] != 0:
                continue
            e = m.get("mitarbeiter_eintritt")
            if isinstance(e, str):
                e = datetime.strptime(e, "%Y-%m-%d").date()
            elif isinstance(e, datetime):
                e = e.date()
            if e <= end_dt:
                aktive_mitarbeiter.append(m)

        anzahl_aktive = len(aktive_mitarbeiter)
        if anzahl_aktive == 0:
            self.tabelle.clear()
            self.tabelle.setRowCount(0)
            self.tabelle.setColumnCount(0)
            return
        # IDs der ignorierten Mitarbeiter merken
        ignored_ids = [m["mitarbeiter_id"] for m in mitarbeiter_liste if m["mitarbeiter_ignorieren"] != 0]

        # Soll berechnen, ignorierte Einträge rausziehen
        mitarbeiter_soll_punkte = self.verteile_sollpunkte_auf_mitarbeiter(start_dt, end_dt, aktive_mitarbeiter,
                                                                           ignored_ids)
        # Ist wahlweise wie bisher (optional noch auf Eintrittsdatum filtern)
        arbeitstage = self.lade_arbeitstage_je_mitarbeiter_im_zeitraum(start_dt, end_dt)
        mitarbeiter_ist = {}
        # Eintrittsmap für Filter
        eintritt_map = {}
        for m in aktive_mitarbeiter:
            e = m.get("mitarbeiter_eintritt")
            if isinstance(e, str):
                e = datetime.strptime(e, "%Y-%m-%d").date()
            elif isinstance(e, datetime):
                e = e.date()
            eintritt_map[m["mitarbeiter_id"]] = e

        for mid, daten in arbeitstage.items():
            # nur Tage ab Eintritt zählen (falls nötig)
            ist_sum = 0
            e = eintritt_map.get(mid, start_dt)
            for dstr in daten:
                ddate = datetime.strptime(dstr, "%Y-%m-%d").date()
                if ddate >= e:
                    ist_sum += self.punkte_ist_pro_tag(dstr)
            mitarbeiter_ist[mid] = ist_sum

        # Tabelle befüllen (außerhalb der Schleife!)
        self.tabelle.clear()
        self.tabelle.setColumnCount(7)
        self.tabelle.setHorizontalHeaderLabels(["ID", "Vorname", "Nachname","Eintrittdatum" ,"Soll Punkte", "Ist Punkte", "Differenz"])
        self.tabelle.setRowCount(anzahl_aktive)

        for row, m in enumerate(aktive_mitarbeiter):
            mid = m.get("mitarbeiter_id")
            vorname = m.get("mitarbeiter_vorname", "")
            nachname = m.get("mitarbeiter_nachname", "")
            eintritt = m.get("mitarbeiter_eintritt", "")

            soll = mitarbeiter_soll_punkte.get(mid, 0.0)
            ist = mitarbeiter_ist.get(mid, 0.0)
            diff = ist - soll

            self.tabelle.setItem(row, 0, QTableWidgetItem(str(mid)))
            self.tabelle.setItem(row, 1, QTableWidgetItem(vorname))
            self.tabelle.setItem(row, 2, QTableWidgetItem(nachname))
            self.tabelle.setItem(row, 3, QTableWidgetItem(eintritt))
            self.tabelle.setItem(row, 4, QTableWidgetItem(f"{soll:.2f}"))
            self.tabelle.setItem(row, 5, QTableWidgetItem(f"{ist:.2f}"))
            diff_item = QTableWidgetItem(f"{diff:.2f}")
            if diff < 0:
                diff_item.setForeground(Qt.Qt.red)
            elif diff > 0:
                diff_item.setForeground(Qt.Qt.darkGreen)
            self.tabelle.setItem(row, 6, diff_item)


