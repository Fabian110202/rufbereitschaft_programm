# modern_theme.py
#
# Helles Karten-Theme: Inhalte liegen als weiße Karten mit weichem Schatten auf
# einem grauen Grund. Buttons sind flach mit einer Akzentfarbe.
#
# Wichtig: Qt-Stylesheets kennen kein box-shadow. Schatten werden deshalb über
# QGraphicsDropShadowEffect gesetzt — dafür gibt es unten die Helfer `karte()`
# und `schatten()`.
#
# Ebenfalls wichtig: Sobald hier `QTableWidget::item` gestylt wird, ignoriert Qt
# `QTableWidgetItem.setBackground()`. Zellen dürfen ihre Farbe daher nicht über
# den Hintergrund transportieren — siehe farbpunkt() in mitarbeiter.py.

from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect, QVBoxLayout
from PyQt5.QtGui import QColor

# ---------------------------------------------------------------- Farbpalette

AKZENT = "#2563EB"
GRUND = "#F1F4F9"
KARTE = "#FFFFFF"
TEXT = "#1F2937"
TEXT_LEISE = "#6B7280"
RAHMEN = "#E4E8EF"
ROT = "#DC2626"
GRUEN = "#15803D"


def schatten(widget, blur=28, y_versatz=6, deckkraft=32):
    """Weichen Schlagschatten auf ein Widget legen."""
    effekt = QGraphicsDropShadowEffect(widget)
    effekt.setBlurRadius(blur)
    effekt.setXOffset(0)
    effekt.setYOffset(y_versatz)
    effekt.setColor(QColor(15, 23, 42, deckkraft))
    widget.setGraphicsEffect(effekt)
    return widget


def deutsche_buttons(buttonbox):
    """Beschriftungen einer QDialogButtonBox eindeutschen und Rollen stylen."""
    from PyQt5.QtWidgets import QDialogButtonBox

    beschriftungen = {
        QDialogButtonBox.Ok: "Speichern",
        QDialogButtonBox.Cancel: "Abbrechen",
        QDialogButtonBox.Yes: "Ja",
        QDialogButtonBox.No: "Nein",
    }
    for rolle, text in beschriftungen.items():
        knopf = buttonbox.button(rolle)
        if knopf is not None:
            knopf.setText(text)

    abbrechen = buttonbox.button(QDialogButtonBox.Cancel)
    if abbrechen is not None:
        abbrechen.setObjectName("secondaryButton")

    return buttonbox


def karte(*widgets, abstand=14, rand=18):
    """Widgets/Layouts in eine weiße Karte mit Schatten packen."""
    rahmen = QFrame()
    rahmen.setObjectName("karte")
    layout = QVBoxLayout(rahmen)
    layout.setContentsMargins(rand, rand, rand, rand)
    layout.setSpacing(abstand)

    for w in widgets:
        if hasattr(w, "addWidget"):     # ist ein Layout
            layout.addLayout(w)
        else:
            layout.addWidget(w)

    schatten(rahmen)
    return rahmen


MODERN_LIGHT_STYLE = f"""
/* ---------- Grundlagen ---------- */

QWidget {{
    background-color: {GRUND};
    color: {TEXT};
    font-family: "Segoe UI", "Inter", "Noto Sans", "Cantarell", "Arial";
    font-size: 13px;
}}

QLabel {{
    background: transparent;
    color: {TEXT};
}}

QLabel#kartentitel {{
    font-size: 15px;
    font-weight: 700;
    color: {TEXT};
}}

QLabel#hinweis {{
    color: {TEXT_LEISE};
    font-size: 12px;
}}

QToolTip {{
    background-color: {TEXT};
    color: #F9FAFB;
    border: none;
    border-radius: 6px;
    padding: 6px 9px;
}}

/* ---------- Karten ---------- */

QFrame#karte {{
    background-color: {KARTE};
    border: 1px solid {RAHMEN};
    border-radius: 14px;
}}

/* Reine Layout-Container in Karten: durchsichtig statt grau.
   Achtung: NICHT `QFrame#karte > QWidget` verwenden — dieser Selektor hat
   höhere Spezifität als `QPushButton` und macht Buttons unsichtbar. */
QWidget#transparent {{
    background-color: transparent;
}}

QFrame#trenner {{
    background-color: {RAHMEN};
    max-height: 1px;
    border: none;
}}

/* ---------- Buttons: flach, eine Akzentfarbe ---------- */

QPushButton {{
    background-color: {AKZENT};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
    min-height: 17px;
}}

QPushButton:hover     {{ background-color: #1D4ED8; }}
QPushButton:pressed   {{ background-color: #1E40AF; }}
QPushButton:disabled  {{ background-color: #E5E7EB; color: #9CA3AF; }}
QPushButton:focus     {{ outline: none; }}

QPushButton#secondaryButton {{
    background-color: #FFFFFF;
    color: {TEXT};
    border: 1px solid #D3D9E2;
}}
QPushButton#secondaryButton:hover    {{ background-color: #F5F7FA; border-color: #B9C2CE; }}
QPushButton#secondaryButton:pressed  {{ background-color: #EBEFF4; }}
QPushButton#secondaryButton:disabled {{ background-color: #F7F8FA; color: #B6BCC6; border-color: #E4E8EF; }}

QPushButton#dangerButton {{
    background-color: #FFFFFF;
    color: {ROT};
    border: 1px solid #F0C4C4;
}}
QPushButton#dangerButton:hover    {{ background-color: #FEF2F2; border-color: {ROT}; }}
QPushButton#dangerButton:pressed  {{ background-color: #FEE2E2; }}
QPushButton#dangerButton:disabled {{ background-color: #F7F8FA; color: #C9CED6; border-color: #E4E8EF; }}

/* Dezenter Icon-Button für Zeilenaktionen */
QPushButton#zeilenAktion {{
    background-color: transparent;
    color: {TEXT_LEISE};
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    font-weight: 600;
}}
QPushButton#zeilenAktion:hover {{ background-color: #EEF2F7; color: {TEXT}; }}

/* ---------- Eingabefelder ---------- */

QLineEdit, QDateEdit, QComboBox, QSpinBox {{
    background-color: #FFFFFF;
    color: {TEXT};
    border: 1px solid #D3D9E2;
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 18px;
    selection-background-color: {AKZENT};
    selection-color: #FFFFFF;
}}

QLineEdit:hover, QDateEdit:hover, QComboBox:hover {{ border-color: #B9C2CE; }}

QLineEdit:focus, QDateEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 2px solid {AKZENT};
    padding: 7px 9px;
}}

QLineEdit:disabled, QDateEdit:disabled {{
    background-color: #F5F7FA;
    color: #9CA3AF;
}}

QLineEdit[ungueltig="true"] {{
    border: 2px solid {ROT};
    background-color: #FEF2F2;
    padding: 7px 9px;
}}

/* Nur den Rahmen des Aufklapp-Bereichs entfernen. Den Pfeil zeichnet Qt selbst —
   ein per border-Trick "gebauter" Pfeil wird hier als grauer Block gerendert,
   weil Qt-Stylesheets für ::down-arrow ein echtes Bild erwarten. */
QComboBox::drop-down, QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    border: none;
    width: 22px;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid {RAHMEN};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #E8F0FE;
    selection-color: #1E3A8A;
    outline: none;
}}

/* ---------- Checkbox ---------- */

QCheckBox {{
    spacing: 9px;
    color: {TEXT};
    background: transparent;
    padding: 3px 0;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #C4CBD6;
    background-color: #FFFFFF;
}}

QCheckBox::indicator:hover   {{ border-color: {AKZENT}; }}
QCheckBox::indicator:checked {{ background-color: {AKZENT}; border-color: {AKZENT}; }}

/* ---------- Tabellen ---------- */

QTableWidget {{
    background-color: {KARTE};
    alternate-background-color: #FAFBFD;
    color: {TEXT};
    gridline-color: transparent;
    border: none;
    selection-background-color: #E8F0FE;
    selection-color: #1E3A8A;
    outline: none;
}}

/* Hier bewusst KEIN `color:` setzen — das würde QTableWidgetItem.setForeground()
   aushebeln (ausgegraute Zeilen, rote/grüne Differenz). Die Textfarbe kommt
   aus der QWidget-Regel oben. */
QTableWidget::item {{
    padding: 11px 10px;
    border: none;
    border-bottom: 1px solid #F0F2F6;
}}

QTableWidget::item:hover    {{ background-color: #F5F8FE; }}
QTableWidget::item:selected {{ background-color: #E8F0FE; color: #1E3A8A; }}

QHeaderView {{ background-color: transparent; }}

QHeaderView::section {{
    background-color: transparent;
    color: {TEXT_LEISE};
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {RAHMEN};
    font-weight: 600;
    font-size: 12px;
}}

QHeaderView::section:hover {{ color: {TEXT}; }}

QTableCornerButton::section {{ background-color: transparent; border: none; }}

/* ---------- Kontextmenü ---------- */

QMenu {{
    background-color: #FFFFFF;
    border: 1px solid {RAHMEN};
    border-radius: 10px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 22px 8px 14px;
    border-radius: 6px;
    color: {TEXT};
}}

QMenu::item:selected {{ background-color: #E8F0FE; color: #1E3A8A; }}
QMenu::item:disabled {{ color: #B6BCC6; }}
QMenu::separator {{ height: 1px; background: {RAHMEN}; margin: 5px 8px; }}

/* ---------- Tabs ---------- */

QTabWidget::pane {{ border: none; background: transparent; }}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_LEISE};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 11px 18px;
    margin-right: 4px;
    font-weight: 600;
}}

QTabBar::tab:hover    {{ color: {TEXT}; }}
QTabBar::tab:selected {{ color: {AKZENT}; border-bottom: 2px solid {AKZENT}; }}

/* ---------- Dialoge ---------- */

QDialog {{ background-color: {KARTE}; }}
QDialogButtonBox QPushButton {{ min-width: 96px; }}
QMessageBox {{ background-color: {KARTE}; }}
QMessageBox QLabel {{ color: {TEXT}; }}

/* ---------- Scrollbars ---------- */

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #CBD2DC; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #A7B0BD; }}

QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #CBD2DC; border-radius: 5px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: #A7B0BD; }}

QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- Statusleiste ---------- */

QStatusBar {{ background-color: transparent; color: {TEXT_LEISE}; }}
QStatusBar::item {{ border: none; }}
"""
