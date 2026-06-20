"""
معالج التسجيل - خطوات إنشاء الملف الشخصي
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config.settings import States, WELCOME_MESSAGE
from keyboards.keyboards import (
    get_start_keyboard, get_main_menu_keyboard, get_regions_keyboard,
    get_categories_keyboard, get_specializations_keyboard,
    get_education_keyboard, get_experience_keyboard,
    get_work_type_keyboard, get_salary_keyboard,
    get_cv_options_keyboard, get_skip_keyboard,
    get_confirm_profile_keyboard, get_back_to_menu_keyboard
)
from database.db import get_user, save_user, update_user_field


PROGRESS_BAR = {
    1: "▓░░░░░░░░░ 10%",
    2: "▓▓░░░░░░░░ 20%",
    3: "▓▓▓░░░░░░░ 30%",
    4: "▓▓▓▓░░░░░░ 40%",
    5: "▓▓▓▓▓░░░░░ 50%",
    6: "▓▓▓▓▓▓░░░░ 60%",
    7: "▓▓▓▓▓▓▓░░░ 70%",
    8: "▓▓▓▓▓▓▓▓░░ 80%",
    9: "▓▓▓▓▓▓▓▓▓░ 90%",
    10: "▓▓▓▓▓▓▓▓▓▓ 100% ✅",
}


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start"""
    user = update.effective_user
    telegram_id = user.id

    db_user = get_user(telegram_id)

    if db_user and db_user.get("registration_complete"):
        # مستخدم مسجّل مسبقاً
        await update.message.reply_text(
            f"أهلاً مجدداً *{db_user.get('full_name_ar', user.first_name)}* 👋\n\n"
            "ماذا تريد أن تفعل اليوم؟",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # مستخدم جديد
        await update.message.reply_text(
            WELCOME_MESSAGE,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_start_keyboard()
        )
        # حفظ بيانات أولية
        save_user(telegram_id, {
            "username": user.username or "",
            "registration_complete": 0
        })
        context.user_data["state"] = States.MAIN_MENU
        context.user_data["temp_profile"] = {}


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء التسجيل"""
    query = update.callback_query
    await query.answer()

    context.user_data["state"] = States.REG_FULL_NAME
    context.user_data["temp_profile"] = {}

    await query.edit_message_text(
        "📝 *الخطوة 1 من 10*\n"
        f"{PROGRESS_BAR[1]}\n\n"
        "أدخل *اسمك الكامل بالعربية* 👇\n"
        "_مثال: محمد عبدالله الأحمدي_",
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة المدخلات النصية حسب الحالة الحالية"""
    state = context.user_data.get("state")
    text = update.message.text.strip()
    telegram_id = update.effective_user.id

    if state == States.REG_FULL_NAME:
        context.user_data["temp_profile"]["full_name_ar"] = text
        context.user_data["state"] = States.REG_FULL_NAME_EN

        await update.message.reply_text(
            "📝 *الخطوة 2 من 10*\n"
            f"{PROGRESS_BAR[2]}\n\n"
            "أدخل *اسمك بالإنجليزية* 👇\n"
            "_مثال: Mohammed Abdullah Al-Ahmadi_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_skip_keyboard("skip_name_en")
        )

    elif state == States.REG_FULL_NAME_EN:
        context.user_data["temp_profile"]["full_name_en"] = text
        await ask_region(update, context)

    elif state == States.REG_EMAIL:
        if "@" in text and "." in text:
            context.user_data["temp_profile"]["email"] = text
            await ask_phone(update, context)
        else:
            await update.message.reply_text(
                "⚠️ الإيميل غير صحيح، أعد المحاولة\n"
                "_مثال: name@gmail.com_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_skip_keyboard("skip_email")
            )

    elif state == States.REG_PHONE:
        # تنسيق رقم السعودي
        phone = text.replace(" ", "").replace("-", "")
        if phone.startswith("05") and len(phone) == 10:
            context.user_data["temp_profile"]["phone"] = phone
        elif phone.startswith("+9665") and len(phone) == 13:
            context.user_data["temp_profile"]["phone"] = phone
        else:
            context.user_data["temp_profile"]["phone"] = phone  # حفظ على أي حال
        await ask_cv(update, context)

    elif state == States.REG_LINKEDIN:
        context.user_data["temp_profile"]["linkedin_url"] = text
        await show_profile_summary(update, context)


async def ask_region(update, context):
    """طلب المنطقة"""
    context.user_data["state"] = States.REG_REGION
    msg = (
        "📝 *الخطوة 3 من 10*\n"
        f"{PROGRESS_BAR[3]}\n\n"
        "🗺️ اختر *منطقتك* في المملكة العربية السعودية 👇"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_regions_keyboard()
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_regions_keyboard()
        )


async def ask_category(update, context):
    """طلب التخصص الرئيسي"""
    context.user_data["state"] = States.REG_CATEGORY
    msg = (
        "📝 *الخطوة 4 من 10*\n"
        f"{PROGRESS_BAR[4]}\n\n"
        "🎯 اختر *مجال تخصصك* الرئيسي 👇"
    )
    await update.callback_query.edit_message_text(
        msg, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_categories_keyboard()
    )


async def ask_specialization(update, context, category: str):
    """طلب التخصص الفرعي"""
    context.user_data["state"] = States.REG_SPECIALIZATION
    msg = (
        "📝 *الخطوة 5 من 10*\n"
        f"{PROGRESS_BAR[5]}\n\n"
        f"🔍 اختر *تخصصك الدقيق* في {category} 👇"
    )
    await update.callback_query.edit_message_text(
        msg, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_specializations_keyboard(category)
    )


async def ask_education(update, context):
    """طلب المؤهل الدراسي"""
    context.user_data["state"] = States.REG_EDUCATION
    msg = (
        "📝 *الخطوة 6 من 10*\n"
        f"{PROGRESS_BAR[6]}\n\n"
        "🎓 اختر *أعلى مؤهل دراسي* لديك 👇"
    )
    await update.callback_query.edit_message_text(
        msg, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_education_keyboard()
    )


async def ask_experience(update, context):
    """طلب سنوات الخبرة"""
    context.user_data["state"] = States.REG_EXPERIENCE
    msg = (
        "📝 *الخطوة 7 من 10*\n"
        f"{PROGRESS_BAR[7]}\n\n"
        "⭐ كم *سنوات خبرتك* العملية؟"
    )
    await update.callback_query.edit_message_text(
        msg, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_experience_keyboard()
    )


async def ask_work_type(update, context):
    """طلب نوع الدوام"""
    context.user_data["state"] = States.REG_WORK_TYPE
    msg = (
        "📝 *الخطوة 8 من 10*\n"
        f"{PROGRESS_BAR[8]}\n\n"
        "🏢 ما *نوع الدوام* المفضّل لديك؟"
    )
    await update.callback_query.edit_message_text(
        msg, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_work_type_keyboard()
    )


async def ask_salary(update, context):
    """طلب الراتب المتوقع"""
    context.user_data["state"] = States.REG_SALARY
    msg = (
        "📝 *الخطوة 9 من 10*\n"
        f"{PROGRESS_BAR[9]}\n\n"
        "💰 ما *نطاق الراتب* المتوقع لديك؟\n"
        "_هذه المعلومة سرية ولن تُشارك مع أحد_"
    )
    await update.callback_query.edit_message_text(
        msg, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_salary_keyboard()
    )


async def ask_email(update, context):
    """طلب الإيميل"""
    context.user_data["state"] = States.REG_EMAIL
    msg = (
        "📝 *الخطوة 9 من 10*\n"
        f"{PROGRESS_BAR[9]}\n\n"
        "📧 أدخل *بريدك الإلكتروني* لإرسال طلبات التوظيف تلقائياً\n\n"
        "🔒 _بياناتك محمية ولن تُشارك إلا مع أصحاب العمل عند التقديم_"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_skip_keyboard("skip_email")
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_skip_keyboard("skip_email")
        )


async def ask_phone(update, context):
    """طلب رقم الهاتف"""
    context.user_data["state"] = States.REG_PHONE
    msg = (
        "📱 أدخل *رقم جوالك* للتواصل\n"
        "_مثال: 0512345678_"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_skip_keyboard("skip_phone")
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_skip_keyboard("skip_phone")
        )


async def ask_cv(update, context):
    """طلب رفع السيرة الذاتية"""
    context.user_data["state"] = States.REG_CV
    msg = (
        "📝 *الخطوة 10 من 10*\n"
        f"{PROGRESS_BAR[10]}\n\n"
        "📄 الآن أضف *سيرتك الذاتية* 👇\n\n"
        "يمكنك رفع ملف PDF أو صورة، أو تخطي هذه الخطوة الآن"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cv_options_keyboard()
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_cv_options_keyboard()
        )


async def handle_cv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رفع ملف السيرة الذاتية — يدعم وضع التسجيل والتعديل"""
    from database.db import update_user_field
    from keyboards.keyboards import get_edit_profile_keyboard

    state = context.user_data.get("state")
    is_edit_mode = (state == States.EDIT_CV)

    if state not in (States.REG_CV, States.EDIT_CV):
        return

    telegram_id = update.effective_user.id
    file_id = None
    filename = None

    if update.message.document:
        file = update.message.document
        if file.mime_type == "application/pdf":
            file_id = file.file_id
            filename = file.file_name or "cv.pdf"
        else:
            await update.message.reply_text(
                "⚠️ يرجى رفع ملف *PDF* فقط\n_الصور أو ملفات Word غير مدعومة_",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    elif update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        filename = "cv_image.jpg"

    if not file_id:
        return

    if is_edit_mode:
        # وضع التعديل — احفظ مباشرة في قاعدة البيانات
        update_user_field(telegram_id, "cv_file_id", file_id)
        update_user_field(telegram_id, "cv_filename", filename)
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text(
            "✅ *تم تحديث السيرة الذاتية بنجاح!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
    else:
        # وضع التسجيل — احفظ مؤقتاً
        context.user_data.setdefault("temp_profile", {})["cv_file_id"] = file_id
        context.user_data["temp_profile"]["cv_filename"] = filename
        await update.message.reply_text(
            "✅ *تم رفع السيرة الذاتية بنجاح!*",
            parse_mode=ParseMode.MARKDOWN
        )
        await ask_linkedin(update, context)


async def ask_linkedin(update, context):
    """طلب لينكد إن (اختياري)"""
    context.user_data["state"] = States.REG_LINKEDIN
    msg = (
        "🔗 أدخل *رابط LinkedIn* الخاص بك (اختياري)\n"
        "_مثال: https://linkedin.com/in/yourname_"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_skip_keyboard("skip_linkedin")
        )
    else:
        await update.message.reply_text(
            msg, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_skip_keyboard("skip_linkedin")
        )


async def show_profile_summary(update, context):
    """عرض ملخص الملف الشخصي قبل الحفظ"""
    profile = context.user_data.get("temp_profile", {})

    cv_status = "✅ تم الرفع" if profile.get("cv_file_id") else "❌ لم يُرفع"

    summary = (
        "🎉 *ملفك الشخصي جاهز!* تحقق من البيانات:\n\n"
        f"👤 *الاسم:* {profile.get('full_name_ar', 'غير محدد')}\n"
        f"🌐 *الاسم (EN):* {profile.get('full_name_en', 'غير محدد')}\n"
        f"📍 *المنطقة:* {profile.get('region', 'غير محدد')}\n"
        f"🎯 *المجال:* {profile.get('category', 'غير محدد')}\n"
        f"🔍 *التخصص:* {profile.get('specialization', 'غير محدد')}\n"
        f"🎓 *المؤهل:* {profile.get('education_level', 'غير محدد')}\n"
        f"⭐ *الخبرة:* {profile.get('experience_level', 'غير محدد')}\n"
        f"🏢 *نوع الدوام:* {profile.get('work_type', 'غير محدد')}\n"
        f"💰 *الراتب:* {profile.get('salary_range', 'غير محدد')}\n"
        f"📧 *الإيميل:* {profile.get('email', 'لم يُضف')}\n"
        f"📱 *الجوال:* {profile.get('phone', 'لم يُضف')}\n"
        f"📄 *السيرة الذاتية:* {cv_status}\n"
        f"🔗 *LinkedIn:* {'✅' if profile.get('linkedin_url') else '❌'}\n"
    )

    msg = update.callback_query if update.callback_query else update.message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            summary, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_confirm_profile_keyboard()
        )
    else:
        await update.message.reply_text(
            summary, parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_confirm_profile_keyboard()
        )


async def confirm_and_save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ الملف الشخصي نهائياً"""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    profile = context.user_data.get("temp_profile", {})
    profile["registration_complete"] = 1

    success = save_user(telegram_id, profile)

    if success:
        await query.edit_message_text(
            "🎊 *تم حفظ ملفك الشخصي بنجاح!*\n\n"
            "✅ ستصلك الآن إشعارات بالوظائف المناسبة لك فور نزولها\n"
            "🤖 يمكنك تفعيل التقديم التلقائي من الإعدادات\n\n"
            "نتمنى لك التوفيق! 🌟",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data["state"] = States.MAIN_MENU
        context.user_data["temp_profile"] = {}
    else:
        await query.edit_message_text(
            "❌ حدث خطأ في الحفظ، يرجى المحاولة مجدداً",
            reply_markup=get_back_to_menu_keyboard()
        )
