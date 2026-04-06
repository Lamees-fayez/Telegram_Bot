import re
import logging
from typing import List, Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class KhamsatScraper:
    BASE_URL = "https://khamsat.com/community/requests"

    KEYWORDS = [
        "excel", "microsoft excel", "power bi", "dashboard", "داش بورد",
        "اكسل", "إكسل", "تحليل بيانات", "data analysis", "eda",
        "sql", "python", "automation", "scraping", "web scraping"
    ]

    def _normalize(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def _matches_keywords(self, title: str, desc: str = "") -> bool:
        haystack = self._normalize(f"{title} {desc}")
        return any(k.lower() in haystack for k in self.KEYWORDS)

    def search_jobs(self) -> List[Dict]:
        jobs: List[Dict] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1366, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            try:
                logger.info("فتح صفحة خمسات...")
                page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)

                # ندي الصفحة فرصة تحمل العناصر الديناميكية
                page.wait_for_timeout(4000)

                # ننزل لأسفل قليلًا لو الصفحة بتأخر بعض العناصر
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(2000)

                # بدائل سيليكترز لأن تصميم الموقع قد يختلف
                cards = page.locator("a[href*='/community/requests/']").all()

                seen = set()

                for card in cards:
                    try:
                        href = card.get_attribute("href") or ""
                        title = card.inner_text(timeout=3000).strip()

                        if not href or not title:
                            continue

                        if not href.startswith("http"):
                            href = "https://khamsat.com" + href

                        # تنظيف عنوان مكرر
                        key = (title[:120], href)
                        if key in seen:
                            continue
                        seen.add(key)

                        if not self._matches_keywords(title):
                            continue

                        jobs.append({
                            "title": title,
                            "url": href,
                            "link": href,
                            "description": "",
                            "price": "",
                            "platform": "khamsat_requests"
                        })

                    except Exception as e:
                        logger.warning(f"تخطي عنصر بسبب خطأ: {e}")
                        continue

                logger.info(f"Khamsat Playwright jobs found = {len(jobs)}")

            except PlaywrightTimeoutError:
                logger.error("Timeout أثناء تحميل صفحة خمسات")
            except Exception as e:
                logger.error(f"Khamsat scraper error: {e}")
            finally:
                context.close()
                browser.close()

        return jobs
