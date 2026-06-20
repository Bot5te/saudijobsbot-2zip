"""
معالج تعديل الملف الشخصي
يسمح للمستخدم بتعديل كل حقل على حدة
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config.settings import States
from keyboards.keyboards import (
    get_edit_profile_keyboard, get_regions_keyboard,
    get_categories_keyboard, get_specializations_keyboard,
    get_education_keyboard, get_experience_keyboard,
    get_work_type_keyboard, get_salary_keyboard,
    get_back_to_menu_keyboard, get_skip_keyboard
)
from database.db import get_user, update_user_field, save_user


# ─────────────────────────────────────────
# الدوال الخاصة بكل حقل
# ─────────────────────────────────────────

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل الاسم"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_NAME_AR
    await query.edit_message_text(
        "✏️ *تعديل الاسم*\n\nأدخل اسمك الكامل بالعربية:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_skip_keyboard("cancel_edit")
    )


async def edit_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل المنطقة"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_PROFILE
    context.user_data["editing_field"] = "region"
    await query.edit_message_text(
        "📍 *تعديل المنطقة*\n\nاختر منطقتك:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_regions_keyboard()
    )


async def edit_specialization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل التخصص"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_PROFILE
    context.user_data["editing_field"] = "category"
    await query.edit_message_text(
        "🎯 *تعديل التخصص*\n\nاختر مجالك الرئيسي:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_categories_keyboard()
    )


async def edit_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل المؤهل الدراسي"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_PROFILE
    context.user_data["editing_field"] = "education_level"
    await query.edit_message_text(
        "🎓 *تعديل المؤهل الدراسي*\n\nاختر مؤهلك:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_education_keyboard()
    )


async def edit_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل الخبرة"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_PROFILE
    context.user_data["editing_field"] = "experience_level"
    await query.edit_message_text(
        "⭐ *تعديل سنوات الخبرة*\n\nاختر مستوى خبرتك:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_experience_keyboard()
    )


async def edit_work_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل نوع الدوام"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_PROFILE
    context.user_data["editing_field"] = "work_type"
    await query.edit_message_text(
        "🏢 *تعديل نوع الدوام*\n\nاختر نوع الدوام المفضل:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_work_type_keyboard()
    )


async def edit_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل الراتب المتوقع"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_PROFILE
    context.user_data["editing_field"] = "salary_range"
    await query.edit_message_text(
        "💰 *تعديل الراتب المتوقع*\n\nاختر النطاق المناسب:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_salary_keyboard()
    )


async def edit_email_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل الإيميل"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_EMAIL
    await query.edit_message_text(
        "📧 *تعديل البريد الإلكتروني*\n\nأدخل بريدك الإلكتروني الجديد:\n"
        "_مثال: name@gmail.com_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_skip_keyboard("cancel_edit")
    )


async def edit_cv_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل السيرة الذاتية"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_CV
    from keyboards.keyboards import get_cv_options_keyboard
    await query.edit_message_text(
        "📄 *تحديث السيرة الذاتية*\n\nأرسل الملف الجديد:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_cv_options_keyboard()
    )


async def edit_linkedin_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل LinkedIn"""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = States.EDIT_LINKEDIN
    await query.edit_message_text(
        "🔗 *تعديل رابط LinkedIn*\n\nأدخل الرابط الجديد:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_skip_keyboard("cancel_edit")
    )


# ─────────────────────────────────────────
# معالجة المدخلات النصية في وضع التعديل
# ─────────────────────────────────────────

async def handle_edit_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    معالجة النصوص في وضع التعديل.
    يرجع True إذا تمت المعالجة، False إذا لم تكن في وضع تعديل.
    """
    state = context.user_data.get("state")
    text = update.message.text.strip()
    telegram_id = update.effective_user.id

    if state == States.EDIT_NAME_AR:
        update_user_field(telegram_id, "full_name_ar", text)
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text(
            f"✅ *تم تحديث الاسم إلى:* {text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    elif state == States.EDIT_NAME_EN:
        update_user_field(telegram_id, "full_name_en", text)
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text(
            f"✅ *تم تحديث الاسم الإنجليزي*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    elif state == States.EDIT_EMAIL:
        if "@" in text and "." in text:
            update_user_field(telegram_id, "email", text)
            context.user_data["state"] = States.MAIN_MENU
            await update.message.reply_text(
                f"✅ *تم تحديث الإيميل إلى:* `{text}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_edit_profile_keyboard()
            )
        else:
            await update.message.reply_text(
                "⚠️ إيميل غير صحيح، أعد المحاولة:",
                reply_markup=get_skip_keyboard("cancel_edit")
            )
        return True

    elif state == States.EDIT_LINKEDIN:
        update_user_field(telegram_id, "linkedin_url", text)
        context.user_data["state"] = States.MAIN_MENU
        await update.message.reply_text(
            "✅ *تم تحديث رابط LinkedIn*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    return False


# ─────────────────────────────────────────
# معالجة اختيار الأزرار في وضع التعديل
# ─────────────────────────────────────────

async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    معالجة callback في وضع التعديل.
    يرجع True إذا تمت المعالجة.
    """
    query = update.callback_query
    data = query.data
    telegram_id = update.effective_user.id
    editing_field = context.user_data.get("editing_field")

    # إلغاء التعديل
    if data == "cancel_edit":
        await query.answer()
        context.user_data["state"] = States.MAIN_MENU
        context.user_data.pop("editing_field", None)
        await query.edit_message_text(
            "✏️ *تعديل الملف الشخصي*\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    # في وضع التعديل — المنطقة
    if editing_field == "region" and data.startswith("region_"):
        value = data[len("region_"):]
        update_user_field(telegram_id, "region", value)
        await query.answer(f"✅ تم تحديث المنطقة")
        context.user_data.pop("editing_field", None)
        context.user_data["state"] = States.MAIN_MENU
        await query.edit_message_text(
            f"✅ *تم تحديث المنطقة إلى:* {value}\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    # في وضع التعديل — التخصص الرئيسي
    if editing_field == "category" and data.startswith("cat_"):
        value = data[len("cat_"):]
        update_user_field(telegram_id, "category", value)
        context.user_data["editing_field"] = "specialization"
        await query.answer(f"✅ {value}")
        await query.edit_message_text(
            f"🔍 الآن اختر *التخصص الدقيق* في {value}:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_specializations_keyboard(value)
        )
        return True

    # في وضع التعديل — التخصص الفرعي
    if editing_field == "specialization" and data.startswith("spec_"):
        value = data[len("spec_"):]
        update_user_field(telegram_id, "specialization", value)
        await query.answer(f"✅ تم التحديث")
        context.user_data.pop("editing_field", None)
        context.user_data["state"] = States.MAIN_MENU
        await query.edit_message_text(
            f"✅ *تم تحديث التخصص إلى:* {value}\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    # في وضع التعديل — المؤهل
    if editing_field == "education_level" and data.startswith("edu_"):
        value = data[len("edu_"):]
        update_user_field(telegram_id, "education_level", value)
        await query.answer(f"✅ تم التحديث")
        context.user_data.pop("editing_field", None)
        context.user_data["state"] = States.MAIN_MENU
        await query.edit_message_text(
            f"✅ *تم تحديث المؤهل إلى:* {value}\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    # في وضع التعديل — الخبرة
    if editing_field == "experience_level" and data.startswith("exp_"):
        value = data[len("exp_"):]
        update_user_field(telegram_id, "experience_level", value)
        await query.answer(f"✅ تم التحديث")
        context.user_data.pop("editing_field", None)
        context.user_data["state"] = States.MAIN_MENU
        await query.edit_message_text(
            f"✅ *تم تحديث الخبرة إلى:* {value}\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    # في وضع التعديل — نوع الدوام
    if editing_field == "work_type" and data.startswith("wtype_"):
        value = data[len("wtype_"):]
        update_user_field(telegram_id, "work_type", value)
        await query.answer(f"✅ تم التحديث")
        context.user_data.pop("editing_field", None)
        context.user_data["state"] = States.MAIN_MENU
        await query.edit_message_text(
            f"✅ *تم تحديث نوع الدوام إلى:* {value}\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    # في وضع التعديل — الراتب
    if editing_field == "salary_range" and data.startswith("sal_"):
        value = data[len("sal_"):]
        update_user_field(telegram_id, "salary_range", value)
        await query.answer(f"✅ تم التحديث")
        context.user_data.pop("editing_field", None)
        context.user_data["state"] = States.MAIN_MENU
        await query.edit_message_text(
            f"✅ *تم تحديث الراتب المتوقع*\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )
        return True

    return False
