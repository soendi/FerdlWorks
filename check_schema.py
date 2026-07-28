import sqlite3
conn = sqlite3.connect(r'C:\Users\sonde\AppData\Roaming\FerdlWorks\ferdlworks.db')
cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='positions'")
print(cur.fetchone()[0])