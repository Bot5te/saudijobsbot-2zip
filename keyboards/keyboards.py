"""
لوحات المفاتيح - Keyboards لجميع قوائم البوت
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config.settings import (
    SAUDI_REGIONS, JOB_CATEGORIES, EDUCATION_LEVELS,
    EXPERIENCE_LEVELS, WORK_TYPES, SALARY_RANGES
)


def get_main_menu_keyboard():
    """القائمة الرئيسية"""
    keyboard = [
        [
            InlineKeyboardButton("👤 ملفي الشخصي", callback_data="profile"),
            InlineKeyboardButton("📄 سيرتي الذاتية", callback_data="cv_menu"),
        ],
        [
            InlineKeyboardButton("🔍 تصفح الوظائف", callback_data="browse_jobs"),
            InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
        ],
        [
            InlineKeyboardButton("🔔 إعدادات التنبيهات", callback_data="notification_settings"),
            InlineKeyboardButton("✏️ تعديل التفضيلات", callback_data="edit_preferences"),
        ],
        [
            InlineKeyboardButton("📋 تقديماتي", callback_data="my_applications"),
            InlineKeyboardButton("💡 نصائح مهنية", callback_data="career_tips"),
        ],
        [
            InlineKeyboardButton("❓ مساعدة", callback_data="help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_start_keyboard():
    """زر البدء للمستخدمين الجدد"""
    keyboard = [
        [InlineKeyboardButton("🚀 إنشاء ملفي الشخصي", callback_data="start_registration")],
        [InlineKeyboardButton("ℹ️ عن البوت", callback_data="about_bot")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_regions_keyboard():
    """لوحة اختيار المنطقة"""
    keyboard = []
    row = []
    for i, region in enumerate(SAUDI_REGIONS):
        row.append(InlineKeyboardButton(region, callback_data=f"region_{region}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_categories_keyboard():
    """لوحة اختيار التخصص الرئيسي"""
    keyboard = []
    for category in JOB_CATEGORIES.keys():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_specializations_keyboard(category: str):
    """لوحة اختيار التخصص الفرعي"""
    specs = JOB_CATEGORIES.get(category, [])
    keyboard = []
    for spec in specs:
        keyboard.append([InlineKeyboardButton(spec, callback_data=f"spec_{spec}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(keyboard)


def get_education_keyboard():
    """لوحة اختيار المؤهل الدراسي"""
    keyboard = []
    for edu in EDUCATION_LEVELS:
        keyboard.append([InlineKeyboardButton(edu, callback_data=f"edu_{edu}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_experience_keyboard():
    """لوحة اختيار سنوات الخبرة"""
    keyboard = []
    for exp in EXPERIENCE_LEVELS:
        keyboard.append([InlineKeyboardButton(exp, callback_data=f"exp_{exp}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_work_type_keyboard():
    """لوحة اختيار نوع الدوام"""
    keyboard = []
    row = []
    for i, wt in enumerate(WORK_TYPES):
        row.append(InlineKeyboardButton(wt, callback_data=f"wtype_{wt}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_salary_keyboard():
    """لوحة اختيار الراتب المتوقع"""
    keyboard = []
    for sal in SALARY_RANGES:
        keyboard.append([InlineKeyboardButton(sal, callback_data=f"sal_{sal}")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_cv_options_keyboard():
    """خيارات إضافة السيرة الذاتية"""
    keyboard = [
        [InlineKeyboardButton("📎 رفع ملف PDF", callback_data="upload_cv_pdf")],
        [InlineKeyboardButton("🖼️ رفع صورة", callback_data="upload_cv_image")],
        [InlineKeyboardButton("✍️ تعبئة البيانات يدوياً", callback_data="manual_cv")],
        [InlineKeyboardButton("⏭️ تخطي الآن", callback_data="skip_cv")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_skip_keyboard(skip_data: str = "skip"):
    """زر تخطي"""
    keyboard = [
        [InlineKeyboardButton("⏭️ تخطي", callback_data=skip_data)],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_profile_keyboard():
    """تأكيد الملف الشخصي"""
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد وحفظ الملف", callback_data="confirm_profile")],
        [InlineKeyboardButton("✏️ تعديل", callback_data="edit_profile_before_save")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_job_card_keyboard(job_id: int, apply_link: str = None, apply_email: str = None):
    """أزرار بطاقة الوظيفة"""
    keyboard = []

    if apply_email:
        keyboard.append([
            InlineKeyboardButton("📧 تقديم تلقائي بالإيميل", callback_data=f"auto_apply_{job_id}")
        ])
    if apply_link:
        keyboard.append([
            InlineKeyboardButton("🔗 فتح رابط التقديم", url=apply_link)
        ])

    keyboard.append([
        InlineKeyboardButton("✅ قدّمت عليها", callback_data=f"mark_applied_{job_id}"),
        InlineKeyboardButton("❌ لا تناسبني", callback_data=f"dismiss_job_{job_id}"),
    ])
    keyboard.append([
        InlineKeyboardButton("💾 حفظ الوظيفة", callback_data=f"save_job_{job_id}"),
        InlineKeyboardButton("📤 مشاركة", callback_data=f"share_job_{job_id}"),
    ])
    return InlineKeyboardMarkup(keyboard)


def get_notification_settings_keyboard(notifications_on: bool, auto_apply_on: bool):
    """إعدادات الإشعارات"""
    notif_icon = "🔔 مفعّل" if notifications_on else "🔕 معطّل"
    auto_icon = "✅ مفعّل" if auto_apply_on else "❌ معطّل"

    keyboard = [
        [InlineKeyboardButton(
            f"الإشعارات: {notif_icon}",
            callback_data="toggle_notifications"
        )],
        [InlineKeyboardButton(
            f"التقديم التلقائي: {auto_icon}",
            callback_data="toggle_auto_apply"
        )],
        [InlineKeyboardButton(
            "📧 إعداد إيميل التقديم",
            callback_data="email_setup"
        )],
        [InlineKeyboardButton("⬅️ رجوع للقائمة", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_edit_profile_keyboard():
    """قائمة تعديل الملف الشخصي"""
    keyboard = [
        [
            InlineKeyboardButton("✏️ الاسم", callback_data="edit_name"),
            InlineKeyboardButton("📍 المنطقة", callback_data="edit_region"),
        ],
        [
            InlineKeyboardButton("🎯 التخصص", callback_data="edit_specialization"),
            InlineKeyboardButton("🎓 المؤهل", callback_data="edit_education"),
        ],
        [
            InlineKeyboardButton("⭐ الخبرة", callback_data="edit_experience"),
            InlineKeyboardButton("🏢 نوع الدوام", callback_data="edit_work_type"),
        ],
        [
            InlineKeyboardButton("💰 الراتب المتوقع", callback_data="edit_salary"),
            InlineKeyboardButton("📧 الإيميل", callback_data="edit_email"),
        ],
        [
            InlineKeyboardButton("📄 السيرة الذاتية", callback_data="edit_cv"),
            InlineKeyboardButton("🔗 LinkedIn", callback_data="edit_linkedin"),
        ],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard():
    """زر الرجوع للقائمة الرئيسية"""
    keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)
