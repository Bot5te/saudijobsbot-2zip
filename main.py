"""
🤖 بوت التوظيف السعودي - نقطة البداية الرئيسية
Saudi Jobs Telegram Bot - Main Entry Point

التشغيل:
    pip install python-telegram-bot==21.3
    python main.py
"""

import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from config.settings import BOT_TOKEN, CHANNEL_ID, ADMIN_ID
from database.db import init_db
from handlers.registration import (
    cmd_start, handle_text_input, handle_cv_upload
)
from handlers.callbacks import handle_callback
from handlers.edit_profile import handle_edit_text_input
from utils.email_sender import handle_email_setup_text
from utils.notifier import process_channel_message
from app import server 

async def handle_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    موزّع الرسائل النصية:
    يوجّه للمعالج الصح حسب الحالة الحالية
    """
    from config.settings import States

    state = context.user_data.get("state", "")

    # 1) وضع إعداد إيميل التقديم التلقائي
    if state in (States.EMAIL_SETUP_ADDRESS, States.EMAIL_SETUP_PASSWORD):
        handled = await handle_email_setup_text(update, context)
        if handled:
            return

    # 2) وضع تعديل الملف الشخصي (نصوص: اسم، إيميل، LinkedIn)
    handled = await handle_edit_text_input(update, context)
    if handled:
        return

    # 3) خطوات التسجيل الأولي
    await handle_text_input(update, context)


# ─────────────────────────────────────────
# إعداد السجل (Logging)
# ─────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# معالج رسائل القناة
# ─────────────────────────────────────────
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة منشورات القناة وتحويلها لوظائف"""
    message = update.channel_post
    if not message or not message.text:
        return

    channel = message.chat.username or str(message.chat.id)
    logger.info(f"📥 منشور جديد من القناة @{channel}")

    await process_channel_message(
        context.bot,
        message.text,
        message.message_id,
        channel
    )


# ─────────────────────────────────────────
# معالج الأوامر الإضافية
# ─────────────────────────────────────────
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help"""
    await update.message.reply_text(
        "📖 *الأوامر المتاحة:*\n\n"
        "/start - بدء البوت أو القائمة الرئيسية\n"
        "/profile - عرض ملفك الشخصي\n"
        "/jobs - آخر الوظائف\n"
        "/settings - الإعدادات\n"
        "/help - المساعدة",
        parse_mode="Markdown"
    )


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /profile"""
    from database.db import get_user
    from keyboards.keyboards import get_edit_profile_keyboard
    user = get_user(update.effective_user.id)
    if user and user.get("registration_complete"):
        await update.message.reply_text(
            f"👤 مرحباً *{user.get('full_name_ar', '')}*\n\nاضغط لعرض ملفك:",
            parse_mode="Markdown",
            reply_markup=get_edit_profile_keyboard()
        )
    else:
        await update.message.reply_text(
            "لم تُكمل التسجيل بعد.\nاضغط /start للبدء"
        )


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /jobs"""
    from database.db import get_recent_jobs
    from keyboards.keyboards import get_job_card_keyboard
    from telegram.constants import ParseMode
    from utils.notifier import build_job_card_text

    jobs = get_recent_jobs(5)
    if not jobs:
        await update.message.reply_text("📭 لا توجد وظائف حالياً. سنُشعرك فور نزول وظائف جديدة!")
        return

    await update.message.reply_text(f"💼 *آخر {len(jobs)} وظائف:*", parse_mode=ParseMode.MARKDOWN)
    for job in jobs:
        await update.message.reply_text(
            build_job_card_text(job),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_job_card_keyboard(job["id"], job.get("apply_link"), job.get("apply_email"))
        )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المشرف - /admin"""
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر للمشرف فقط.")
        return

    from database.db import get_connection
    conn = get_connection()
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE registration_complete=1").fetchone()[0]
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    recent_jobs = conn.execute(
        "SELECT title, company, created_at FROM jobs ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    conn.close()

    text = (
        "🛠️ *لوحة تحكم المشرف*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"👥 *المستخدمون المسجلون:* {total_users}\n"
        f"💼 *الوظائف في قاعدة البيانات:* {total_jobs}\n"
        f"📨 *إجمالي التقديمات:* {total_apps}\n"
        "━━━━━━━━━━━━━━━━\n"
        "📋 *آخر 5 وظائف أضيفت:*\n"
    )
    for job in recent_jobs:
        text += f"  • {job['title']} - {job['company'] or 'غير محدد'}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ─────────────────────────────────────────
# نقطة البداية
# ─────────────────────────────────────────
def main():
    """تشغيل البوت"""

    if not BOT_TOKEN:
        logger.error("❌ لم يُحدد BOT_TOKEN! أضف المتغير في الإعدادات.")
        print("❌ خطأ: BOT_TOKEN غير موجود. أضفه كمتغير بيئة.")
        return

    # تهيئة قاعدة البيانات
    init_db()
    logger.info("✅ تم تهيئة قاعدة البيانات")

    # إنشاء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()

    # ─── أوامر ───
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("admin", cmd_admin))

    # ─── أزرار Inline ───
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ─── رسائل نصية (تسجيل + تعديل + إعداد إيميل) ───
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.ChatType.CHANNEL,
        handle_all_text
    ))

    # ─── رفع الملفات (CV) ───
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO,
        handle_cv_upload
    ))

    # ─── منشورات القناة ───
    app.add_handler(MessageHandler(
        filters.ChatType.CHANNEL,
        handle_channel_post
    ))

    logger.info("🚀 البوت يعمل الآن...")
    print("=" * 50)
    print("🤖 بوت التوظيف السعودي")
    print("✅ جاهز للعمل!")
    print("=" * 50)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    server()
    main()
