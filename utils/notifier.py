"""
نظام الإشعارات - مطابقة الوظائف مع المستخدمين وإرسال التنبيهات
"""

import re
import logging
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from database.db import (
    save_job, get_matching_users, mark_notification_sent,
    was_notified
)
from keyboards.keyboards import get_job_card_keyboard

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# تحليل نص الوظيفة
# ─────────────────────────────────────────

def _clean_url(url: str) -> str:
    """تنظيف URL من الأحرف الزائدة في النهاية"""
    return url.rstrip(".,;:)\"'><")


def parse_job_from_text(text: str, message_id: int, channel: str) -> dict:
    """
    استخراج بيانات الوظيفة من نص المنشور
    يعمل بدون AI بالبحث عن أنماط نصية محددة
    """
    job = {
        "channel_message_id": message_id,
        "source_channel": channel,
        "raw_text": text,
        "title": None,
        "company": None,
        "region": None,
        "category": None,
        "specialization": None,
        "apply_link": None,
        "apply_email": None,
        "salary": None,
        "work_type": None,
        "deadline": None,
        "description": text[:500],
    }

    lines = text.strip().splitlines()

    # استخراج المسمى الوظيفي
    title_patterns = [
        r"(?:وظيفة|مطلوب|فرصة عمل|وظائف شاغرة|المسمى الوظيفي)[:\s]+([^\n]+)",
        r"(?:vacancy|job title|position|role)[:\s]+([^\n]+)",
    ]
    for pattern in title_patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            job["title"] = m.group(1).strip()[:100]
            break

    # إذا لم يوجد pattern، نأخذ أول سطر غير فارغ (5-80 حرف)
    if not job["title"]:
        for line in lines:
            line = line.strip()
            if 5 <= len(line) <= 80 and not line.startswith("http"):
                job["title"] = line
                break

    # استخراج اسم الشركة
    company_patterns = [
        r"(?:الشركة|جهة العمل|صاحب العمل|المنشأة)[:\s]+([^\n]+)",
        r"(?:company|employer|organization)[:\s]+([^\n]+)",
        r"(?:شركة|مؤسسة|مجموعة)\s+([^\n]{3,50})",
    ]
    for pattern in company_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            job["company"] = m.group(1).strip()[:100]
            break

    # استخراج المنطقة
    from config.settings import SAUDI_REGIONS
    for region in SAUDI_REGIONS:
        if region not in ("أي منطقة", "عن بُعد (Remote)") and region in text:
            job["region"] = region
            break

    # الكشف عن العمل عن بُعد
    if re.search(r"remote|عن\s*بُ?عد|work from home|من المنزل", text, re.IGNORECASE):
        if not job["region"]:
            job["region"] = "عن بُعد (Remote)"
        job["work_type"] = "🏠 عن بُعد (Remote)"

    # استخراج البريد الإلكتروني
    email_m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    if email_m:
        job["apply_email"] = email_m.group(0)

    # استخراج الرابط (مع تنظيف صحيح)
    url_m = re.search(r"https?://[^\s\"'<>،,]+", text)
    if url_m:
        job["apply_link"] = _clean_url(url_m.group(0))

    # استخراج الراتب
    salary_patterns = [
        r"(?:الراتب|salary|المرتب|الأجر)[:\s]+([^\n]+)",
        r"(\d[\d,]+)\s*(?:ريال|SAR|ر\.س)",
        r"(?:يصل\s+إلى|يتراوح)[:\s]+([^\n]+)",
    ]
    for pattern in salary_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            job["salary"] = m.group(1).strip()[:80]
            break

    # استخراج الموعد النهائي
    deadline_patterns = [
        r"(?:آخر\s+موعد|deadline|ينتهي\s+التقديم)[:\s]+([^\n]+)",
        r"(?:التقديم\s+حتى)[:\s]+([^\n]+)",
    ]
    for pattern in deadline_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            job["deadline"] = m.group(1).strip()[:50]
            break

    # تحديد الفئة من الكلمات المفتاحية
    category_keywords = {
        "💻 تقنية المعلومات": [
            "برمج", "مطور", "developer", "software", "بايثون", "python",
            "جافا", "java", "شبكات", "سيكيورتي", "cybersecurity", "IT",
            "تقنية معلومات", "data", "بيانات", "ذكاء اصطناعي", "AI",
            "frontend", "backend", "fullstack", "devops", "cloud", "سحابة",
            "database", "قاعدة بيانات", "تطبيق", "موقع إلكتروني"
        ],
        "💼 الإدارة والأعمال": [
            "مدير", "محاسب", "تسويق", "مبيعات", "موارد بشرية",
            "HR", "سكرتير", "إداري", "مالي", "محاسبة", "مشتريات",
            "تجارة", "business", "marketing", "sales", "accounting",
            "بيع", "تأمين", "عقار", "استشارات", "ادارة"
        ],
        "🏥 الصحة والطب": [
            "طبيب", "ممرض", "صيدلي", "مستشفى", "طبي", "صحة",
            "عيادة", "تمريض", "أسنان", "علاج", "مختبر", "doctor",
            "nurse", "pharmacy", "medical", "health", "hospital",
            "تغذية", "أشعة", "طوارئ", "جراح"
        ],
        "🏗️ الهندسة": [
            "مهندس", "engineer", "مدني", "كهربائي", "ميكانيكي",
            "معماري", "كيميائي", "صناعي", "بترول", "إنشاءات",
            "مشاريع", "بنية تحتية", "civil", "electrical", "mechanical",
            "هندسة", "رسم هندسي", "AutoCAD"
        ],
        "📚 التعليم": [
            "معلم", "مدرس", "أستاذ", "تعليم", "teacher", "مدرسة",
            "جامعة", "تدريب", "instructor", "تأهيل", "تدريس",
            "محاضر", "أكاديمية", "دورة", "curriculum"
        ],
        "⚖️ القانون والشريعة": [
            "محامي", "قانوني", "قضاء", "شريعة", "lawyer", "legal",
            "تعاقد", "عقود", "compliance", "قانون"
        ],
        "🎨 الإبداع والتصميم": [
            "مصمم", "تصميم", "designer", "graphic", "جرافيك",
            "فوتوشوب", "illustrator", "UI", "UX", "إعلام",
            "محتوى", "content", "فيديو", "تصوير", "فن"
        ],
        "🔧 الفنيون والحرفيون": [
            "كهربائي", "سباك", "تكييف", "ميكانيك", "لحام",
            "نجار", "فني", "تقني", "صيانة", "technician",
            "electrician", "plumber", "mechanic"
        ],
        "📦 اللوجستيك والنقل": [
            "مستودع", "توصيل", "توزيع", "أسطول", "جمارك",
            "لوجستيك", "logistics", "warehouse", "delivery", "شحن",
            "سائق", "driver", "نقل", "supply chain"
        ],
        "🍽️ الضيافة والسياحة": [
            "فندق", "مطعم", "سياحة", "hotel", "restaurant",
            "hospitality", "tourism", "طاهي", "خدمة", "barista",
            "ضيافة", "استقبال", "reception"
        ],
    }

    text_lower = text.lower()
    for cat, keywords in category_keywords.items():
        if any(kw.lower() in text_lower for kw in keywords):
            job["category"] = cat
            break

    # التأكد من وجود عنوان
    if not job["title"]:
        job["title"] = "وظيفة جديدة"

    return job


# ─────────────────────────────────────────
# إرسال الإشعارات
# ─────────────────────────────────────────

async def send_job_notification(bot: Bot, user: dict, job: dict):
    """إرسال إشعار وظيفة لمستخدم واحد"""
    telegram_id = user["telegram_id"]
    job_id = job["id"]

    if was_notified(telegram_id, job_id):
        return False

    text = build_job_card_text(job)

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_job_card_keyboard(
                job_id,
                job.get("apply_link"),
                job.get("apply_email")
            )
        )
        mark_notification_sent(telegram_id, job_id)
        return True
    except TelegramError as e:
        logger.error(f"❌ خطأ في إرسال الإشعار للمستخدم {telegram_id}: {e}")
        return False


def build_job_card_text(job: dict) -> str:
    """بناء نص بطاقة الوظيفة"""
    text = "🔔 *وظيفة تناسبك!*\n"
    text += "━━━━━━━━━━━━━━━━\n"
    text += f"💼 *{job.get('title', 'وظيفة')}*\n"

    if job.get("company"):
        text += f"🏢 {job['company']}\n"

    if job.get("region"):
        text += f"📍 {job['region']}\n"

    if job.get("category"):
        text += f"🎯 {job['category']}\n"

    if job.get("work_type"):
        text += f"🕐 {job['work_type']}\n"

    if job.get("salary"):
        text += f"💰 {job['salary']}\n"

    if job.get("deadline"):
        text += f"⏰ آخر موعد: {job['deadline']}\n"

    text += "━━━━━━━━━━━━━━━━\n"

    if job.get("apply_email"):
        text += "📧 _يدعم التقديم التلقائي_\n"

    return text


async def process_channel_message(bot: Bot, message_text: str, message_id: int, channel: str):
    """معالجة منشور جديد من القناة وإرسال الإشعارات"""
    if not message_text or len(message_text) < 20:
        return 0

    # تحليل الوظيفة
    job_data = parse_job_from_text(message_text, message_id, channel)

    # حفظ الوظيفة
    job_id = save_job(job_data)
    if not job_id:
        logger.warning(f"⚠️ فشل حفظ الوظيفة من القناة @{channel}")
        return 0

    job_data["id"] = job_id

    # إيجاد المستخدمين المناسبين
    matching_users = get_matching_users(job_data)

    # إرسال الإشعارات
    sent_count = 0
    for user in matching_users:
        success = await send_job_notification(bot, user, job_data)
        if success:
            sent_count += 1

    logger.info(f"📨 تم إرسال إشعار وظيفة '{job_data['title']}' لـ {sent_count} مستخدم")
    return sent_count
