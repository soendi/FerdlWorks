import sqlite3
conn = sqlite3.connect(r'C:\Users\sonde\AppData\Roaming\FerdlWorks\ferdlworks.db')
conn.execute("PRAGMA foreign_keys=OFF")

# Backup existing data
rows = conn.execute("SELECT * FROM positions").fetchall()

# Drop and recreate
conn.execute("DROP TABLE positions")
conn.execute("""
    CREATE TABLE positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER NOT NULL,
        pos_type TEXT NOT NULL CHECK(pos_type IN('tool','material','text')),
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
    )
""")

# Restore data
for r in rows:
    conn.execute("""INSERT INTO positions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", r)

conn.execute("PRAGMA foreign_keys=ON")
conn.commit()
print("Table recreated with 'text' in CHECK constraint")