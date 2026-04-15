import sqlite3
import logging

logger = logging.getLogger(__name__)


class JobsDatabase:
    def __init__(self, db_name="jobs.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            unique_key TEXT PRIMARY KEY,
            job_id TEXT,
            title TEXT,
            url TEXT,
            platform TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.conn.commit()

    def job_exists(self, unique_key: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM jobs WHERE unique_key = ? LIMIT 1", (unique_key,))
        return cursor.fetchone() is not None

    def add_job(self, job: dict, unique_key: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO jobs (unique_key, job_id, title, url, platform)
            VALUES (?, ?, ?, ?, ?)
        """, (
            unique_key,
            str(job.get("job_id", "")),
            str(job.get("title", "")),
            str(job.get("url", "")),
            str(job.get("platform", "unknown")),
        ))
        self.conn.commit()
