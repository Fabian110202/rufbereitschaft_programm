import sqlite3
from sqlite3 import Error

class Datenbank:
    def __init__(self, datei='datenbank/rufbereitschaft.sqlite'):
        self.datei = datei
        self.conn = None
        self.cursor = None
        self.verbinde()
        self.erstelle_tabellen()

    def verbinde(self):
        try:
            self.conn = sqlite3.connect(self.datei)
            self.conn.row_factory = sqlite3.Row  # Für dict-ähnliche Rückgabe
            self.cursor = self.conn.cursor()
            print("SQLite-Verbindung erfolgreich.")
        except Error as e:
            print(f"Fehler bei Verbindung zur SQLite-DB: {e}")

    def schliesse_verbindung(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def erstelle_tabellen(self):
        mitarbeiter_sql = """
        CREATE TABLE IF NOT EXISTS mitarbeiter (
            mitarbeiter_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mitarbeiter_vorname TEXT DEFAULT NULL,
            mitarbeiter_nachname TEXT DEFAULT NULL,
            mitarbeiter_eintritt TEXT DEFAULT NULL,
            mitarbeiter_farbe TEXT DEFAULT '#ffffff'
        );
        """

        kalender_sql = """
        CREATE TABLE IF NOT EXISTS kalender_mitarbeiter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT NOT NULL,
            mitarbeiter_id INTEGER NOT NULL,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mitarbeiter_id) REFERENCES mitarbeiter(mitarbeiter_id)
        );
        """

        trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS update_kalender_mitarbeiter_timestamp
        AFTER UPDATE ON kalender_mitarbeiter
        FOR EACH ROW
        BEGIN
            UPDATE kalender_mitarbeiter SET aktualisiert_am = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """

        self.cursor.execute(mitarbeiter_sql)
        self.cursor.execute(kalender_sql)
        self.cursor.execute(trigger_sql)
        self.conn.commit()

    def lade_mitarbeiter(self):
        query = "SELECT mitarbeiter_id, mitarbeiter_vorname, mitarbeiter_nachname, mitarbeiter_eintritt, mitarbeiter_farbe FROM mitarbeiter"
        self.cursor.execute(query)
        return [dict(row) for row in self.cursor.fetchall()]

    def fuege_mitarbeiter_hinzu(self, vorname, nachname, eintritt, farbe):
        query = """
        INSERT INTO mitarbeiter (mitarbeiter_vorname, mitarbeiter_nachname, mitarbeiter_eintritt, mitarbeiter_farbe)
        VALUES (?, ?, ?, ?)
        """
        self.cursor.execute(query, (vorname, nachname, eintritt, farbe))
        self.conn.commit()

    def aktualisiere_mitarbeiter(self, mitarbeiter_id, vorname, nachname, eintritt, farbe):
        query = """
        UPDATE mitarbeiter
        SET mitarbeiter_vorname = ?, mitarbeiter_nachname = ?, mitarbeiter_eintritt = ?, mitarbeiter_farbe = ?
        WHERE mitarbeiter_id = ?
        """
        self.cursor.execute(query, (vorname, nachname, eintritt, farbe, mitarbeiter_id))
        self.conn.commit()

    def loesche_mitarbeiter(self, mitarbeiter_id):
        query = "DELETE FROM mitarbeiter WHERE mitarbeiter_id = ?"
        self.cursor.execute(query, (mitarbeiter_id,))
        self.conn.commit()

    def lade_kalender_eintraege(self, datum):
        query = """
        SELECT k.id, k.datum, k.mitarbeiter_id, m.mitarbeiter_vorname, m.mitarbeiter_nachname
        FROM kalender_mitarbeiter k
        JOIN mitarbeiter m ON k.mitarbeiter_id = m.mitarbeiter_id
        WHERE k.datum = ?
        """
        self.cursor.execute(query, (datum,))
        return [dict(row) for row in self.cursor.fetchall()]

    def fuege_kalender_eintrag_hinzu(self, datum, mitarbeiter_id):
        query = "INSERT INTO kalender_mitarbeiter (datum, mitarbeiter_id) VALUES (?, ?)"
        self.cursor.execute(query, (datum, mitarbeiter_id))
        self.conn.commit()

    def aktualisiere_kalender_eintrag(self, eintrag_id, neues_datum, neue_mitarbeiter_id):
        query = """
        UPDATE kalender_mitarbeiter
        SET datum = ?, mitarbeiter_id = ?
        WHERE id = ?
        """
        self.cursor.execute(query, (neues_datum, neue_mitarbeiter_id, eintrag_id))
        self.conn.commit()
