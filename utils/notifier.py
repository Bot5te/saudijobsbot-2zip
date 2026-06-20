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

def _parse_job_smart(text: str, message_id: int, channel: str) -> dict:
    """
    تحليل ذكي للوظيفة: يجرب Groq AI أولاً، ثم يرجع لـ regex كاحتياط
    """
    from utils.ai_helper import ai_parse_job

    # الخطوة 1: محاولة التحليل بالذكاء الاصطناعي
    ai_result = ai_parse_job(text)

    if ai_result:
        logger.info("🤖 تم تحليل الوظيفة بالذكاء الاصطناعي")
        # تطبيع المنطقة لتتطابق مع قيم الإعدادات
        region = _normalize_region(ai_result.get("region", ""))
        # تطبيع التخصص ليتطابق مع الفئات المعرّفة
        category = _normalize_category(ai_result.get("category", ""))

        job = {
            "channel_message_id": message_id,
            "source_channel": channel,
            "raw_text": text,
            "title": (ai_result.get("title") or "وظيفة جديدة")[:100],
            "company": (ai_result.get("company") or "")[:100],
            "region": region,
            "category": category,
            "specialization": (ai_result.get("specialization") or "")[:100],
            "apply_link": None,
            "apply_email": None,
            "salary": (ai_result.get("salary") or "")[:80],
            "work_type": ai_result.get("work_type") or "",
            "deadline": (ai_result.get("deadline") or "")[:50],
            "requirements": (ai_result.get("requirements") or "")[:300],
            "description": text[:500],
        }

        # نستخرج الإيميل والرابط بـ regex دائماً (موثوق أكثر)
        email_m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        if email_m:
            job["apply_email"] = email_m.group(0)
        url_m = re.search(r"https?://[^\s\"'<>،,]+", text)
        if url_m:
            job["apply_link"] = _clean_url(url_m.group(0))

        return job

    # الخطوة 2: احتياط بـ regex التقليدي
    logger.info("🔍 تم تحليل الوظيفة بـ regex (Groq غير متاح)")
    return parse_job_from_text(text, message_id, channel)


def _normalize_region(region_text: str) -> str:
    """تطبيع اسم المنطقة ليتطابق مع قائمة SAUDI_REGIONS"""
    if not region_text:
        return ""
    from config.settings import SAUDI_REGIONS
    region_text = region_text.strip()
    # بحث مباشر
    for r in SAUDI_REGIONS:
        if r in region_text or region_text in r:
            return r
    # بحث بكلمات مفتاحية
    keywords = {
        "رياض": "الرياض", "جده": "جدة", "جدة": "جدة",
        "مكة": "مكة المكرمة", "مدينة": "المدينة المنورة",
        "دمام": "الدمام", "خبر": "الخبر", "أحساء": "الأحساء",
        "طائف": "الطائف", "تبوك": "تبوك", "أبها": "أبها",
        "remote": "عن بُعد (Remote)", "بُعد": "عن بُعد (Remote)",
        "بعد": "عن بُعد (Remote)", "جازان": "جازان",
        "نجران": "نجران", "حائل": "حائل",
    }
    text_lower = region_text.lower()
    for kw, val in keywords.items():
        if kw in text_lower or kw in region_text:
            return val
    return region_text  # إرجاع النص الأصلي إن لم يُعثر


def _normalize_category(category_text: str) -> str:
    """تطبيع التخصص ليتطابق مع JOB_CATEGORIES"""
    if not category_text:
        return ""
    from config.settings import JOB_CATEGORIES
    # بحث مباشر
    for cat in JOB_CATEGORIES.keys():
        cat_clean = cat.split(" ", 1)[-1] if " " in cat else cat
        if cat_clean in category_text or category_text in cat_clean:
            return cat
    # بحث بكلمات مفتاحية
    keywords = {
        "تقني": "💻 تقنية المعلومات",
        "برمج": "💻 تقنية المعلومات",
        "IT": "💻 تقنية المعلومات",
        "هندس": "🏗️ الهندسة",
        "engineer": "🏗️ الهندسة",
        "صح": "🏥 الصحة والطب",
        "طب": "🏥 الصحة والطب",
        "تعليم": "📚 التعليم",
        "معلم": "📚 التعليم",
        "إدار": "💼 الإدارة والأعمال",
        "محاسب": "💼 الإدارة والأعمال",
        "مبيعات": "💼 الإدارة والأعمال",
        "قانون": "⚖️ القانون والشريعة",
        "تصميم": "🎨 الإبداع والتصميم",
        "لوجستيك": "📦 اللوجستيك والنقل",
        "ضيافة": "🍽️ الضيافة والسياحة",
        "فندق": "🍽️ الضيافة والسياحة",
        "فني": "🔧 الفنيون والحرفيون",
    }
    for kw, val in keywords.items():
        if kw in category_text:
            return val
    return category_text


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

    # تحليل الوظيفة — نجرب AI أولاً ثم regex كاحتياط
    job_data = _parse_job_smart(message_text, message_id, channel)

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
