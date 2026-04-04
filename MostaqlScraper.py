import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
from typing import List, Dict
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class MostaqlScraper:
    BASE_URL = "https://mostaql.com"
    PROJECTS_URL = "https://mostaql.com/projects"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Referer": "https://mostaql.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        self.keywords = [
            "excel", "اكسل",
            "power bi", "powerbi",
            "dashboard", "داشبورد", "داش بورد",
            "تحليل بيانات", "تحليل", "بيانات",
            "data analysis", "data analyst",
            "web scraping", "scraping", "scraper", "سحب بيانات"
        ]

    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip().lower()

    def is_relevant(self, text: str) -> bool:
        text = self.normalize_text(text)
        return any(kw.lower() in text for kw in self.keywords)

    def fix_url(self, href: str) -> str:
        if not href:
            return self.PROJECTS_URL
        return urljoin(self.BASE_URL, href)

    def extract_price_from_card(self, card) -> str:
        try:
            text = card.get_text(" ", strip=True)
            price_match = re.search(r'(\d+\s*-\s*\d+\s*\$|\d+\s*\$|\$\s*\d+)', text)
            if price_match:
                return price_match.group(1)
        except Exception:
            pass
        return "غير محدد"

    def extract_price_from_project_page(self, url: str) -> str:
        try:
            time.sleep(random.uniform(1, 2))
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text(" ", strip=True)

            price_patterns = [
                r'ميزانية المشروع[^0-9$]*([\d\.,]+\s*-\s*[\d\.,]+\s*\$)',
                r'ميزانية المشروع[^0-9$]*([\d\.,]+\s*\$)',
                r'Budget[^0-9$]*([\d\.,]+\s*-\s*[\d\.,]+\s*\$)',
                r'Budget[^0-9$]*([\d\.,]+\s*\$)',
            ]

            for pattern in price_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        except Exception as e:
            logger.warning(f"تعذر استخراج السعر من صفحة المشروع: {url} | {e}")

        return "غير محدد"

    def extract_description_from_project_page(self, url: str) -> str:
        try:
            time.sleep(random.uniform(1, 2))
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            possible_blocks = soup.find_all(["p", "div"])
            for block in possible_blocks:
                txt = block.get_text(" ", strip=True)
                if txt and len(txt) > 80:
                    return txt[:400]

        except Exception:
            pass

        return ""

    def search_jobs(self) -> List[Dict]:
        jobs = []

        try:
            logger.info("🔍 البحث في مستقل من صفحة المشاريع...")
            response = self.session.get(self.PROJECTS_URL, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # نجمع كل روابط المشاريع المحتملة
            project_links = soup.find_all("a", href=re.compile(r"^/project/\d+"))
            logger.info(f"عدد الروابط المبدئي من مستقل: {len(project_links)}")

            seen_urls = set()

            for link in project_links:
                try:
                    href = link.get("href", "").strip()
                    if not href:
                        continue

                    full_url = self.fix_url(href)

                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    title = (
                        link.get_text(" ", strip=True)
                        or link.get("title", "")
                        or link.get("aria-label", "")
                    ).strip()

                    if not title or len(title) < 5:
                        continue

                    if not self.is_relevant(title):
                        continue

                    card = link.find_parent(["div", "article", "li", "section"])
                    price = "غير محدد"

                    if card:
                        price = self.extract_price_from_card(card)

                    if price == "غير محدد":
                        price = self.extract_price_from_project_page(full_url)

                    job = {
                        "title": f"🆕 مشروع مستقل: {title[:120]}",
                        "url": full_url,
                        "price": price,
                        "description": "",
                        "posted_date": time.strftime("%Y-%m-%d %H:%M")
                    }

                    jobs.append(job)
                    logger.info(f"✅ {title[:60]} -> {full_url}")

                except Exception as e:
                    logger.warning(f"تخطي عنصر في مستقل: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ خطأ في سحب مستقل: {e}")

        # إزالة التكرار
        unique_jobs = []
        seen = set()
        for job in jobs:
            if job["url"] not in seen:
                unique_jobs.append(job)
                seen.add(job["url"])

        logger.info(f"🎯 وجد {len(unique_jobs)} مشروع فريد من مستقل")
        return unique_jobs[:10]
