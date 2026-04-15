import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import List, Dict
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class MostaqlScraper:
    BASE_URL = "https://mostaql.com"
    PROJECTS_URL = "https://mostaql.com/projects"

    KEYWORDS = [
        "excel", "microsoft excel", "power bi", "dashboard",
        "اكسل", "إكسل", "اكسيل", "داشبورد", "داش بورد",
        "لوحة تحكم", "لوحه تحكم",
        "تحليل بيانات", "data analysis", "data analytics",
        "sql", "python", "scraping", "web scraping",
        "data extraction", "سحب بيانات", "استخراج بيانات",
        "جمع بيانات", "google sheets", "جوجل شيت",
        "power query", "باور كويري", "eda", "automation",
        "csv", "xlsx", "kpi", "kpis", "تقارير", "تقرير"
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://mostaql.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""

        text = text.lower().strip()

        arabic_map = {
            "أ": "ا", "إ": "ا", "آ": "ا",
            "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"
        }
        for old, new in arabic_map.items():
            text = text.replace(old, new)

        text = re.sub(r"[\u0617-\u061A\u064B-\u0652]", "", text)
        text = re.sub(r"[^\w\s\+\#]", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def matches_keywords(self, title: str) -> bool:
        text = self.normalize_text(title)
        return any(self.normalize_text(k) in text for k in self.KEYWORDS)

    def canonicalize_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

    def extract_project_id(self, href: str) -> str:
        match = re.search(r"/project/(\d+)", href or "")
        return match.group(1) if match else ""

    def search_jobs(self) -> List[Dict]:
        jobs: List[Dict] = []

        try:
            logger.info("جلب صفحة مستقل...")
            response = self.session.get(self.PROJECTS_URL, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            links = soup.find_all("a", href=re.compile(r"/project/\d+"))

            seen_ids = set()

            for link in links:
                try:
                    href = (link.get("href") or "").strip()
                    title = (
                        link.get_text(" ", strip=True)
                        or link.get("title", "")
                        or link.get("aria-label", "")
                        or ""
                    ).strip()

                    if not href or not title:
                        continue

                    full_url = urljoin(self.BASE_URL, href)
                    full_url = self.canonicalize_url(full_url)

                    job_id = self.extract_project_id(full_url)
                    if not job_id or job_id in seen_ids:
                        continue

                    seen_ids.add(job_id)

                    if not self.matches_keywords(title):
                        continue

                    jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "url": full_url,
                        "link": full_url,
                        "description": "",
                        "price": "غير محدد",
                        "platform": "mostaql"
                    })

                except Exception as e:
                    logger.warning(f"تخطي عنصر من مستقل بسبب خطأ: {e}")
                    continue

            jobs.sort(key=lambda x: int(x.get("job_id", 0)), reverse=True)
            logger.info(f"Mostaql jobs found = {len(jobs)}")

        except Exception as e:
            logger.error(f"Mostaql scraper error: {e}")

        return jobs
