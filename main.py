import os
from dotenv import load_dotenv
import threading
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
        self.bot = TelegramBot(TELEGRAM_TOKEN, self.db)  # ✅ TELEGRAM_TOKEN من config
        self.scrapers = {
    'mostaql': MostaqlScraper(),
    'khamsat_requests': KhamsatScraper(),  # ✅ جديد   # الخدمات العادية
    'upwork': UpworkScraper()
}
    
    def scrape_all(self):
        logger.info("=" * 50)
        logger.info("🔍 البحث في كل المواقع...")
        total_new = 0
        
        for name, scraper in self.scrapers.items():
            try:
                jobs = scraper.search_jobs()
                logger.info(f"  📡 {name}: وجد {len(jobs)} مشروع")
                
                for job in jobs:
                    if self.db.save_job(name, job):
                        total_new += 1
                        logger.info(f"    ✅ جديد: {job['title'][:50]}...")
                    else:
                        logger.info(f"    ⏭️ مكرر: {job['title'][:30]}")
                
            except Exception as e:
                logger.error(f"  ❌ {name}: {e}")
        
        logger.info(f"✅ إجمالي {total_new} مشروع جديد")
        self.show_db_status()
    
    def show_db_status(self):
        jobs = self.db.get_new_jobs()
        logger.info(f"📊 في قاعدة البيانات: {len(jobs)} مشروع (آخر 24 ساعة)")
        for job in jobs[:2]:
            logger.info(f"  📋 {job['title'][:40]} <- {job['platform']}")
        logger.info("=" * 50)
    
    def run(self):
        logger.info("🚀 بدء البوت...")
        
        # بحث فوري
        self.scrape_all()
        
        # جدولة كل 10 دقايق
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.scrape_all, 'interval', minutes=10)
        scheduler.start()
        
        logger.info("🤖 البوت جاهز - /jobs للمشاريع")
        
        # تشغيل البوت
        self.bot.app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    bot = JobsBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 إيقاف البوت")