import time
import pytz
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

from config import TELEGRAM_TOKEN, SCRAPE_INTERVAL
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
        logger.info("🔍 بدء البحث في كل المواقع...")

        subs = self.db.get_subscribers()
        logger.info(f"👥 عدد المشتركين الحالي = {len(subs)}")

        total_new = 0

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"🌐 فحص المصدر: {name}")
                jobs = scraper.search_jobs() or []

                logger.info(f"📡 {name}: عدد النتائج الراجعة = {len(jobs)}")

                for job in jobs:
                    try:
                        job["platform"] = name
                        saved = self.db.save_job(name, job)

                        if saved:
                            total_new += 1
                            logger.info(f"✅ تم حفظ فرصة جديدة من {name}: {job.get('title', '')[:70]}")
                            self.bot.notify_subscribers(job)
                        else:
                            logger.info(f"⏭️ فرصة مكررة: {job.get('title', '')[:70]}")

                    except Exception as e:
                        logger.error(f"❌ خطأ أثناء حفظ/إرسال فرصة من {name}: {e}")

            except Exception as e:
                logger.error(f"❌ خطأ أثناء تشغيل {name}: {e}")

        logger.info(f"✅ إجمالي الفرص الجديدة = {total_new}")
        self.show_db_status()
        logger.info("=" * 80)

    def show_db_status(self):
        try:
            jobs = self.db.get_new_jobs(limit=10)
            logger.info(f"📊 آخر الوظائف في DB = {len(jobs)}")

            for job in jobs[:5]:
                logger.info(f"📋 {job.get('platform', '')} | {job.get('title', '')[:60]}")

        except Exception as e:
            logger.error(f"❌ show_db_status error: {e}")

    def run(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN غير موجود في ملف .env")

        logger.info("🚀 بدء تشغيل البوت...")

        # أول تشغيل
        self.scrape_all()

        scheduler = BackgroundScheduler(timezone=pytz.utc)
        scheduler.add_job(
            self.scrape_all,
            trigger="interval",
            seconds=int(SCRAPE_INTERVAL),
            max_instances=1,
            coalesce=True
        )
        scheduler.start()

        logger.info("🤖 البوت شغال")
        logger.info("📌 استخدمي /start لتفعيل الإشعارات")
        logger.info("📌 استخدمي /jobs لعرض آخر 10 فرص")
        logger.info("📌 استخدمي /test لاختبار الإرسال")

        self.bot.run()


if __name__ == "__main__":
    bot = JobsBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت")
