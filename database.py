def save_job(self, platform: str, job: Dict) -> bool:
    conn = None
    try:
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO jobs (platform, title, url, price, description, posted_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            platform,
            job.get("title", ""),
            job.get("url", ""),
            job.get("price", ""),
            job.get("description", ""),
            job.get("posted_date", "")
        ))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.error(f"save_job error: {e}")
        return False
    finally:
        if conn:
            conn.close()
