import sqlite3
import json
from datetime import datetime
from typing import List, Dict

class JobsDatabase:
    def __init__(self, db_path="jobs.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                title TEXT,
                url TEXT UNIQUE,
                price TEXT,
                description TEXT,
                posted_date TEXT,
                scraped_date TEXT,
                notified_users TEXT DEFAULT '[]'
            )
        ''')
        conn.commit()
        conn.close()
    
    def save_job(self, platform: str, job_data: Dict) -> bool:
        """Save job if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO jobs 
            (platform, title, url, price, description, posted_date, scraped_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            platform,
            job_data['title'],
            job_data['url'],
            job_data.get('price', 'غير محدد'),
            job_data.get('description', ''),
            job_data.get('posted_date', ''),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def get_new_jobs(self) -> List[Dict]:
        """Get jobs from last 24 hours"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM jobs 
            WHERE scraped_date > datetime('now', '-1 day')
            ORDER BY scraped_date DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        jobs = []
        for row in rows:
            jobs.append({
                'id': row[0],
                'platform': row[1],
                'title': row[2],
                'url': row[3],
                'price': row[4],
                'description': row[5],
                'posted_date': row[6],
                'scraped_date': row[7]
            })
        return jobs
    
    def mark_notified(self, job_id: int, user_id: int):
        """Mark job as notified for specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT notified_users FROM jobs WHERE id = ?', (job_id,))
        result = cursor.fetchone()
        
        if result:
            users = json.loads(result[0])
            if user_id not in users:
                users.append(user_id)
                cursor.execute('UPDATE jobs SET notified_users = ? WHERE id = ?', 
                             (json.dumps(users), job_id))
                conn.commit()
        
        conn.close()