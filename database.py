import sqlite3

class JobsDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("jobs.db", check_same_thread=False)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY
        )
        """)

    def exists(self, job_id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,))
        return cur.fetchone() is not None

    def add(self, job_id: str):
        self.conn.execute(
            "INSERT OR IGNORE INTO jobs (id) VALUES (?)",
            (job_id,)
        )
        self.conn.commit()
