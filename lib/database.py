import sqlite3
import os
from datetime import datetime
from lib.logger import get_logger


def get_db_path():
    """Get the database path — always %APPDATA%/FerdlWorks/ferdlworks.db."""
    base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FerdlWorks")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "ferdlworks.db")


DB_PATH = get_db_path()


def get_db():
    return Database()


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.logger = get_logger()
        self._create_tables()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _create_tables(self):
        conn = self._connect()
        try:
            # Migration: add missing columns for older DBs
            for col, dtype in [("merge_tools", "TEXT DEFAULT '1'"),
                               ("merge_tool_name", "TEXT DEFAULT 'Werkzeug'"),
                               ("round_tools", "TEXT DEFAULT '1'")]:
                try:
                    conn.execute(f"ALTER TABLE documents ADD COLUMN {col} {dtype}")
                except sqlite3.OperationalError:
                    pass  # column already exists
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    first_name TEXT DEFAULT '',
                    last_name TEXT DEFAULT '',
                    street TEXT DEFAULT '',
                    zip TEXT DEFAULT '',
                    city TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    price REAL NOT NULL DEFAULT 0,
                    price_unit TEXT NOT NULL DEFAULT 'h',
                    note TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    price_per_m2 REAL NOT NULL DEFAULT 0,
                    note TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_type TEXT NOT NULL CHECK(doc_type IN ('RG','LS')),
                    doc_number TEXT NOT NULL,
                    customer_id INTEGER NOT NULL,
                    date TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                    discount_type TEXT DEFAULT 'percent',
                    discount_value REAL DEFAULT 0,
                    total_net REAL DEFAULT 0,
                    total_tax REAL DEFAULT 0,
                    total_gross REAL DEFAULT 0,
                    note TEXT DEFAULT '',
                    internal_note TEXT DEFAULT '',
                    paid TEXT DEFAULT '0',
                    due_date TEXT DEFAULT '',
                    print_note TEXT DEFAULT '1',
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                );

                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL,
                    pos_type TEXT NOT NULL CHECK(pos_type IN('tool','material')),
                    ref_id INTEGER,
                    description TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 1,
                    unit TEXT DEFAULT '',
                    price_per_unit REAL DEFAULT 0,
                    total REAL DEFAULT 0,
                    sort_order INTEGER DEFAULT 0,
                    orig_price TEXT DEFAULT '',
                    orig_price_unit TEXT DEFAULT '',
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS doc_counter (
                    doc_type TEXT PRIMARY KEY,
                    current_number INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS texts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            # Migration: documents – paid, due_date, discount_type, print_note
            for col in ("paid", "due_date", "print_note", "internal_note"):
                try:
                    conn.execute(f"ALTER TABLE documents ADD COLUMN {col} TEXT DEFAULT ''")
                except sqlite3.OperationalError:
                    pass
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN discount_type TEXT DEFAULT 'percent'")
            except sqlite3.OperationalError:
                pass
            # Migration: orig_price / orig_price_unit für EP-Einheit aus Verwaltung
            for col in ("orig_price", "orig_price_unit"):
                try:
                    conn.execute(f"ALTER TABLE positions ADD COLUMN {col} TEXT DEFAULT ''")
                except sqlite3.OperationalError:
                    pass  # Spalte existiert bereits
            # Migration: pos_type CHECK um 'text' erweitern + Spalten ergänzen
            conn.execute("PRAGMA foreign_keys=OFF")
            try:
                conn.execute("INSERT INTO positions (doc_id, pos_type, description) VALUES (-2, 'text', '__migrate__')")
                conn.execute("DELETE FROM positions WHERE description='__migrate__'")
            except sqlite3.IntegrityError:
                cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='positions'")
                old_sql = cur.fetchone()["sql"]
                new_sql = old_sql.replace(
                    "CHECK(pos_type IN('tool','material'))",
                    "CHECK(pos_type IN('tool','material','text'))"
                )
                if "orig_price" not in old_sql:
                    new_sql = new_sql.replace(
                        "sort_order INTEGER DEFAULT 0",
                        "sort_order INTEGER DEFAULT 0,\n                    orig_price TEXT DEFAULT '',\n                    orig_price_unit TEXT DEFAULT ''"
                    )
                conn.execute("PRAGMA writable_schema=ON")
                conn.execute("UPDATE sqlite_master SET sql=? WHERE type='table' AND name='positions'", (new_sql,))
                conn.execute("PRAGMA writable_schema=OFF")
            conn.execute("PRAGMA foreign_keys=ON")
        finally:
            conn.close()

    # --- Kunden ---
    def customer_search(self, query=""):
        conn = self._connect()
        try:
            like = f"%{query}%"
            rows = conn.execute("""
                SELECT * FROM customers
                WHERE company LIKE ? OR last_name LIKE ? OR first_name LIKE ?
                  OR city LIKE ? OR zip LIKE ? OR street LIKE ? OR email LIKE ? OR phone LIKE ?
                ORDER BY company, last_name
            """, (like, like, like, like, like, like, like, like)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def customer_get(self, cid):
        conn = self._connect()
        try:
            r = conn.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def customer_save(self, data):
        conn = self._connect()
        try:
            keys = ["company", "first_name", "last_name", "street", "zip", "city",
                    "phone", "email", "note"]
            if data.get("id"):
                sets = ", ".join(f"{k}=?" for k in keys)
                vals = [data.get(k, "") for k in keys] + [data["id"]]
                conn.execute(f"UPDATE customers SET {sets}, updated_at=datetime('now','localtime') WHERE id=?", vals)
            else:
                ks = ", ".join(keys)
                qs = ", ".join("?" for _ in keys)
                vals = [data.get(k, "") for k in keys]
                cur = conn.execute(f"INSERT INTO customers ({ks}) VALUES ({qs})", vals)
                data["id"] = cur.lastrowid
            conn.commit()
            return data
        finally:
            conn.close()

    def customer_delete(self, cid):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM customers WHERE id=?", (cid,))
            conn.commit()
        finally:
            conn.close()

    # --- Werkzeuge ---
    def tool_search(self, query=""):
        conn = self._connect()
        try:
            like = f"%{query}%"
            rows = conn.execute("SELECT * FROM tools WHERE name LIKE ? OR description LIKE ? ORDER BY name",
                                (like, like)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def tool_get(self, tid):
        conn = self._connect()
        try:
            r = conn.execute("SELECT * FROM tools WHERE id=?", (tid,)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def tool_save(self, data):
        conn = self._connect()
        try:
            keys = ["name", "description", "price", "price_unit", "note"]
            if data.get("id"):
                sets = ", ".join(f"{k}=?" for k in keys)
                vals = [data.get(k, "") for k in keys] + [data["id"]]
                conn.execute(f"UPDATE tools SET {sets}, updated_at=datetime('now','localtime') WHERE id=?", vals)
            else:
                ks = ", ".join(keys)
                qs = ", ".join("?" for _ in keys)
                vals = [data.get(k, "") for k in keys]
                cur = conn.execute(f"INSERT INTO tools ({ks}) VALUES ({qs})", vals)
                data["id"] = cur.lastrowid
            conn.commit()
            return data
        finally:
            conn.close()

    def tool_delete(self, tid):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM tools WHERE id=?", (tid,))
            conn.commit()
        finally:
            conn.close()

    # --- Materialien ---
    def material_search(self, query=""):
        conn = self._connect()
        try:
            like = f"%{query}%"
            rows = conn.execute("SELECT * FROM materials WHERE name LIKE ? OR description LIKE ? ORDER BY name",
                                (like, like)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def material_get(self, mid):
        conn = self._connect()
        try:
            r = conn.execute("SELECT * FROM materials WHERE id=?", (mid,)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def material_save(self, data):
        conn = self._connect()
        try:
            keys = ["name", "description", "price_per_m2", "note"]
            if data.get("id"):
                sets = ", ".join(f"{k}=?" for k in keys)
                vals = [data.get(k, "") for k in keys] + [data["id"]]
                conn.execute(f"UPDATE materials SET {sets}, updated_at=datetime('now','localtime') WHERE id=?", vals)
            else:
                ks = ", ".join(keys)
                qs = ", ".join("?" for _ in keys)
                vals = [data.get(k, "") for k in keys]
                cur = conn.execute(f"INSERT INTO materials ({ks}) VALUES ({qs})", vals)
                data["id"] = cur.lastrowid
            conn.commit()
            return data
        finally:
            conn.close()

    def material_delete(self, mid):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM materials WHERE id=?", (mid,))
            conn.commit()
        finally:
            conn.close()

    # --- Texte ---
    def text_search(self, query=""):
        conn = self._connect()
        try:
            like = f"%{query}%"
            rows = conn.execute("SELECT * FROM texts WHERE name LIKE ? ORDER BY name",
                                (like,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def text_get(self, tid):
        conn = self._connect()
        try:
            r = conn.execute("SELECT * FROM texts WHERE id=?", (tid,)).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def text_save(self, data):
        conn = self._connect()
        try:
            keys = ["name", "content"]
            if data.get("id"):
                sets = ", ".join(f"{k}=?" for k in keys)
                vals = [data.get(k, "") for k in keys] + [data["id"]]
                conn.execute(f"UPDATE texts SET {sets}, updated_at=datetime('now','localtime') WHERE id=?", vals)
            else:
                ks = ", ".join(keys)
                qs = ", ".join("?" for _ in keys)
                vals = [data.get(k, "") for k in keys]
                cur = conn.execute(f"INSERT INTO texts ({ks}) VALUES ({qs})", vals)
                data["id"] = cur.lastrowid
            conn.commit()
            return data
        finally:
            conn.close()

    def text_delete(self, tid):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM texts WHERE id=?", (tid,))
            conn.commit()
        finally:
            conn.close()

    # --- Kombinierte Suche (Werkzeug + Material + Text) ---
    def combined_search(self, query=""):
        conn = self._connect()
        try:
            like = f"%{query}%"
            rows = conn.execute("""
                SELECT id, name, 'Werkzeug' as item_type, price, price_unit, 0 as price_per_m2, '' as content
                FROM tools WHERE name LIKE ? OR description LIKE ?
                UNION ALL
                SELECT id, name, 'Material' as item_type, price_per_m2 as price, '' as price_unit, price_per_m2, '' as content
                FROM materials WHERE name LIKE ? OR description LIKE ?
                UNION ALL
                SELECT id, name, 'Text' as item_type, 0 as price, '' as price_unit, 0 as price_per_m2, content
                FROM texts WHERE name LIKE ?
                ORDER BY name LIMIT 100
            """, (like, like, like, like, like)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Dokumente (RG/LS) ---
    def doc_get_next_number(self, doc_type):
        conn = self._connect()
        try:
            cur = conn.execute("SELECT current_number FROM doc_counter WHERE doc_type=?", (doc_type,))
            row = cur.fetchone()
            if row:
                num = row["current_number"] + 1
                conn.execute("UPDATE doc_counter SET current_number=? WHERE doc_type=?", (num, doc_type))
            else:
                num = 1
                conn.execute("INSERT INTO doc_counter (doc_type, current_number) VALUES (?,?)", (doc_type, num))
            conn.commit()
            year = datetime.now().strftime("%Y")
            return f"{doc_type}-{year}-{num:04d}", num
        finally:
            conn.close()

    def doc_save(self, data, positions):
        conn = self._connect()
        try:
            doc_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
            due = data.get("due_date", "")
            if not due:
                from datetime import timedelta
                due = (datetime.strptime(doc_date, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")
            paid = data.get("paid", "0")
            if data.get("id"):
                conn.execute("""UPDATE documents SET customer_id=?, date=?, discount_type=?,
                    discount_value=?, total_net=?, total_tax=?, total_gross=?, note=?,
                    internal_note=?, paid=?, due_date=?, print_note=?,
                    merge_tools=?, merge_tool_name=?, round_tools=? WHERE id=?""",
                    (data["customer_id"], doc_date,
                     data.get("discount_type", "percent"), data.get("discount_value", 0),
                     data.get("total_net", 0), data.get("total_tax", 0),
                     data.get("total_gross", 0), data.get("note", ""),
                     data.get("internal_note", ""), paid, due,
                     data.get("print_note", "1"),
                     "1" if data.get("merge_tools", False) else "0",
                     data.get("merge_tool_name", "Werkzeug"),
                     "1" if data.get("round_tools", False) else "0",
                     data["id"]))
                conn.execute("DELETE FROM positions WHERE doc_id=?", (data["id"],))
                doc_id = data["id"]
            else:
                doc_number, _ = self.doc_get_next_number(data["doc_type"])
                data["doc_number"] = doc_number
                cur = conn.execute("""INSERT INTO documents (doc_type, doc_number, customer_id, date,
                    discount_type, discount_value, total_net, total_tax, total_gross, note,
                    internal_note, paid, due_date, print_note, merge_tools, merge_tool_name, round_tools)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (data["doc_type"], doc_number, data["customer_id"], doc_date,
                     data.get("discount_type", "percent"), data.get("discount_value", 0),
                     data.get("total_net", 0), data.get("total_tax", 0),
                     data.get("total_gross", 0), data.get("note", ""),
                     data.get("internal_note", ""), paid, due,
                     data.get("print_note", "1"),
                     "1" if data.get("merge_tools", False) else "0",
                     data.get("merge_tool_name", "Werkzeug"),
                     "1" if data.get("round_tools", False) else "0"))
                doc_id = cur.lastrowid
            for i, pos in enumerate(positions):
                conn.execute("""INSERT INTO positions (doc_id, pos_type, ref_id, description,
                    quantity, unit, price_per_unit, total, sort_order, orig_price, orig_price_unit)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (doc_id, pos["pos_type"], pos.get("ref_id"), pos["description"],
                     pos.get("quantity", 1), pos.get("unit", ""),
                     pos.get("price_per_unit", 0), pos.get("total", 0), i,
                     pos.get("orig_price", 0), pos.get("orig_price_unit", "")))
            conn.commit()
            return self.doc_get(doc_id)
        finally:
            conn.close()

    def doc_get(self, doc_id):
        conn = self._connect()
        try:
            r = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            if not r:
                return None
            doc = dict(r)
            doc["customer"] = self.customer_get(doc["customer_id"])
            pos_rows = conn.execute("SELECT * FROM positions WHERE doc_id=? ORDER BY sort_order", (doc_id,)).fetchall()
            doc["positions"] = [dict(p) for p in pos_rows]
            return doc
        finally:
            conn.close()

    def doc_search(self, doc_type=None, query=""):
        conn = self._connect()
        try:
            sql = """SELECT d.*, c.company as customer_name, c.city as customer_city,
                     c.last_name as customer_last_name, c.first_name as customer_first_name
                     FROM documents d
                     LEFT JOIN customers c ON d.customer_id = c.id
                     WHERE 1=1"""
            params = []
            if doc_type:
                sql += " AND d.doc_type=?"
                params.append(doc_type)
            if query:
                like = f"%{query}%"
                sql += " AND (d.doc_number LIKE ? OR c.company LIKE ? OR c.last_name LIKE ?)"
                params.extend([like, like, like])
            sql += " ORDER BY d.id DESC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def doc_set_paid(self, doc_id, paid=True):
        conn = self._connect()
        try:
            conn.execute("UPDATE documents SET paid=? WHERE id=?", ("1" if paid else "0", doc_id))
            conn.commit()
        finally:
            conn.close()

    def doc_get_overdue(self):
        conn = self._connect()
        try:
            rows = conn.execute("""SELECT d.*, c.company as customer_name, c.city as customer_city,
                c.last_name as customer_last_name, c.first_name as customer_first_name
                FROM documents d
                LEFT JOIN customers c ON d.customer_id = c.id
                WHERE d.doc_type='RG' AND d.paid='0' AND d.due_date != ''
                AND date(d.due_date) < date('now') ORDER BY d.due_date""").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def doc_delete(self, doc_id):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            conn.commit()
        finally:
            conn.close()

    # --- Einstellungen ---
    def settings_get_all(self):
        conn = self._connect()
        try:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {r["key"]: r["value"] for r in rows}
        finally:
            conn.close()

    def settings_set(self, key, value):
        conn = self._connect()
        try:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
            conn.commit()
        finally:
            conn.close()

    def settings_set_multi(self, data):
        conn = self._connect()
        try:
            for k, v in data.items():
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, str(v)))
            conn.commit()
        finally:
            conn.close()

    # --- Backup / Restore ---
    def backup_to(self, target_path):
        conn = self._connect()
        try:
            backup = sqlite3.connect(target_path)
            conn.backup(backup)
            backup.close()
            self.logger.info(f"Datenbank gesichert nach: {target_path}")
            return True
        except Exception as ex:
            self.logger.error(f"Backup fehlgeschlagen: {ex}")
            return False
        finally:
            conn.close()

    def restore_from(self, source_path):
        if not os.path.exists(source_path):
            self.logger.error(f"Backup-Datei nicht gefunden: {source_path}")
            return False
        conn = self._connect()
        try:
            source = sqlite3.connect(source_path)
            source.backup(conn)
            source.close()
            self.logger.info(f"Datenbank wiederhergestellt von: {source_path}")
            return True
        except Exception as ex:
            self.logger.error(f"Wiederherstellung fehlgeschlagen: {ex}")
            return False
        finally:
            conn.close()
