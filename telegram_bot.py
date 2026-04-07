import os
import logging
from typing import Dict

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

from database import JobsDatabase

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, db: JobsDatabase, polling_enabled: bool = True):
        self.token = token
        self.db = db
        self.polling_enabled = polling_enabled

        self.bot = Bot(token=token)
        self.updater = None
        self.dispatcher = None

        if self.polling_enabled:
            self.updater = Updater(token=token, use_context=True)
            self.dispatcher = self.updater.dispatcher
            self.setup_handlers()

    def setup_handlers(self):
        if not self.dispatcher:
            return

        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("jobs", self.get_jobs))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(CommandHandler("test", self.test_command))
        self.dispatcher.add_handler(CommandHandler("subscribers", self.subscribers_command))
        self.dispatcher.add_handler(CommandHandler("stop", self.stop_command))
        self.dispatcher.add_handler(CallbackQueryHandler(self.button_callback))
        self.dispatcher.add_error_handler(self.error_handler)

    def error_handler(self, update, context):
        logger.exception("Telegram update error", exc_info=context.error)

    def start_command(self, update: Update, context: CallbackContext):
        try:
            chat_id = update.effective_chat.id
            self.db.add_subscriber(chat_id)

            text = (
                "تم تشغيل البوت بنجاح ✅\n\n"
                "الأوامر:\n"
                "/jobs - آخر 10 فرص\n"
                "/test - اختبار الإرسال\n"
                "/subscribers - عدد المشتركين\n"
                "/stop - إلغاء الإشعارات\n"
                "/help - المساعدة"
            )

            update.message.reply_text(text)
            logger.info(f"start_command ok for {chat_id}")

        except Exception as e:
            logger.exception(f"start_command error: {e}")
            if update.message:
                update.message.reply_text(f"حدث خطأ أثناء التفعيل: {e}")

    def stop_command(self, update: Update, context: CallbackContext):
        try:
            chat_id = update.effective_chat.id
            self.db.remove_subscriber(chat_id)
            update.message.reply_text("تم إلغاء الاشتراك ✅")
        except Exception as e:
            logger.exception(f"stop_command error: {e}")
            update.message.reply_text(f"حدث خطأ: {e}")

    def help_command(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            "/start\n"
            "/jobs\n"
            "/test\n"
            "/subscribers\n"
            "/stop\n"
            "/help"
        )

    def test_command(self, update: Update, context: CallbackContext):
        try:
            chat_id = update.effective_chat.id
            self.bot.send_message(chat_id=chat_id, text="رسالة اختبار ✅")
        except Exception as e:
            logger.exception(f"test_command error: {e}")
            update.message.reply_text(f"فشل الاختبار: {e}")

    def subscribers_command(self, update: Update, context: CallbackContext):
        try:
            subscribers = self.db.get_subscribers()
            update.message.reply_text(f"عدد المشتركين: {len(subscribers)}")
        except Exception as e:
            logger.exception(f"subscribers_command error: {e}")
            update.message.reply_text(f"حدث خطأ: {e}")

    def build_jobs_message(self, jobs, title_prefix="آخر"):
        if not jobs:
            return "لا توجد وظائف حاليًا"

        lines = [f"{title_prefix} {len(jobs[:10])} وظائف:\n"]
        for i, job in enumerate(jobs[:10], 1):
            title = job.get("title", "بدون عنوان")
            url = job.get("url", "")
            price = job.get("price", "غير محدد")
            platform = job.get("platform", "unknown")
            posted_date = str(job.get("posted_date", job.get("scraped_date", "")))[:16]

            lines.extend([
                f"{i}. {title}",
                f"السعر: {price}",
                f"الموقع: {platform}",
                f"التاريخ: {posted_date}",
                f"الرابط: {url}",
                ""
            ])

        return "\n".join(lines)

    def get_jobs(self, update: Update, context: CallbackContext):
        try:
            jobs = self.db.get_new_jobs(limit=10)
            if not jobs:
                update.message.reply_text("لا توجد وظائف محفوظة حاليًا")
                return

            message = self.build_jobs_message(jobs, title_prefix="آخر")
            keyboard = [[InlineKeyboardButton("تحديث", callback_data="refresh_jobs")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                message,
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )
        except Exception as e:
            logger.exception(f"get_jobs error: {e}")
            update.message.reply_text(f"حدث خطأ أثناء جلب الوظائف: {e}")

    def button_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()

        try:
            if query.data == "refresh_jobs":
                jobs = self.db.get_new_jobs(limit=10)
                if not jobs:
                    query.edit_message_text("لا توجد وظائف محفوظة حاليًا")
                    return

                message = self.build_jobs_message(jobs, title_prefix="محدث")
                keyboard = [[InlineKeyboardButton("تحديث", callback_data="refresh_jobs")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    disable_web_page_preview=False
                )
        except Exception as e:
            logger.exception(f"button_callback error: {e}")
            try:
                query.edit_message_text(f"حدث خطأ أثناء التحديث: {e}")
            except Exception:
                pass

    def format_job_message(self, job: Dict) -> str:
        title = job.get("title", "فرصة جديدة")
        url = job.get("url") or job.get("link") or ""
        price = job.get("price", "غير محدد")
        platform = job.get("platform", "unknown")
        posted_date = str(job.get("posted_date", job.get("scraped_date", "")))[:16]

        return (
            f"فرصة جديدة\n\n"
            f"{title}\n"
            f"السعر: {price}\n"
            f"الموقع: {platform}\n"
            f"التاريخ: {posted_date}\n"
            f"{url}"
        )

    def notify_subscribers(self, job: Dict):
        subscribers = self.db.get_subscribers()

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
                logger.info(f"notification sent to {chat_id}")
            except Exception as e:
                logger.exception(f"notify error to {chat_id}: {e}")

    def run(self):
        if not self.polling_enabled or not self.updater:
            logger.info("Polling disabled")
            return

        logger.info("Starting Telegram polling...")
        self.updater.start_polling(drop_pending_updates=True)
        self.updater.idle()
