import requests
from bs4 import BeautifulSoup
import re

KEYWORDS = [
    "excel", "power bi", "dashboard",
    "اكسل", "داشبورد", "تحليل بيانات",
    "sql", "python", "scraping","web scrapping","سحب بيانات","Excel"
]


class KhamsatScraper:
    URL = "https://khamsat.com/community/requests"

    def search_jobs(self):
        jobs = []

        res = requests.get(self.URL)
        soup = BeautifulSoup(res.text, "html.parser")

        links = soup.select("a[href*='/community/requests/']")

        seen = set()

        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href")

            if not title or not href:
                continue

            full_url = "https://khamsat.com" + href

            job_id = re.search(r"/requests/(\d+)", href)
            if not job_id:
                continue

            job_id = job_id.group(1)

            if job_id in seen:
                continue

            seen.add(job_id)

            text = title.lower()

            if not any(k in text for k in KEYWORDS):
                continue

            jobs.append({
                "job_id": job_id,
                "title": title,
                "url": full_url,
                "platform": "khamsat"
            })

        return jobs
