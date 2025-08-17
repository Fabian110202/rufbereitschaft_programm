import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from kalender import KalenderWidget
from mitarbeiter import MitarbeiterWidget
from datenbank import Datenbank
from sollistwidget import SollIstWidget
import os
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
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.North)  # North = oben, West = links
        tabs.setMovable(True)                  # Tabs verschiebbar
        tabs.setDocumentMode(True)             # Flacher, moderner Look
        self.setCentralWidget(tabs)

        # Tabs hinzufügen mit Icons
        tabs.addTab(MitarbeiterWidget(self.db), QIcon("icons/users-solid.svg"), "Mitarbeiter")
        tabs.addTab(KalenderWidget(self.db), QIcon("icons/calendar-solid.svg"), "Kalender")
        tabs.addTab(SollIstWidget(self.db), QIcon("icons/chart-bar-solid.svg"), "Soll/Ist Übersicht")

        # Styling (kann noch weiter angepasst werden)
        self.setStyleSheet("""
            QTabWidget::pane {
                border-top: 2px solid #C2C7CB;
                background: #fdfdfd;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #C4C4C3;
                max-width: 250px;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-color: #9B9B9B;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #d6d6d6;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
