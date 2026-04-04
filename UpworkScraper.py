import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
from typing import List, Dict
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class UpworkScraper:
    BASE_URL = "https://www.upwork.com"
    SEARCH_URL = "https://www.upwork.com/nx/search/jobs/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Referer": "https://www.upwork.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        self.keywords = [
            "excel", "power bi", "powerbi",
            "dashboard", "data analysis", "data analyst",
            "data entry", "web scraping", "scraping",
            "python", "sql", "report", "reporting",
            "google sheets", "automation"
        ]

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def is_relevant(self, text: str) -> bool:
        text = self.normalize_text(text)
        return any(keyword in text for keyword in self.keywords)

    def build_search_urls(self) -> List[str]:
        return [
            self.SEARCH_URL,
            f"{self.SEARCH_URL}?q=excel",
            f"{self.SEARCH_URL}?q=power%20bi",
            f"{self.SEARCH_URL}?q=data%20analysis",
            f"{self.SEARCH_URL}?q=web%20scraping",
        ]

    def extract_price(self, text: str) -> str:
        if not text:
            return "غير محدد"

        patterns = [
            r"\$[\d,]+(?:\.\d+)?(?:\s*-\s*\$[\d,]+(?:\.\d+)?)?",
            r"Hourly:\s*\$[\d,]+(?:\.\d+)?",
            r"Fixed[- ]price",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        return "غير محدد"

    def extract_posted_date(self, text: str) -> str:
        if not text:
            return ""

        patterns = [
            r"\b\d+\s+minutes?\s+ago\b",
            r"\b\d+\s+hours?\s+ago\b",
            r"\b\d+\s+days?\s+ago\b",
            r"\bYesterday\b",
            r"\bToday\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        return ""

    def collect_job_cards(self, soup: BeautifulSoup) -> List:
        selectors = [
            "article",
            "section",
            "div[data-test='JobTile']",
            "div.job-tile",
            "div[data-qa='job-tile']",
        ]

        cards = []
        seen = set()

        for selector in selectors:
            try:
                found = soup.select(selector)
                for card in found:
                    card_id = str(card)[:300]
                    if card_id not in seen:
                        seen.add(card_id)
                        cards.append(card)
            except Exception:
                continue

        return cards

    def extract_job_from_card(self, card) -> Dict:
        text = card.get_text(" ", strip=True)

        title = ""
        url = ""

        # محاولة استخراج اللينك والعنوان
        links = card.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")
            link_text = link.get_text(" ", strip=True)

            if "/jobs/" in href or "/job/" in href or "/freelance-jobs/" in href:
                url = urljoin(self.BASE_URL, href)
                if link_text and len(link_text) > 5:
                    title = link_text
                    break

        # fallback لو ما لقاش
        if not title:
            for tag in card.find_all(["h2", "h3", "h4", "a"]):
                txt = tag.get_text(" ", strip=True)
                if txt and len(txt) > 5:
                    title = txt
                    break

        if not title:
            return {}

        price = self.extract_price(text)
        posted_date = self.extract_posted_date(text)

        description = text[:700] if text else ""

        return {
            "title": title[:120],
            "url": url,
            "price": price,
            "description": description,
            "posted_date": posted_date
        }

    def search_jobs(self) -> List[Dict]:
        logger.info("🔍 البحث في Upwork عن آخر الوظائف المطابقة...")
        all_jobs = []
        seen_urls = set()
        search_urls = self.build_search_urls()

        for search_url in search_urls:
            try:
                logger.info(f"🌐 Upwork URL: {search_url}")
                response = self.session.get(search_url, timeout=20)

                if response.status_code != 200:
                    logger.warning(f"Upwork returned status {response.status_code} for {search_url}")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                cards = self.collect_job_cards(soup)
                logger.info(f"📦 عدد العناصر المبدئي من Upwork: {len(cards)}")

                for card in cards:
                    try:
                        job = self.extract_job_from_card(card)
                        if not job:
                            continue

                        searchable_text = f"{job.get('title', '')} {job.get('description', '')}"

                        if not self.is_relevant(searchable_text):
                            continue

                        job_url = job.get("url", "").strip()

                        # لو مفيش لينك، نسمح بيه مرة واحدة حسب العنوان
                        unique_key = job_url if job_url else job.get("title", "").strip().lower()
                        if not unique_key or unique_key in seen_urls:
                            continue

                        seen_urls.add(unique_key)

                        job["title"] = f"🆕 وظيفة Upwork: {job['title']}"
                        all_jobs.append(job)
                        logger.info(f"✅ مطابق Upwork: {job['title'][:70]}")

                    except Exception as e:
                        logger.warning(f"تخطي عنصر Upwork: {e}")
                        continue

                time.sleep(random.uniform(1, 2))

            except Exception as e:
                logger.error(f"❌ خطأ في Upwork URL {search_url}: {e}")
                continue

        # غالبًا Upwork الأحدث يظهر أولًا، فنأخذ أول 10 مطابقين
        final_jobs = all_jobs[:10]
        logger.info(f"🎯 تم جلب {len(final_jobs)} وظيفة من Upwork (آخر 10 مطابقين)")
        return final_jobs
