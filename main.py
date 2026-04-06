import os
import time
import logging
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
        self.bot = TelegramBot(TELEGRAM_TOKEN, self.db)

        self.scrapers = {
            "mostaql": MostaqlScraper(),
            "khamsat_requests": KhamsatScraper(),
        }

    def scrape_all(self):
        logger.info("=" * 80)
        logger.info("بدء البحث في كل المواقع...")

        try:
            subs = self.db.get_subscribers()
            logger.info(f"عدد المشتركين الحالي = {len(subs)}")
        except Exception as e:
            logger.error(f"خطأ في قراءة المشتركين: {e}")
            subs = []

        total_new = 0

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"فحص المصدر: {name}")
                jobs = scraper.search_jobs() or []
                logger.info(f"{name}: عدد النتائج الراجعة = {len(jobs)}")

                for job in jobs:
                    try:
                        job["platform"] = name
                        saved = self.db.save_job(name, job)

                        if saved:
                            total_new += 1
                            logger.info(f"تم حفظ فرصة جديدة من {name}: {job.get('title', '')[:70]}")
                            self.bot.notify_subscribers(job)
                        else:
                            logger.info(f"فرصة مكررة: {job.get('title', '')[:70]}")

                    except Exception as e:
                        logger.error(f"خطأ أثناء حفظ/إرسال فرصة من {name}: {e}")

            except Exception as e:
                logger.error(f"خطأ أثناء تشغيل {name}: {e}")

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
            logger.error(f"show_db_status error: {e}")

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


if __name__ == "__main__":
    bot = JobsBot()

    github_actions = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"

    try:
        if github_actions:
            bot.run_github_actions_mode(cycles=5, sleep_seconds=60)
        else:
            bot.run_once()
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise
