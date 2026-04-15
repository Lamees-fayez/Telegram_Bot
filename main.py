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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_env_value(*names: str, default=None):
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


CHECK_INTERVAL = int(get_env_value("CHECK_INTERVAL", default="60"))


def normalize_job(job: Dict, source_name: str) -> Dict:
    job_id = str(job.get("job_id", "")).strip()
    url = str(job.get("url") or job.get("link") or "").strip()
    title = str(job.get("title", "")).strip()
    price = str(job.get("price", "غير محدد")).strip()
    description = str(job.get("description", "")).strip()
    platform = str(job.get("platform", source_name)).strip()

    return {
        "job_id": job_id,
        "title": title,
        "url": url,
        "link": url,
        "price": price,
        "description": description,
        "platform": platform,
        "posted_date": str(job.get("posted_date", "")).strip(),
    }


def build_unique_key(job: Dict) -> str:
    platform = str(job.get("platform", "unknown")).strip().lower()
    job_id = str(job.get("job_id", "")).strip()
    url = str(job.get("url", "")).strip()

    if job_id:
        return f"{platform}:{job_id}"
    return f"{platform}:{url}"


def db_job_exists(db: JobsDatabase, job: Dict, unique_key: str) -> bool:
    try:
        return db.job_exists(unique_key)
    except TypeError:
        url = str(job.get("url", "")).strip()
        return db.job_exists(url)
    except Exception:
        url = str(job.get("url", "")).strip()
        try:
            return db.job_exists(url)
        except Exception:
            logger.exception("فشل فحص وجود المشروع في قاعدة البيانات")
            return False


def db_add_job(db: JobsDatabase, job: Dict, unique_key: str) -> None:
    try:
        db.add_job(job, unique_key)
    except TypeError:
        db.add_job(job)
    except Exception:
        try:
            db.add_job(job)
        except Exception:
            logger.exception("فشل حفظ المشروع في قاعدة البيانات")


def collect_jobs() -> List[Dict]:
    all_jobs: List[Dict] = []

    scrapers = [
        ("mostaql", MostaqlScraper()),
        ("khamsat", KhamsatScraper()),
    ]

    for source_name, scraper in scrapers:
        try:
            logger.info(f"بدأ فحص {source_name}")
            jobs = scraper.search_jobs() or []
            logger.info(f"{source_name}: تم العثور على {len(jobs)} مشروع")
            normalized_jobs = [normalize_job(job, source_name) for job in jobs]
            all_jobs.extend(normalized_jobs)
        except Exception as e:
            logger.exception(f"خطأ أثناء فحص {source_name}: {e}")

    return all_jobs


def send_start_message(bot: TelegramBot, chat_id: str) -> None:
    try:
        if hasattr(bot, "bot"):
            bot.bot.send_message(
                chat_id=int(chat_id),
                text="✅ تم تشغيل البوت بنجاح وهو الآن يراقب المشاريع الجديدة."
            )
    except Exception as e:
        logger.exception(f"تعذر إرسال رسالة البداية: {e}")


def send_job(bot: TelegramBot, job: Dict, chat_id: str) -> None:
    try:
        if hasattr(bot, "notify_subscribers"):
            bot.notify_subscribers(job)
            return

        if hasattr(bot, "send_new_job"):
            bot.send_new_job(job)
            return

        if hasattr(bot, "bot"):
            text = (
                f"🚀 مشروع جديد\n\n"
                f"📌 {job.get('title', '')}\n"
                f"💰 {job.get('price', 'غير محدد')}\n"
                f"🌐 {job.get('platform', '')}\n"
                f"🔗 {job.get('url', '')}"
            )
            bot.bot.send_message(chat_id=int(chat_id), text=text, disable_web_page_preview=True)
            return

        logger.error("لا توجد دالة إرسال مناسبة داخل telegram_bot.py")
    except Exception as e:
        logger.exception(f"فشل إرسال مشروع: {e}")


def main():
    token = get_env_value("TELEGRAM_BOT_TOKEN", "BOT_TOKEN")
    chat_id = get_env_value("TELEGRAM_CHAT_ID", "CHAT_ID")

    if not token:
        raise ValueError("لم يتم العثور على TELEGRAM_BOT_TOKEN أو BOT_TOKEN في ملف .env")

    if not chat_id:
        raise ValueError("لم يتم العثور على TELEGRAM_CHAT_ID أو CHAT_ID في ملف .env")

    db = JobsDatabase()
    bot = TelegramBot(token=token, db=db)

    logger.info("✅ البوت بدأ التشغيل")
    send_start_message(bot, chat_id)

    sent_this_session: Set[str] = set()

    while True:
        try:
            jobs = collect_jobs()
            new_jobs: List[Dict] = []

            for job in jobs:
                unique_key = build_unique_key(job)
                if not unique_key or unique_key.endswith(":"):
                    continue

                if unique_key in sent_this_session:
                    continue

                if db_job_exists(db, job, unique_key):
                    continue

                db_add_job(db, job, unique_key)
                sent_this_session.add(unique_key)
                new_jobs.append(job)

            if new_jobs:
                logger.info(f"✅ تم العثور على {len(new_jobs)} مشروع جديد")
                for job in new_jobs:
                    send_job(bot, job, chat_id)
                    time.sleep(2)
            else:
                logger.info("ℹ️ لا يوجد مشاريع جديدة حالياً")

        except Exception as e:
            logger.exception(f"خطأ في اللوب الرئيسية: {e}")

        logger.info(f"⏳ انتظار {CHECK_INTERVAL} ثانية قبل الفحص التالي")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
