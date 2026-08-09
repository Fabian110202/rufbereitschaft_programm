from datetime import datetime, timedelta, date
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QLabel, QDateEdit, QPushButton, QHeaderView
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor

from feiertagsAPI import FeiertageAPI
from modern_theme import karte, ROT, GRUEN


class SollIstWidget(QWidget):
    def __init__(self, datenbank):
        super().__init__()
        self.db = datenbank

        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(18, 18, 18, 18)
        aussen.setSpacing(14)

        # Filter-Layout (Start- und Enddatum)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

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
        self.btn_aktualisieren.setObjectName("primaryButton")
        self.btn_aktualisieren.setToolTip("Soll/Ist für den gewählten Zeitraum neu berechnen")
        filter_layout.addWidget(self.btn_aktualisieren)
        filter_layout.addStretch()

        self.tabelle = QTableWidget()
        self.tabelle.setAlternatingRowColors(True)
        self.tabelle.setShowGrid(False)
        self.tabelle.setSortingEnabled(True)
        self.tabelle.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabelle.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabelle.verticalHeader().setVisible(False)
        self.tabelle.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        titel = QLabel("Soll/Ist Übersicht")
        titel.setObjectName("kartentitel")

        self.hinweis_label = QLabel()
        self.hinweis_label.setObjectName("hinweis")
        self.hinweis_label.setWordWrap(True)
        self.hinweis_label.setVisible(False)

        aussen.addWidget(karte(filter_layout, rand=14))
        aussen.addWidget(karte(titel, self.tabelle, self.hinweis_label))

        self.btn_aktualisieren.clicked.connect(self.lade_und_zeige_daten)

        # Daten direkt laden
        self.lade_und_zeige_daten()

    def feld(self, obj, key, default=None):
        """Liest Werte sowohl aus dicts als auch aus sqlite3.Row-Objekten."""
        if obj is None:
            return default
        if hasattr(obj, "get"):
            return obj.get(key, default)
        try:
            return obj[key]
        except (KeyError, IndexError, TypeError):
            return default

    def norm_datum(self, d):
        if d is None or d == "":
            return None
        if isinstance(d, str):
            return datetime.strptime(d, "%Y-%m-%d").date()
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, QDate):
            return date(d.year(), d.month(), d.day())
        return d

    def datum_als_text(self, d):
        d = self.norm_datum(d)
        return d.strftime("%Y-%m-%d") if d else ""

    def ist_aktiv_am_tag(self, mitarbeiter, datum):
        datum = self.norm_datum(datum)
        eintritt = self.norm_datum(self.feld(mitarbeiter, "mitarbeiter_eintritt"))
        austritt = self.norm_datum(self.feld(mitarbeiter, "mitarbeiter_austritt"))

        if eintritt and datum < eintritt:
            return False
        if austritt and datum > austritt:
            return False

        return True

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
        datum = self.norm_datum(datum)
        datum_str = datum.strftime("%Y-%m-%d")
        tag = datum.weekday()
        stichtag = date(2026, 3, 1)

        if FeiertageAPI.is_feiertag_in_land(datum_str):
            return 3
        if datum >= stichtag:
            # Ab 01.03.2026 gelten Freitag, Samstag und Sonntag als 2-Punkte-Tage.
            return 2 if tag >= 4 else 1

        # Vor dem 01.03.2026 gelten Samstag und Sonntag als 2-Punkte-Tage.
        return 2 if tag >= 5 else 1

    def punkte_ist_pro_tag(self, datum):
        datum = self.norm_datum(datum)
        datum_str = datum.strftime("%Y-%m-%d")
        tag = datum.weekday()
        stichtag = date(2026, 3, 1)

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

        self.db.cursor.execute(query_count, (datum_str,))
        row = self.db.cursor.fetchone()
        count = row[0] if row else 0

        self.db.cursor.execute(query_individuell, (datum_str,))
        row = self.db.cursor.fetchone()

        individuelle_punkte = 0.0
        if row and row[0] is not None:
            try:
                individuelle_punkte = float(row[0])
            except (ValueError, TypeError):
                individuelle_punkte = 0.0

        mehrfach_belegt = count > 1
        hat_individuelle_punkte = individuelle_punkte > 0

        if FeiertageAPI.is_feiertag_in_land(datum_str):
            return individuelle_punkte if hat_individuelle_punkte else 3

        if hat_individuelle_punkte:
            return individuelle_punkte / 2 if mehrfach_belegt else individuelle_punkte

        if datum >= stichtag:
            ist_zwei_punkte_tag = tag >= 4
        else:
            ist_zwei_punkte_tag = tag >= 5

        if ist_zwei_punkte_tag:
            return 1 if mehrfach_belegt else 2

        return 1

    def gesamt_soll_punkte_im_zeitraum(self, start_dt, end_dt):
        tage = self.tage_im_zeitraum(start_dt, end_dt)
        gesamt = 0
        for tag in tage:
            gesamt += self.punkte_soll_pro_tag(tag)
        return gesamt

    def verteile_sollpunkte_auf_mitarbeiter(self, start_dt, end_dt, aktive_mitarbeiter, ignored_ids=None):
        if ignored_ids is None:
            ignored_ids = []

        # Startwerte
        soll = {
            self.feld(m, "mitarbeiter_id"): 0.0
            for m in aktive_mitarbeiter
        }

        # Tag für Tag verteilen
        d = start_dt
        while d <= end_dt:
            pts = self.punkte_soll_pro_tag(d)  # Tagespunkte (1/2/3)

            # Abzug: falls Ignorierte an dem Tag eingetragen sind
            dstr = d.strftime("%Y-%m-%d")
            query = """
                SELECT DISTINCT mitarbeiter_id
                FROM kalender_mitarbeiter
                WHERE datum = ?
            """
            self.db.cursor.execute(query, (dstr,))
            eintraege = [row[0] for row in self.db.cursor.fetchall()]

            if any(mid in ignored_ids for mid in eintraege):
                # Punkte dieses Tages nicht mehr verteilen
                pts = 0

            # Wer ist an diesem Tag aktiv?
            eligible = [
                self.feld(m, "mitarbeiter_id")
                for m in aktive_mitarbeiter
                if self.ist_aktiv_am_tag(m, d)
            ]

            n = len(eligible)
            if n > 0 and pts > 0:
                share = pts / n
                for mid in eligible:
                    soll[mid] += share

            d += timedelta(days=1)

        return soll  # dict: {mid: soll_float}

    def lade_arbeitstage_je_mitarbeiter_im_zeitraum(self, start_dt, end_dt):
        query = """
            SELECT km.mitarbeiter_id, datum
            FROM kalender_mitarbeiter km
            JOIN mitarbeiter m ON km.mitarbeiter_id = m.mitarbeiter_id
            WHERE datum BETWEEN ? AND ?
        """
        self.db.cursor.execute(
            query,
            (start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        )
        ergebnis = self.db.cursor.fetchall()

        arbeitstage = {}
        for row in ergebnis:
            try:
                mid = row["mitarbeiter_id"]
                datum = row["datum"]
            except (TypeError, KeyError, IndexError):
                mid = row[0]
                datum = row[1]

            datum = self.datum_als_text(datum)
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

    def punkte_berechnen(self, datum):
        datum = self.norm_datum(datum)
        datum_str = datum.strftime("%Y-%m-%d")
        tag = datum.weekday()
        stichtag = date(2026, 3, 1)

        query = """
            SELECT COUNT(*) AS count
            FROM kalender_mitarbeiter km
            WHERE datum = ?
        """
        self.db.cursor.execute(query, (datum_str,))
        row = self.db.cursor.fetchone()
        count = row[0] if row else 0

        if FeiertageAPI.is_feiertag_in_land(datum_str):
            return 3

        if datum >= stichtag:
            ist_zwei_punkte_tag = tag >= 4
        else:
            ist_zwei_punkte_tag = tag >= 5

        if ist_zwei_punkte_tag:
            return 1 if count > 1 else 2

        return 1

    def zeige_hinweis(self, text=""):
        self.hinweis_label.setText(text)
        self.hinweis_label.setVisible(bool(text))

    def lade_und_zeige_daten(self):
        self.zeige_hinweis("")
        start_qdate = self.start_datum.date()
        end_qdate = self.end_datum.date()
        start_dt = date(start_qdate.year(), start_qdate.month(), start_qdate.day())
        end_dt = date(end_qdate.year(), end_qdate.month(), end_qdate.day())

        mitarbeiter_liste = self.db.lade_mitarbeiter()

        # Aktive Mitarbeiter: nicht ignoriert und im gewählten Zeitraum aktiv
        aktive_mitarbeiter = []
        for m in mitarbeiter_liste:
            if self.feld(m, "mitarbeiter_ignorieren", 0) != 0:
                continue

            e = self.norm_datum(self.feld(m, "mitarbeiter_eintritt"))
            a = self.norm_datum(self.feld(m, "mitarbeiter_austritt"))

            if e is None:
                continue
            if e <= end_dt and (a is None or a >= start_dt):
                aktive_mitarbeiter.append(m)

        anzahl_aktive = len(aktive_mitarbeiter)
        if anzahl_aktive == 0:
            self.tabelle.clear()
            self.tabelle.setRowCount(0)
            self.tabelle.setColumnCount(0)
            self.zeige_hinweis(
                "Für diesen Zeitraum gibt es keine aktiven Mitarbeiter. "
                "Prüfe die Eintritts- und Austrittsdaten im Tab „Mitarbeiter“ "
                "oder wähle einen anderen Zeitraum."
            )
            return

        # IDs der ignorierten Mitarbeiter merken
        ignored_ids = [
            self.feld(m, "mitarbeiter_id")
            for m in mitarbeiter_liste
            if self.feld(m, "mitarbeiter_ignorieren", 0) != 0
        ]

        # Soll berechnen, ignorierte Einträge rausziehen
        mitarbeiter_soll_punkte = self.verteile_sollpunkte_auf_mitarbeiter(
            start_dt,
            end_dt,
            aktive_mitarbeiter,
            ignored_ids
        )

        arbeitstage = self.lade_arbeitstage_je_mitarbeiter_im_zeitraum(start_dt, end_dt)
        mitarbeiter_ist = {
            self.feld(m, "mitarbeiter_id"): 0.0
            for m in aktive_mitarbeiter
        }
        mid_to_m = {
            self.feld(m, "mitarbeiter_id"): m
            for m in aktive_mitarbeiter
        }

        for mid, daten in arbeitstage.items():
            m = mid_to_m.get(mid)
            if not m:
                continue

            ist_sum = 0.0
            for dstr in daten:
                ddate = self.norm_datum(dstr)
                if self.ist_aktiv_am_tag(m, ddate):
                    ist_sum += self.punkte_ist_pro_tag(dstr)

            mitarbeiter_ist[mid] = ist_sum

        # Tabelle befüllen — Sortierung währenddessen aus, sonst verrutschen die Zeilen
        self.tabelle.setSortingEnabled(False)
        self.tabelle.clear()
        self.tabelle.setColumnCount(7)
        self.tabelle.setHorizontalHeaderLabels([
            "ID", "Vorname", "Nachname", "Eintrittsdatum",
            "Soll Punkte", "Ist Punkte", "Differenz"
        ])
        self.tabelle.setRowCount(anzahl_aktive)

        def zahl_item(wert, tooltip=""):
            """Item, das numerisch sortiert statt alphabetisch."""
            item = QTableWidgetItem()
            item.setData(Qt.DisplayRole, round(float(wert), 2))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if tooltip:
                item.setToolTip(tooltip)
            return item

        for row, m in enumerate(aktive_mitarbeiter):
            mid = self.feld(m, "mitarbeiter_id")
            vorname = self.feld(m, "mitarbeiter_vorname", "")
            nachname = self.feld(m, "mitarbeiter_nachname", "")
            eintritt = self.datum_als_text(self.feld(m, "mitarbeiter_eintritt", ""))

            soll = mitarbeiter_soll_punkte.get(mid, 0.0)
            ist = mitarbeiter_ist.get(mid, 0.0)
            diff = ist - soll

            self.tabelle.setItem(row, 0, zahl_item(mid))
            self.tabelle.setItem(row, 1, QTableWidgetItem(str(vorname)))
            self.tabelle.setItem(row, 2, QTableWidgetItem(str(nachname)))
            self.tabelle.setItem(row, 3, QTableWidgetItem(eintritt))
            self.tabelle.setItem(row, 4, zahl_item(soll, "Rechnerisch fairer Anteil im Zeitraum"))
            self.tabelle.setItem(row, 5, zahl_item(ist, "Tatsächlich geleistete Punkte"))

            if diff < 0:
                tooltip = f"{abs(diff):.2f} Punkte unter dem Soll"
            elif diff > 0:
                tooltip = f"{diff:.2f} Punkte über dem Soll"
            else:
                tooltip = "Genau im Soll"

            diff_item = zahl_item(diff, tooltip)
            if diff < 0:
                diff_item.setForeground(QColor(ROT))
            elif diff > 0:
                diff_item.setForeground(QColor(GRUEN))

            self.tabelle.setItem(row, 6, diff_item)

        self.tabelle.setSortingEnabled(True)
