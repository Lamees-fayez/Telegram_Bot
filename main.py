import os
import time
import logging
from typing import Dict, List, Set
from dotenv import load_dotenv

from database import JobsDatabase
from telegram_bot import TelegramBot
from MostaqlScraper import MostaqlScraper
from KhamsatScraper import KhamsatScraper

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_env(*names, default=None):
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


CHECK_INTERVAL = int(get_env("CHECK_INTERVAL", default="60"))


def normalize_text(text: str) -> str:
    text = (text or "").strip().lower()

    arabic_map = {
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"
    }

    for old, new in arabic_map.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def is_good_job(job: Dict) -> bool:
    title = normalize_text(job.get("title", ""))
    description = normalize_text(job.get("description", ""))
    full_text = f"{title} {description}"

    keywords = [
        "excel", "microsoft excel", "اكسل", "اكسيل", "إكسل",
        "power bi", "powerbi",
        "dashboard", "dash board", "داشبورد", "داش بورد",
        "لوحه تحكم", "لوحة تحكم",
        "تحليل بيانات", "data analysis", "data analytics",
        "sql", "python", "power query", "باور كويري",
        "web scraping", "scraping", "data extraction",
        "سحب بيانات", "استخراج بيانات", "جمع بيانات",
        "google sheets", "google sheet", "جوجل شيت", "جوجل شيتس",
        "eda", "automation", "csv", "xlsx",
        "data", "analysis", "report", "reports", "reporting",
        "kpi", "kpis", "تقارير", "تقرير", "تحليل",
        "database", "قاعده بيانات", "قاعدة بيانات"
    ]

    return any(normalize_text(keyword) in full_text for keyword in keywords)


def normalize_job(job: Dict, source: str) -> Dict:
    return {
        "job_id": str(job.get("job_id", "")).strip(),
        "title": str(job.get("title", "")).strip(),
        "url": str(job.get("url") or job.get("link") or "").strip(),
        "link": str(job.get("url") or job.get("link") or "").strip(),
        "price": str(job.get("price", "غير محدد")).strip(),
        "description": str(job.get("description", "")).strip(),
        "platform": str(job.get("platform", source)).strip(),
        "posted_date": str(job.get("posted_date", "")).strip(),
    }


def build_unique_key(job: Dict) -> str:
    platform = str(job.get("platform", "unknown")).strip().lower()
    job_id = str(job.get("job_id", "")).strip()
    url = str(job.get("url", "")).strip()

    if job_id:
        return f"{platform}:{job_id}"

    return f"{platform}:{url}"


def collect_jobs() -> List[Dict]:
    all_jobs = []

    scrapers = [
        ("mostaql", MostaqlScraper()),
        ("khamsat", KhamsatScraper()),
    ]

    for source_name, scraper in scrapers:
        try:
            logger.info(f"📡 فحص {source_name}")
            jobs = scraper.search_jobs() or []
            normalized_jobs = [normalize_job(job, source_name) for job in jobs]
            filtered_jobs = [job for job in normalized_jobs if is_good_job(job)]

            logger.info(f"{source_name}: {len(filtered_jobs)} بعد الفلترة")
            all_jobs.extend(filtered_jobs)

        except Exception as e:
            logger.exception(f"خطأ أثناء فحص {source_name}: {e}")

    return all_jobs


def send_start_message(bot: TelegramBot, chat_id: str):
    try:
        if hasattr(bot, "bot"):
            bot.bot.send_message(
                chat_id=int(chat_id),
                text="✅ تم تشغيل البوت بنجاح وهو الآن يراقب المشاريع الجديدة."
            )
    except Exception as e:
        logger.exception(f"تعذر إرسال رسالة البداية: {e}")


def send_job(bot: TelegramBot, job: Dict):
    try:
        if hasattr(bot, "notify_subscribers"):
            bot.notify_subscribers(job)
        elif hasattr(bot, "send_new_job"):
            bot.send_new_job(job)
        else:
            logger.error("لا توجد دالة إرسال مناسبة داخل telegram_bot.py")
    except Exception as e:
        logger.exception(f"فشل إرسال مشروع: {e}")


def main():
    token = get_env("TELEGRAM_BOT_TOKEN", "BOT_TOKEN")
    chat_id = get_env("TELEGRAM_CHAT_ID", "CHAT_ID")

    if not token:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN أو BOT_TOKEN غير موجود")

    if not chat_id:
        raise ValueError("❌ TELEGRAM_CHAT_ID أو CHAT_ID غير موجود")

    db = JobsDatabase()
    bot = TelegramBot(token=token, db=db)

    logger.info("🚀 البوت بدأ")
    send_start_message(bot, chat_id)

    sent_this_session: Set[str] = set()

    while True:
        try:
            jobs = collect_jobs()
            new_jobs = []

            for job in jobs:
                unique_key = build_unique_key(job)

                if not unique_key or unique_key.endswith(":"):
                    continue

                if unique_key in sent_this_session:
                    continue

                if db.job_exists(unique_key):
                    continue

                db.add_job(job, unique_key)
                sent_this_session.add(unique_key)
                new_jobs.append(job)

            if new_jobs:
                logger.info(f"🔥 {len(new_jobs)} مشروع جديد")
                for job in new_jobs:
                    send_job(bot, job)
                    time.sleep(2)
            else:
                logger.info("😴 مفيش جديد")

        except Exception as e:
            logger.exception(f"💥 خطأ في اللوب الرئيسية: {e}")

        logger.info(f"⏳ انتظار {CHECK_INTERVAL} ثانية")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
