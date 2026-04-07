import os
import json
import time
import logging
import threading
from dotenv import load_dotenv

from config import TELEGRAM_TOKEN
from database import JobsDatabase
from telegram_bot import TelegramBot
from MostaqlScraper import MostaqlScraper
from KhamsatScraper import KhamsatScraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JobsBot:
    def __init__(self):
        self.db = JobsDatabase()

        github_actions = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"
        polling_enabled = not github_actions

        self.bot = TelegramBot(
            TELEGRAM_TOKEN,
            self.db,
            polling_enabled=polling_enabled
        )

        self.scrapers = {
            "mostaql": MostaqlScraper(),
            "khamsat_requests": KhamsatScraper(),
        }

        self.state_file = "jobs_state.json"
        self.sent_jobs = self.load_state()

        self.scrape_interval = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "60"))
        self.stop_event = threading.Event()

    def load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
        except Exception as e:
            logger.error(f"load_state error: {e}")
        return set()

    def save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self.sent_jobs)), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"save_state error: {e}")

    def build_unique_key(self, platform: str, job: dict) -> str:
        job_id = (job.get("job_id") or "").strip()
        url = (job.get("url") or job.get("link") or "").strip()

        if job_id:
            return f"{platform}:{job_id}"

        return f"{platform}:{url}"

    def scrape_all(self):
        logger.info("=" * 80)
        logger.info("بدء البحث في كل المواقع...")

        try:
            subs = self.db.get_subscribers()
            logger.info(f"عدد المشتركين الحالي = {len(subs)}")
        except Exception as e:
            logger.error(f"خطأ في قراءة المشتركين: {e}")

        total_new = 0

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"فحص المصدر: {name}")
                jobs = scraper.search_jobs() or []
                logger.info(f"{name}: عدد النتائج الراجعة = {len(jobs)}")

                for job in jobs:
                    try:
                        job["platform"] = name

                        if not job.get("url") and job.get("link"):
                            job["url"] = job["link"]

                        unique_key = self.build_unique_key(name, job)

                        if not unique_key or unique_key.endswith(":"):
                            logger.warning(f"تم تخطي وظيفة بدون مفتاح فريد: {job.get('title', '')[:60]}")
                            continue

                        if unique_key in self.sent_jobs:
                            logger.info(f"مكرر (state): {job.get('title', '')[:70]}")
                            continue

                        saved = self.db.save_job(name, job)

                        if saved:
                            total_new += 1
                            self.sent_jobs.add(unique_key)
                            self.save_state()

                            logger.info(f"تم حفظ فرصة جديدة من {name}: {job.get('title', '')[:70]}")
                            self.bot.notify_subscribers(job)
                        else:
                            logger.info(f"فرصة مكررة في DB: {job.get('title', '')[:70]}")
                            self.sent_jobs.add(unique_key)
                            self.save_state()

                    except Exception as e:
                        logger.error(f"خطأ أثناء حفظ/إرسال فرصة من {name}: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"خطأ أثناء تشغيل {name}: {e}", exc_info=True)

        logger.info(f"إجمالي الفرص الجديدة = {total_new}")
        self.show_db_status()
        logger.info("=" * 80)

    def show_db_status(self):
        try:
            jobs = self.db.get_new_jobs(limit=10)
            logger.info(f"آخر الوظائف في DB = {len(jobs)}")

            for job in jobs[:5]:
                logger.info(f"{job.get('platform', '')} | {job.get('title', '')[:60]}")

        except Exception as e:
            logger.error(f"show_db_status error: {e}", exc_info=True)

    def run_once(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN غير موجود")

        logger.info("تشغيل دورة واحدة...")
        self.scrape_all()

    def run_github_actions_mode(self, cycles=5, sleep_seconds=60):
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN غير موجود")

        logger.info("GitHub Actions mode started")

        for i in range(cycles):
            logger.info(f"Cycle {i + 1}/{cycles} started")
            try:
                self.scrape_all()
            except Exception as e:
                logger.exception(f"خطأ في الدورة {i + 1}: {e}")

            if i < cycles - 1:
                logger.info(f"انتظار {sleep_seconds} ثانية قبل الدورة التالية...")
                time.sleep(sleep_seconds)

        logger.info("GitHub Actions mode finished")

    def scraping_loop(self):
        logger.info(f"Scraping loop started. Interval = {self.scrape_interval} seconds")

        while not self.stop_event.is_set():
            try:
                self.scrape_all()
            except Exception as e:
                logger.exception(f"خطأ داخل scraping_loop: {e}")

            if self.stop_event.wait(self.scrape_interval):
                break

        logger.info("Scraping loop stopped")

    def run_polling_mode(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN غير موجود")

        logger.info("Polling mode started")

        scraper_thread = threading.Thread(target=self.scraping_loop, daemon=True)
        scraper_thread.start()

        self.bot.run()

    def stop(self):
        self.stop_event.set()


if __name__ == "__main__":
    bot = JobsBot()

    github_actions = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"

    try:
        if github_actions:
            bot.run_github_actions_mode(cycles=5, sleep_seconds=60)
        else:
            bot.run_polling_mode()
    except KeyboardInterrupt:
        bot.stop()
        logger.info("تم إيقاف البوت")
    except Exception as e:
        bot.stop()
        logger.exception(f"Fatal error: {e}")
        raise
