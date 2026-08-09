# CLAUDE.md

Hinweise für Claude Code zur Arbeit an diesem Repository.

## Was das Programm macht

Desktop-Anwendung (PyQt5) zur Verwaltung einer **Rufbereitschaft** in NRW. Mitarbeiter
werden gepflegt, Rufbereitschaftstage im Kalender eingetragen, und in einer Soll/Ist-
Übersicht wird geprüft, ob die Bereitschaftslast fair verteilt ist. Die Bewertung erfolgt
über ein **Punktesystem** pro Tag.

Sprache im Code und in der UI ist Deutsch (Bezeichner, Kommentare, Tabellen-/Spaltennamen).
Neuer Code soll das beibehalten.

## Ausführen

```bash
.venv/bin/python main.py          # Anwendung starten
pyinstaller main.spec             # Windows-Build (One-File, ohne Konsole)
```

Abhängigkeiten: `PyQt5`, `requests`, `platformdirs`. Es gibt keine `requirements.txt`
und keine Tests.

## Architektur

Drei Tabs, je ein Widget, alle teilen sich **eine** `Datenbank`-Instanz aus
[main.py](main.py):

| Datei | Rolle |
| --- | --- |
| [main.py](main.py) | `MainWindow`, DB-Pfad via `platformdirs`, Tab-Aufbau |
| [datenbank.py](datenbank.py) | SQLite-Zugriff, Schema, Ad-hoc-Migrationen |
| [mitarbeiter.py](mitarbeiter.py) | Tab „Mitarbeiter": CRUD, Farbe, Ignorieren-Flag |
| [kalender.py](kalender.py) | Tab „Kalender": Einträge anlegen/löschen, Tagesfärbung |
| [sollistwidget.py](sollistwidget.py) | Tab „Soll/Ist": gesamte Punkteberechnung |
| [feiertagsAPI.py](feiertagsAPI.py) | Feiertage NRW über `feiertage-api.de`, Klassen-Cache |
| [modern_theme.py](modern_theme.py) | Globales Qt-Stylesheet |

Datenbankdatei: `user_data_dir("Rufbereitschaft", "GahlenDevelopment")/rufbereitschaft.db`.
Der Default `datenbank/rufbereitschaft.sqlite` in `Datenbank.__init__` wird von `main.py`
überschrieben.

### Schema

* `mitarbeiter` — Vor-/Nachname, Eintritt, Austritt, Farbe (`#rrggbb`), `mitarbeiter_ignorieren`
* `kalender_mitarbeiter` — `datum` (TEXT `YYYY-MM-DD`), `mitarbeiter_id`, `individuelle_punkte`,
  Zeitstempel. Ein Tag mit zwei Mitarbeitern = **zwei Zeilen** mit gleichem `datum`
  („Tag geteilt").

Migrationen laufen in `erstelle_tabellen()` als `PRAGMA table_info` + `ALTER TABLE`.
Neue Spalten dort nach demselben Muster ergänzen — es gibt kein Migrationsframework.

## Punktelogik (die eigentliche Fachlogik)

Alles in [sollistwidget.py](sollistwidget.py). Regeln:

* Feiertag (NRW) → 3 Punkte
* Ab dem **Stichtag 01.03.2026**: Fr/Sa/So = 2 Punkte, sonst 1
* Vor dem Stichtag: Sa/So = 2 Punkte, sonst 1
* `individuelle_punkte > 0` überschreibt den Tageswert (Ist-Seite)
* Geteilter Tag (mehrere Einträge) halbiert den Wert je Mitarbeiter

**Soll** ([`verteile_sollpunkte_auf_mitarbeiter`](sollistwidget.py#L157)): die Tagespunkte
werden gleichmäßig auf alle am Tag aktiven, nicht ignorierten Mitarbeiter verteilt. Ist an
einem Tag ein *ignorierter* Mitarbeiter eingetragen, entfallen die Punkte des Tages komplett.

**Ist** ([`punkte_ist_pro_tag`](sollistwidget.py#L104)): Punkte aus den tatsächlichen
Kalendereinträgen. Differenz = Ist − Soll; negativ = rot, positiv = grün.

Der Stichtag 01.03.2026 ist an **drei** Stellen hartkodiert (`punkte_soll_pro_tag`,
`punkte_ist_pro_tag`, `punkte_berechnen`). Bei Änderungen alle drei anpassen.

## Konventionen

* Datumsformat in der DB durchgehend `YYYY-MM-DD` als TEXT.
* `QDate` ↔ `date` ↔ `str` wird über `norm_datum`/`datum_als_text` in
  [sollistwidget.py](sollistwidget.py) vereinheitlicht; `feld()` liest sowohl `dict` als
  auch `sqlite3.Row`.
* SQL immer parametrisiert (`?`) — so ist es im Bestand, bitte beibehalten.
* Nach schreibenden Kalender-Operationen `lade_alle_eintraege()` aufrufen; das lädt
  Mitarbeiter *und* Einträge neu, färbt ein und baut die Legende.
* Ein Tab-Wechsel löst über `MainWindow.tab_gewechselt` einen Reload des Zieltabs aus —
  neue Widgets dort eintragen, damit sie aktuell bleiben.
* Styling gehört zentral in [modern_theme.py](modern_theme.py). Karten-Layout: Inhalte
  über `karte(...)` einpacken (weiße Fläche + Schatten via `QGraphicsDropShadowEffect`,
  weil Qt kein `box-shadow` kennt). Buttons wählen ihre Variante über `setObjectName`:
  ohne Namen = blau/primär, `secondaryButton` = weiß, `dangerButton` = rot-outline.
  `deutsche_buttons(...)` übersetzt eine `QDialogButtonBox`.

### Qt-Stylesheet-Fallen (mehrfach reingelaufen)

* Sobald `QTableWidget::item` im Stylesheet eine **Eigenschaft** setzt, ignoriert Qt die
  entsprechende Item-Methode. `background-color` dort ⇒ `setBackground()` wirkungslos;
  `color` dort ⇒ `setForeground()` wirkungslos. Deshalb steht in der `::item`-Regel
  bewusst kein `color`, und Mitarbeiterfarben laufen über ein **Icon**
  (`farbpunkt()` in [mitarbeiter.py](mitarbeiter.py)) statt über den Zellenhintergrund —
  Icons werden immer gezeichnet.
* Selektoren wie `QFrame#karte > QWidget` haben höhere Spezifität als `QPushButton` und
  machen Buttons unsichtbar. Für durchsichtige Layout-Container stattdessen
  `setObjectName("transparent")` verwenden.
* `::down-arrow` braucht ein echtes Bild; ein per `border`-Trick gebauter Pfeil wird als
  grauer Block gerendert. Den Pfeil zeichnet Qt selbst.

### Bedienung des Mitarbeiter-Tabs

Aktionen sind an der Zeile erreichbar, nicht nur über die Buttons: Doppelklick =
bearbeiten, Rechtsklick = Kontextmenü (bearbeiten, Farbe ändern, ignorieren umschalten,
löschen), `Entf` = löschen. `gewaehlter_mitarbeiter()` ist der einzige Weg zur Auswahl;
`lade_mitarbeiter(auswahl_id)` hält die Markierung über einen Reload hinweg.

## Bekannte Schwachstellen

Beim Anfassen der betroffenen Stellen mitbeheben, statt darum herum zu bauen:

1. **`punkte_berechnen` ist toter Code** ([sollistwidget.py](sollistwidget.py#L253)) —
   Duplikat von `punkte_ist_pro_tag` ohne Aufrufer.
2. **Feiertags-API ohne Fallback** — `FeiertageAPI` wirft bei fehlender Netzverbindung
   durch bis in die UI; der Cache lebt nur im Prozess. Ein Request pro Jahr, aber
   `is_feiertag_in_land` wird pro Tag pro Mitarbeiter aufgerufen.
3. **N+1-Queries** — `punkte_ist_pro_tag` setzt zwei Queries pro Tag ab,
   `verteile_sollpunkte_auf_mitarbeiter` eine weitere. Bei großen Zeiträumen spürbar.
4. **Keine Constraints** — kein `UNIQUE(datum, mitarbeiter_id)`, kein
   `ON DELETE CASCADE`. Löschen eines Mitarbeiters lässt verwaiste Kalendereinträge
   zurück, die den JOIN in `lade_alle_eintraege` still ausfiltern — sie zählen aber
   weiterhin im `COUNT(*)` von `punkte_ist_pro_tag` mit und verfälschen dadurch die
   Punkte der übrigen Mitarbeiter.
5. **`individuelle_punkte` ist als INTEGER deklariert, wird aber als Float verwendet**
   — der Dialog validiert inzwischen auf Zahlen mit zwei Nachkommastellen, die
   Spaltendeklaration passt aber noch nicht dazu (SQLite toleriert es).

Bereits behoben (nicht erneut melden): Debug-Log in `aktualisiere_tabelle`,
Mitarbeiter-Reload im Kalender, Validierung der individuellen Punkte,
`start > end`-Prüfung, fehlende `.gitignore`, verschluckte Exceptions in
`MitarbeiterWidget`.
