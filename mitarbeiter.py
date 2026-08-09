from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QDialog,
    QLineEdit, QFormLayout, QDialogButtonBox,
    QColorDialog, QFrame, QDateEdit, QCheckBox,
    QMessageBox, QHeaderView, QLabel, QMenu, QAction,
    QAbstractItemView
)
from PyQt5.QtCore import QDate, Qt, QSize
from PyQt5.QtGui import QColor, QPixmap, QPainter, QIcon, QKeySequence

from modern_theme import karte, deutsche_buttons, TEXT_LEISE


def farbpunkt(farbe, groesse=14):
    """Runden Farbklecks als Icon erzeugen.

    Icons werden — anders als per setBackground gesetzte Zellenhintergründe —
    auch dann gezeichnet, wenn ein Stylesheet QTableWidget::item stylt.
    """
    rand = 3
    pixmap = QPixmap(groesse + 2 * rand, groesse + 2 * rand)
    pixmap.fill(Qt.transparent)

    maler = QPainter(pixmap)
    maler.setRenderHint(QPainter.Antialiasing)
    maler.setBrush(farbe)
    maler.setPen(QColor(0, 0, 0, 40))
    maler.drawEllipse(rand, rand, groesse, groesse)
    maler.end()

    return QIcon(pixmap)


class MitarbeiterWidget(QWidget):
    def __init__(self, datenbank):
        super().__init__()
        self.db = datenbank
        self.daten = []

        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(18, 18, 18, 18)

        # --- Kopfzeile der Karte: Titel + Aktionen ---
        titel = QLabel("Mitarbeiter")
        titel.setObjectName("kartentitel")

        self.btn_add = QPushButton("+  Mitarbeiter")
        self.btn_edit = QPushButton("Bearbeiten")
        self.btn_delete = QPushButton("Löschen")

        self.btn_edit.setObjectName("secondaryButton")
        self.btn_delete.setObjectName("dangerButton")

        self.btn_add.clicked.connect(self.hinzufuegen)
        self.btn_edit.clicked.connect(self.bearbeiten)
        self.btn_delete.clicked.connect(self.loeschen)

        kopf = QHBoxLayout()
        kopf.setSpacing(10)
        kopf.addWidget(titel)
        kopf.addStretch()
        kopf.addWidget(self.btn_edit)
        kopf.addWidget(self.btn_delete)
        kopf.addWidget(self.btn_add)

        # --- Tabelle ---
        self.tabelle = QTableWidget()
        self.tabelle.setAlternatingRowColors(True)
        self.tabelle.setShowGrid(False)
        self.tabelle.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabelle.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabelle.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabelle.verticalHeader().setVisible(False)
        self.tabelle.setIconSize(QSize(20, 20))
        self.tabelle.setColumnCount(7)
        self.tabelle.setHorizontalHeaderLabels(
            ["", "ID", "Vorname", "Nachname", "Eintritt", "Austritt", "Ignorieren"]
        )

        header = self.tabelle.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)     # Farbpunkt schmal halten
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tabelle.setColumnWidth(0, 38)

        # Direkte Bedienung an der Zeile statt nur über die Buttons oben
        self.tabelle.doubleClicked.connect(self.bearbeiten)
        self.tabelle.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabelle.customContextMenuRequested.connect(self.zeige_kontextmenue)
        self.tabelle.itemSelectionChanged.connect(self.aktualisiere_button_zustand)

        # Entf-Taste löscht die markierte Zeile
        self.action_loeschen = QAction("Löschen", self)
        self.action_loeschen.setShortcut(QKeySequence.Delete)
        self.action_loeschen.setShortcutContext(Qt.WidgetShortcut)
        self.action_loeschen.triggered.connect(self.loeschen)
        self.tabelle.addAction(self.action_loeschen)

        self.hinweis = QLabel(
            "Doppelklick bearbeitet eine Zeile · Rechtsklick öffnet weitere Aktionen · Entf löscht"
        )
        self.hinweis.setObjectName("hinweis")

        aussen.addWidget(karte(kopf, self.tabelle, self.hinweis))

        self.lade_mitarbeiter()

    # ---------------------------------------------------------- Auswahl-Helfer

    def gewaehlter_mitarbeiter(self):
        """Datensatz der markierten Zeile oder None."""
        zeile = self.tabelle.currentRow()
        if zeile < 0 or zeile >= len(self.daten):
            return None
        return self.daten[zeile]

    def aktualisiere_button_zustand(self):
        hat_auswahl = self.gewaehlter_mitarbeiter() is not None
        self.btn_edit.setEnabled(hat_auswahl)
        self.btn_delete.setEnabled(hat_auswahl)

    def zeige_kontextmenue(self, position):
        zeile = self.tabelle.rowAt(position.y())
        if zeile < 0:
            return
        self.tabelle.selectRow(zeile)

        mitarbeiter = self.gewaehlter_mitarbeiter()
        if mitarbeiter is None:
            return

        menue = QMenu(self)
        menue.addAction("Bearbeiten …", self.bearbeiten)
        menue.addAction("Farbe ändern …", self.farbe_aendern)

        wird_ignoriert = bool(mitarbeiter.get("mitarbeiter_ignorieren"))
        menue.addAction(
            "Wieder berücksichtigen" if wird_ignoriert else "Bei Soll/Ist ignorieren",
            self.ignorieren_umschalten
        )
        menue.addSeparator()
        menue.addAction("Löschen", self.loeschen)

        menue.exec_(self.tabelle.viewport().mapToGlobal(position))

    def lade_mitarbeiter(self, auswahl_id=None):
        """Daten neu laden; auswahl_id markiert danach wieder diesen Mitarbeiter."""
        if auswahl_id is None:
            aktuell = self.gewaehlter_mitarbeiter()
            auswahl_id = aktuell.get("mitarbeiter_id") if aktuell else None

        self.daten = self.db.lade_mitarbeiter()
        self.aktualisiere_tabelle()

        if auswahl_id is not None:
            for zeile, m in enumerate(self.daten):
                if m.get("mitarbeiter_id") == auswahl_id:
                    self.tabelle.selectRow(zeile)
                    break

        self.aktualisiere_button_zustand()

    def datum_als_text(self, datum):
        if hasattr(datum, "strftime"):
            return datum.strftime("%Y-%m-%d")
        if isinstance(datum, QDate):
            return datum.toString("yyyy-MM-dd")
        if isinstance(datum, str):
            return datum.strip()
        return ""

    def mitarbeiter_farbe(self, mitarbeiter):
        farbwert = mitarbeiter.get("mitarbeiter_farbe")
        if isinstance(farbwert, str):
            farbe = QColor(farbwert.strip())
            if farbe.isValid():
                return farbe
        return QColor("#FFFFFF")

    def aktualisiere_tabelle(self):
        self.tabelle.clearContents()
        self.tabelle.setRowCount(len(self.daten))

        for row, mitarbeiter in enumerate(self.daten):
            # Farbe als Punkt in eigener Spalte — die Schrift bleibt dadurch
            # in jeder Zeile dunkel und lesbar.
            farb_item = QTableWidgetItem()
            farb_item.setIcon(farbpunkt(self.mitarbeiter_farbe(mitarbeiter)))
            farb_item.setToolTip("Farbe im Kalender")

            wird_ignoriert = mitarbeiter.get("mitarbeiter_ignorieren") == 1

            items = [
                farb_item,
                QTableWidgetItem(str(mitarbeiter.get("mitarbeiter_id", "") or "")),
                QTableWidgetItem(mitarbeiter.get("mitarbeiter_vorname") or ""),
                QTableWidgetItem(mitarbeiter.get("mitarbeiter_nachname") or ""),
                QTableWidgetItem(self.datum_als_text(mitarbeiter.get("mitarbeiter_eintritt"))),
                QTableWidgetItem(self.datum_als_text(mitarbeiter.get("mitarbeiter_austritt")) or "—"),
                QTableWidgetItem("Ja" if wird_ignoriert else "Nein"),
            ]

            # Ignorierte Mitarbeiter zurückhaltend darstellen
            if wird_ignoriert:
                for item in items[1:]:
                    item.setForeground(QColor(TEXT_LEISE))
                    item.setToolTip("Wird in der Soll/Ist-Berechnung nicht berücksichtigt")

            for spalte, item in enumerate(items):
                self.tabelle.setItem(row, spalte, item)

    def hinzufuegen(self):
        dialog = MitarbeiterDialog()
        if dialog.exec_():
            daten = dialog.get_data()
            try:
                self.db.fuege_mitarbeiter_hinzu(
                    daten["vorname"],
                    daten["nachname"],
                    daten["eintritt"],
                    daten["austritt"],
                    daten["farbe"],
                    daten["ignore"]
                )
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Mitarbeiter konnte nicht angelegt werden:\n{e}")
            self.lade_mitarbeiter()

    def name_von(self, mitarbeiter):
        vorname = mitarbeiter.get("mitarbeiter_vorname") or ""
        nachname = mitarbeiter.get("mitarbeiter_nachname") or ""
        return f"{vorname} {nachname}".strip()

    def speichere(self, mitarbeiter, daten):
        """Änderungen an einem Mitarbeiter schreiben und neu laden."""
        try:
            self.db.aktualisiere_mitarbeiter(
                mitarbeiter["mitarbeiter_id"],
                daten["vorname"],
                daten["nachname"],
                daten["eintritt"],
                daten["austritt"],
                daten["farbe"],
                daten["ignore"]
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Mitarbeiter konnte nicht gespeichert werden:\n{e}")
        self.lade_mitarbeiter(mitarbeiter["mitarbeiter_id"])

    def bearbeiten(self):
        mitarbeiter = self.gewaehlter_mitarbeiter()
        if mitarbeiter is None:
            return

        dialog = MitarbeiterDialog(mitarbeiter)
        if dialog.exec_():
            self.speichere(mitarbeiter, dialog.get_data())

    def farbe_aendern(self):
        """Farbe direkt aus dem Kontextmenü ändern, ohne den ganzen Dialog."""
        mitarbeiter = self.gewaehlter_mitarbeiter()
        if mitarbeiter is None:
            return

        farbe = QColorDialog.getColor(
            self.mitarbeiter_farbe(mitarbeiter), self,
            f"Farbe für {self.name_von(mitarbeiter)}"
        )
        if not farbe.isValid():
            return

        self.speichere(mitarbeiter, {
            "vorname": mitarbeiter.get("mitarbeiter_vorname"),
            "nachname": mitarbeiter.get("mitarbeiter_nachname"),
            "eintritt": mitarbeiter.get("mitarbeiter_eintritt"),
            "austritt": mitarbeiter.get("mitarbeiter_austritt"),
            "farbe": farbe.name(),
            "ignore": mitarbeiter.get("mitarbeiter_ignorieren", 0),
        })

    def ignorieren_umschalten(self):
        mitarbeiter = self.gewaehlter_mitarbeiter()
        if mitarbeiter is None:
            return

        self.speichere(mitarbeiter, {
            "vorname": mitarbeiter.get("mitarbeiter_vorname"),
            "nachname": mitarbeiter.get("mitarbeiter_nachname"),
            "eintritt": mitarbeiter.get("mitarbeiter_eintritt"),
            "austritt": mitarbeiter.get("mitarbeiter_austritt"),
            "farbe": mitarbeiter.get("mitarbeiter_farbe"),
            "ignore": 0 if mitarbeiter.get("mitarbeiter_ignorieren") else 1,
        })

    def loeschen(self):
        mitarbeiter = self.gewaehlter_mitarbeiter()
        if mitarbeiter is None:
            return

        name = self.name_von(mitarbeiter)
        antwort = QMessageBox.question(
            self, "Löschen bestätigen",
            f"{name or 'Diesen Mitarbeiter'} wirklich löschen?\n"
            "Bereits eingetragene Kalendertage bleiben dabei erhalten.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if antwort != QMessageBox.Yes:
            return

        try:
            self.db.loesche_mitarbeiter(mitarbeiter["mitarbeiter_id"])
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Löschen fehlgeschlagen:\n{e}")
        self.lade_mitarbeiter(auswahl_id=-1)


class MitarbeiterDialog(QDialog):
    def __init__(self, daten=None):
        super().__init__()
        self.setWindowTitle("Mitarbeiter erfassen")
        self.setLayout(QFormLayout())
        self.layout().setContentsMargins(24, 24, 24, 24)
        self.layout().setSpacing(12)
        self.setMinimumWidth(420)

        self.vorname = QLineEdit()
        self.nachname = QLineEdit()
        self.eintritt = QDateEdit()
        self.eintritt.setCalendarPopup(True)
        self.eintritt.setDate(QDate.currentDate())

        self.austritt_aktiv = QCheckBox("Austrittsdatum setzen?")
        self.austritt = QDateEdit()
        self.austritt.setCalendarPopup(True)
        self.austritt.setDate(QDate.currentDate())
        self.austritt.setEnabled(False)

        self.austritt_aktiv.toggled.connect(self.austritt.setEnabled)

        # Farbe-Initialisierung und Color Picker Button mit Vorschau
        self.farbe = QColor("#ffffff")  # Standardfarbe
        self.btn_farbe = QPushButton("Farbe wählen …")
        self.btn_farbe.setObjectName("secondaryButton")
        self.btn_farbe.clicked.connect(self.waehle_farbe)

        self.farbe_preview = QFrame()
        self.farbe_preview.setFixedSize(28, 28)
        self.aktualisiere_farbvorschau()

        farbe_layout = QHBoxLayout()
        farbe_layout.setSpacing(10)
        farbe_layout.addWidget(self.farbe_preview)
        farbe_layout.addWidget(self.btn_farbe)
        farbe_layout.addStretch()

        self.layout().addRow("Vorname:", self.vorname)
        self.layout().addRow("Nachname:", self.nachname)
        self.layout().addRow("Eintritt:", self.eintritt)
        self.layout().addRow(self.austritt_aktiv)
        self.layout().addRow("Austritt:", self.austritt)
        self.layout().addRow("Farbe:", farbe_layout)

        self.checkbox = QCheckBox("In der Soll/Ist-Berechnung ignorieren")
        self.layout().addRow("", self.checkbox)

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
            if daten.get("mitarbeiter_austritt"):
                austritt = daten["mitarbeiter_austritt"]
                self.austritt_aktiv.setChecked(True)

                if isinstance(austritt, QDate):
                    self.austritt.setDate(austritt)
                elif hasattr(austritt, "year"):
                    self.austritt.setDate(QDate(austritt.year, austritt.month, austritt.day))
                elif isinstance(austritt, str):
                    try:
                        y, m, d = map(int, austritt.split("-"))
                        self.austritt.setDate(QDate(y, m, d))
                    except ValueError:
                        pass
            if "mitarbeiter_farbe" in daten and daten["mitarbeiter_farbe"]:
                self.farbe = QColor(daten["mitarbeiter_farbe"])
                self.aktualisiere_farbvorschau()

            self.checkbox.setChecked(bool(daten.get("mitarbeiter_ignorieren", 0)))


        buttons = deutsche_buttons(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout().addWidget(buttons)

    def aktualisiere_farbvorschau(self):
        self.farbe_preview.setStyleSheet(
            f"background-color: {self.farbe.name()};"
            "border: 1px solid rgba(0,0,0,0.15); border-radius: 14px;"
        )

    def waehle_farbe(self):
        farbe = QColorDialog.getColor(self.farbe, self, "Farbe auswählen")
        if farbe.isValid():
            self.farbe = farbe
            self.aktualisiere_farbvorschau()

    def get_data(self):
        return {
            "vorname": self.vorname.text(),
            "nachname": self.nachname.text(),
            "eintritt": self.eintritt.date().toPyDate(),
            "austritt": self.austritt.date().toPyDate() if self.austritt_aktiv.isChecked() else None,
            "farbe": self.farbe.name(),
            "ignore": 1 if self.checkbox.isChecked() else 0,
        }