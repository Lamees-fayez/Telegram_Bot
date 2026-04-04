import pytz
from dotenv import load_dotenv
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from config import TELEGRAM_TOKEN, SCRAPE_INTERVAL
from database import JobsDatabase
from telegram_bot import TelegramBot

from MostaqlScraper import MostaqlScraper
from KhamsatScraper import KhamsatScraper
from UpworkScraper import UpworkScraper

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class JobsBot:
    def __init__(self):
        self.db = JobsDatabase()
        self.bot = TelegramBot(TELEGRAM_TOKEN, self.db)

        self.scrapers = {
            "mostaql": MostaqlScraper(),
            "khamsat_requests": KhamsatScraper(),
            "upwork": UpworkScraper()
        }

    def scrape_all(self):
        logger.info("=" * 60)
        logger.info("🔍 بدء البحث في كل المواقع...")
        total_new = 0

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"🌐 فحص: {name}")
                jobs = scraper.search_jobs()
                logger.info(f"📡 {name}: وجد {len(jobs)} نتيجة")

                for job in jobs:
                    try:
                        job["platform"] = name

                        if self.db.save_job(name, job):
                            total_new += 1
                            logger.info(f"✅ جديد: {job['title'][:60]}")

                            # إرسال إشعار فوري للمشتركين
                            self.bot.notify_subscribers(job)
                        else:
                            logger.info(f"⏭️ مكرر: {job['title'][:60]}")

                    except Exception as e:
                        logger.error(f"❌ خطأ أثناء حفظ/إرسال مشروع من {name}: {e}")

            except Exception as e:
                logger.error(f"❌ خطأ في {name}: {e}")

        logger.info(f"✅ إجمالي المشاريع الجديدة: {total_new}")
        self.show_db_status()

    def show_db_status(self):
        jobs = self.db.get_new_jobs(limit=10)
        logger.info(f"📊 إجمالي آخر المشاريع في قاعدة البيانات: {len(jobs)}")

        for job in jobs[:3]:
            logger.info(f"📋 {job.get('title', '')[:40]} <- {job.get('platform', '')}")

        logger.info("=" * 60)

    def run(self):
        logger.info("🚀 بدء تشغيل البوت...")

        # أول فحص عند التشغيل
        self.scrape_all()

        # جدولة الفحص كل عدد دقائق من config
        scheduler = BackgroundScheduler(timezone=pytz.utc)
        scheduler.add_job(
            self.scrape_all,
            trigger='interval',
            minutes=int(SCRAPE_INTERVAL),
            max_instances=1,
            coalesce=True
        )
        scheduler.start()

        logger.info("🤖 البوت شغال")
        logger.info("📌 استخدمي /start لتفعيل الإشعارات")
        logger.info("📌 استخدمي /jobs لعرض آخر 10 فرص")

        # تشغيل التليجرام
        self.bot.run()


if __name__ == "__main__":
    bot = JobsBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت")
