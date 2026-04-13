import sqlite3
import logging

logger = logging.getLogger(__name__)


class JobsDatabase:
    def __init__(self, db_name="jobs.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            site TEXT
        )
        """)
        self.conn.commit()

    def job_exists(self, job_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,))
        return cursor.fetchone() is not None

    def add_job(self, job):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO jobs (id, title, link, site) VALUES (?, ?, ?, ?)",
                (
                    str(job.get("id")),
                    str(job.get("title")),
                    str(job.get("link")),
                    str(job.get("site"))
                )
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"DB insert error: {e}")

    def get_new_jobs(self, jobs):
        new_jobs = []
        try:
            for job in jobs:
                job_id = str(job.get("id"))

                if not job_id:
                    continue

                if not self.job_exists(job_id):
                    self.add_job(job)
                    new_jobs.append(job)

        except Exception as e:
            logger.error(f"database:get_new_jobs error: {e}")

        return new_jobs
