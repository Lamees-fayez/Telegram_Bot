import os
import logging
from typing import Dict

from telegram import Bot
from database import JobsDatabase

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, db: JobsDatabase):
        self.token = token
        self.db = db
        self.bot = Bot(token=token)

    def format_job_message(self, job: Dict) -> str:
        title = job.get("title", "فرصة جديدة")
        url = job.get("url") or job.get("link") or ""
        price = job.get("price", "غير محدد")
        platform = job.get("platform", "unknown").replace("_", " ").title()
        posted_date = str(job.get("posted_date", job.get("scraped_date", "")))[:16]

        return (
            f"🚨 فرصة جديدة نزلت!\n\n"
            f"📌 {title}\n"
            f"💰 {price}\n"
            f"🌐 {platform}\n"
            f"📅 {posted_date}\n"
            f"🔗 {url}"
        )

    def notify_subscribers(self, job: Dict):
        subscribers = self.db.get_subscribers()

        # fallback مهم جدًا علشان GitHub Actions
        fallback_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

        if not subscribers and fallback_chat_id:
            try:
                subscribers = [int(fallback_chat_id)]
            except ValueError:
                logger.warning("TELEGRAM_CHAT_ID غير صالح")

        if not subscribers:
            logger.info("لا يوجد مشتركين")
            return

        msg = self.format_job_message(job)

        for chat_id in subscribers:
            try:
                self.bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    disable_web_page_preview=False
                )
                logger.info(f"sent to {chat_id}")
            except Exception as e:
                logger.error(f"error sending to {chat_id}: {e}")
