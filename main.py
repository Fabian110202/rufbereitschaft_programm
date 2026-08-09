import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt5.QtGui import QIcon
from modern_theme import MODERN_LIGHT_STYLE
from kalender import KalenderWidget
from mitarbeiter import MitarbeiterWidget
from datenbank import Datenbank
from sollistwidget import SollIstWidget
from pathlib import Path
from platformdirs import user_data_dir

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rufbereitschaft-Programm")
        self.setGeometry(100, 100, 1000, 700)

        # Benutzer-spezifischen Datenordner bestimmen
        app_name = "Rufbereitschaft"
        app_author = "GahlenDevelopment"  # optional, unter Windows wird das als Unterordner genutzt
        datenbank_ordner = Path(user_data_dir(app_name, app_author))
        datenbank_ordner.mkdir(parents=True, exist_ok=True)

        # Datenbank-Datei im Nutzerordner ablegen
        datenbank_datei = datenbank_ordner / "rufbereitschaft.db"

        # Verbindung zur DB herstellen
        self.db = Datenbank(datei=str(datenbank_datei))

        # Tab Widget erstellen
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)  # North = oben, West = links
        self.tabs.setMovable(True)                  # Tabs verschiebbar
        self.tabs.setDocumentMode(True)             # Flacher, moderner Look
        self.setCentralWidget(self.tabs)

        # Icons relativ zum Skript auflösen, damit sie auch beim Start aus einem
        # anderen Arbeitsverzeichnis (und im PyInstaller-Bundle) gefunden werden.
        icon_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "icons"

        self.mitarbeiter_tab = MitarbeiterWidget(self.db)
        self.kalender_tab = KalenderWidget(self.db)
        self.sollist_tab = SollIstWidget(self.db)

        self.tabs.addTab(self.mitarbeiter_tab, QIcon(str(icon_dir / "users-solid.svg")), "Mitarbeiter")
        self.tabs.addTab(self.kalender_tab, QIcon(str(icon_dir / "calendar-solid.svg")), "Kalender")
        self.tabs.addTab(self.sollist_tab, QIcon(str(icon_dir / "chart-bar-solid.svg")), "Soll/Ist Übersicht")

        # Beim Tab-Wechsel neu laden, damit Änderungen aus einem anderen Tab
        # (z. B. neu angelegte Mitarbeiter) sofort sichtbar werden.
        self.tabs.currentChanged.connect(self.tab_gewechselt)

        self.statusBar().showMessage("Bereit")

    def tab_gewechselt(self, index):
        widget = self.tabs.widget(index)
        if widget is self.kalender_tab:
            self.kalender_tab.lade_alle_eintraege()
        elif widget is self.sollist_tab:
            self.sollist_tab.lade_und_zeige_daten()
        elif widget is self.mitarbeiter_tab:
            self.mitarbeiter_tab.lade_mitarbeiter()

    def closeEvent(self, event):
        self.db.schliesse_verbindung()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_LIGHT_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
