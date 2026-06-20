"""
معالج الأزرار - Callback Query Handler
يعالج جميع ضغطات الأزرار inline في البوت
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config.settings import States
from keyboards.keyboards import (
    get_main_menu_keyboard, get_back_to_menu_keyboard,
    get_notification_settings_keyboard, get_edit_profile_keyboard
)
from database.db import (
    get_user, update_user_field, save_application,
    get_user_stats, get_recent_jobs, get_job
)
from handlers.registration import (
    start_registration, ask_region, ask_category, ask_specialization,
    ask_education, ask_experience, ask_work_type, ask_salary,
    ask_email, ask_phone, ask_cv, ask_linkedin,
    show_profile_summary, confirm_and_save_profile
)
from handlers.edit_profile import (
    edit_name, edit_region, edit_specialization, edit_education,
    edit_experience, edit_work_type, edit_salary,
    edit_email_field, edit_cv_field, edit_linkedin_field,
    handle_edit_callback
)
from utils.email_sender import (
    start_email_setup, execute_auto_apply,
    get_email_credentials, delete_email_credentials,
    _email_actions_keyboard
)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموزّع الرئيسي لجميع callback queries"""
    query = update.callback_query
    data = query.data
    telegram_id = update.effective_user.id

    # ─── تمرير للمعالج الخاص بوضع التعديل أولاً ───
    editing_field = context.user_data.get("editing_field")
    if editing_field or data == "cancel_edit":
        handled = await handle_edit_callback(update, context)
        if handled:
            return

    # ─── زر الرجوع العام ───
    if data == "back":
        await query.answer()
        user = get_user(telegram_id)
        if user and user.get("registration_complete"):
            name = user.get("full_name_ar", "صديقي")
            await query.edit_message_text(
                f"مرحباً *{name}* 👋\nماذا تريد أن تفعل؟",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            from keyboards.keyboards import get_start_keyboard
            from config.settings import WELCOME_MESSAGE
            await query.edit_message_text(
                WELCOME_MESSAGE,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_start_keyboard()
            )
        return

    # ─── التسجيل ───
    elif data == "start_registration":
        await start_registration(update, context)

    elif data == "back_to_categories":
        await ask_category(update, context)

    elif data == "confirm_profile":
        await confirm_and_save_profile(update, context)

    elif data == "edit_profile_before_save":
        from handlers.registration import show_profile_summary
        context.user_data["state"] = States.MAIN_MENU
        await query.edit_message_text(
            "✏️ *تعديل الملف الشخصي*\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )

    # ─── اختيار المنطقة (في التسجيل) ───
    elif data.startswith("region_") and not editing_field:
        region = data[len("region_"):]
        context.user_data.setdefault("temp_profile", {})["region"] = region
        await query.answer(f"✅ {region}")
        await ask_category(update, context)

    # ─── اختيار التخصص الرئيسي (في التسجيل) ───
    elif data.startswith("cat_") and not editing_field:
        category = data[len("cat_"):]
        context.user_data.setdefault("temp_profile", {})["category"] = category
        await query.answer(f"✅ {category}")
        await ask_specialization(update, context, category)

    # ─── اختيار التخصص الفرعي (في التسجيل) ───
    elif data.startswith("spec_") and not editing_field:
        spec = data[len("spec_"):]
        context.user_data.setdefault("temp_profile", {})["specialization"] = spec
        await query.answer(f"✅ {spec}")
        await ask_education(update, context)

    # ─── اختيار المؤهل (في التسجيل) ───
    elif data.startswith("edu_") and not editing_field:
        edu = data[len("edu_"):]
        context.user_data.setdefault("temp_profile", {})["education_level"] = edu
        await query.answer(f"✅ {edu}")
        await ask_experience(update, context)

    # ─── اختيار الخبرة (في التسجيل) ───
    elif data.startswith("exp_") and not editing_field:
        exp = data[len("exp_"):]
        context.user_data.setdefault("temp_profile", {})["experience_level"] = exp
        await query.answer(f"✅ {exp}")
        await ask_work_type(update, context)

    # ─── نوع الدوام (في التسجيل) ───
    elif data.startswith("wtype_") and not editing_field:
        wtype = data[len("wtype_"):]
        context.user_data.setdefault("temp_profile", {})["work_type"] = wtype
        await query.answer(f"✅ {wtype}")
        await ask_salary(update, context)

    # ─── الراتب (في التسجيل) ───
    elif data.startswith("sal_") and not editing_field:
        sal = data[len("sal_"):]
        context.user_data.setdefault("temp_profile", {})["salary_range"] = sal
        await query.answer(f"✅ {sal}")
        await ask_email(update, context)

    # ─── تخطي الخطوات ───
    elif data == "skip_name_en":
        await ask_region(update, context)

    elif data == "skip_email":
        await ask_phone(update, context)

    elif data == "skip_phone":
        await ask_cv(update, context)

    elif data == "skip_cv":
        await ask_linkedin(update, context)

    elif data == "skip_linkedin":
        await show_profile_summary(update, context)

    # ─── رفع السيرة الذاتية ───
    elif data in ("upload_cv_pdf", "upload_cv_image"):
        context.user_data["state"] = States.REG_CV
        await query.edit_message_text(
            "📎 *أرسل ملف السيرة الذاتية الآن* 👇\n\n"
            "_يدعم البوت: PDF أو صورة JPG/PNG_",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "manual_cv":
        await query.answer()
        await query.edit_message_text(
            "✍️ *تعبئة البيانات يدوياً*\n\n"
            "هذه الخاصية قادمة قريباً!\n\n"
            "في الوقت الحالي يمكنك رفع ملف PDF أو تخطي هذه الخطوة.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )

    # ─── القائمة الرئيسية ───
    elif data == "main_menu":
        user = get_user(telegram_id)
        name = user.get("full_name_ar", "صديقي") if user else "صديقي"
        await query.edit_message_text(
            f"مرحباً *{name}* 👋\nماذا تريد أن تفعل؟",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard()
        )

    # ─── الملف الشخصي ───
    elif data == "profile":
        await show_profile(update, context)

    # ─── تعديل حقول الملف الشخصي ───
    elif data == "edit_preferences":
        await query.answer()
        await query.edit_message_text(
            "✏️ *تعديل الملف الشخصي*\n\nاختر ما تريد تعديله:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_edit_profile_keyboard()
        )

    elif data == "edit_name":
        await edit_name(update, context)

    elif data == "edit_region":
        await edit_region(update, context)

    elif data == "edit_specialization":
        await edit_specialization(update, context)

    elif data == "edit_education":
        await edit_education(update, context)

    elif data == "edit_experience":
        await edit_experience(update, context)

    elif data == "edit_work_type":
        await edit_work_type(update, context)

    elif data == "edit_salary":
        await edit_salary(update, context)

    elif data == "edit_email":
        await edit_email_field(update, context)

    elif data == "edit_cv":
        await edit_cv_field(update, context)

    elif data == "edit_linkedin":
        await edit_linkedin_field(update, context)

    # ─── إعداد الإيميل للتقديم التلقائي ───
    elif data == "email_setup":
        await start_email_setup(update, context)

    elif data == "setup_email":
        # إعادة توجيه لخطوة إدخال الإيميل
        from utils.email_sender import _ask_email_address
        context.user_data["state"] = States.EMAIL_SETUP_ADDRESS
        await _ask_email_address(query, context)

    elif data == "delete_email_creds":
        await query.answer()
        delete_email_credentials(telegram_id)
        await query.edit_message_text(
            "🗑️ *تم حذف بيانات الإيميل المحفوظة*\n\n"
            "يمكنك ربط إيميل جديد في أي وقت.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )

    elif data == "cancel_email_setup":
        await query.answer()
        context.user_data["state"] = States.MAIN_MENU
        context.user_data.pop("setup_email", None)
        await query.edit_message_text(
            "↩️ تم إلغاء إعداد الإيميل.",
            reply_markup=get_back_to_menu_keyboard()
        )

    # ─── إحصائيات المستخدم ───
    elif data == "my_stats":
        await show_stats(update, context)

    # ─── تصفح الوظائف ───
    elif data == "browse_jobs":
        await show_recent_jobs(update, context)

    # ─── إعدادات الإشعارات ───
    elif data == "notification_settings":
        await show_notification_settings(update, context)

    elif data == "toggle_notifications":
        user = get_user(telegram_id)
        current = user.get("notifications_enabled", 1)
        new_val = 0 if current else 1
        update_user_field(telegram_id, "notifications_enabled", new_val)
        status = "مفعّل 🔔" if new_val else "معطّل 🔕"
        await query.answer(f"الإشعارات: {status}")
        await show_notification_settings(update, context)

    elif data == "toggle_auto_apply":
        user = get_user(telegram_id)
        creds = get_email_credentials(telegram_id)
        if not creds:
            await query.answer()
            await query.edit_message_text(
                "⚠️ *يجب ربط إيميلك أولاً*\n\n"
                "اضغط الزر أدناه لربط Gmail وتفعيل التقديم التلقائي:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_email_actions_keyboard(has_creds=False)
            )
            return
        current = user.get("auto_apply_enabled", 0)
        new_val = 0 if current else 1
        update_user_field(telegram_id, "auto_apply_enabled", new_val)
        status = "مفعّل 🤖" if new_val else "معطّل"
        await query.answer(f"التقديم التلقائي: {status}")
        await show_notification_settings(update, context)

    # ─── التقديم على الوظائف ───
    elif data.startswith("mark_applied_"):
        job_id = int(data.split("_")[-1])
        save_application(telegram_id, job_id, "manual")
        await query.answer("✅ تم تسجيل تقديمك على هذه الوظيفة!")

    elif data.startswith("dismiss_job_"):
        await query.answer("تم تجاهل الوظيفة")
        await query.edit_message_reply_markup(reply_markup=None)

    elif data.startswith("auto_apply_"):
        job_id = int(data.split("_")[-1])
        await query.answer("⏳ جاري التقديم...")
        await execute_auto_apply(
            bot=context.bot,
            telegram_id=telegram_id,
            job_id=job_id,
            chat_id=update.effective_chat.id
        )

    elif data.startswith("save_job_"):
        await query.answer("💾 تم حفظ الوظيفة في قائمتك!")

    elif data.startswith("share_job_"):
        job_id = int(data.split("_")[-1])
        job = get_job(job_id)
        if job:
            share_text = f"💼 {job.get('title', 'وظيفة')}\n🏢 {job.get('company', '')}\n📍 {job.get('region', '')}"
            if job.get("apply_link"):
                share_text += f"\n🔗 {job['apply_link']}"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📤 *شارك هذه الوظيفة:*\n\n{share_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        await query.answer()

    elif data == "my_applications":
        await show_my_applications(update, context)

    # ─── إرسال السيرة الذاتية للمستخدم ───
    elif data == "send_my_cv":
        await send_cv_to_user(update, context)

    # ─── نصائح مهنية ───
    elif data == "career_tips":
        await show_career_tips(update, context)

    # ─── مساعدة ───
    elif data == "help":
        await show_help(update, context)

    # ─── عن البوت ───
    elif data == "about_bot":
        await show_about(update, context)

    # ─── cv menu ───
    elif data == "cv_menu":
        await show_cv_menu(update, context)

    else:
        await query.answer()
        await query.edit_message_text(
            "🚧 *هذه الخاصية قيد التطوير*\n\nستكون متاحة قريباً!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )


# ─────────────────────────────────────────
# دوال العرض
# ─────────────────────────────────────────

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الملف الشخصي"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user:
        await query.edit_message_text("❌ لم يُعثر على ملفك، ابدأ التسجيل أولاً")
        return

    cv_status = "✅ موجود" if user.get("cv_file_id") else "❌ لم يُرفع بعد"
    notif = "🔔 مفعّل" if user.get("notifications_enabled") else "🔕 معطّل"
    auto = "🤖 مفعّل" if user.get("auto_apply_enabled") else "❌ معطّل"
    creds = get_email_credentials(telegram_id)
    email_linked = f"✅ `{creds['sender_email']}`" if creds else "❌ لم يُربط"

    text = (
        "👤 *ملفك الشخصي*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📛 *الاسم:* {user.get('full_name_ar', '—')}\n"
        f"🌐 *(EN):* {user.get('full_name_en', '—')}\n"
        f"📍 *المنطقة:* {user.get('region', '—')}\n"
        f"🎯 *المجال:* {user.get('category', '—')}\n"
        f"🔍 *التخصص:* {user.get('specialization', '—')}\n"
        f"🎓 *المؤهل:* {user.get('education_level', '—')}\n"
        f"⭐ *الخبرة:* {user.get('experience_level', '—')}\n"
        f"🏢 *نوع الدوام:* {user.get('work_type', '—')}\n"
        f"💰 *الراتب:* {user.get('salary_range', '—')}\n"
        f"📄 *السيرة:* {cv_status}\n"
        f"📱 *الجوال:* {user.get('phone', '—')}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📧 *إيميل التقديم:* {email_linked}\n"
        f"🔔 *الإشعارات:* {notif}\n"
        f"🤖 *التقديم التلقائي:* {auto}\n"
    )

    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_edit_profile_keyboard()
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدم مع اقتراح AI"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    stats = get_user_stats(telegram_id)
    user = get_user(telegram_id)

    # اقتراح AI لتحسين الملف الشخصي
    try:
        from utils.ai_helper import ai_suggest_improvements
        suggestion = ai_suggest_improvements(user) if user else ""
    except Exception:
        suggestion = ""

    text = (
        "📊 *إحصائياتك*\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📨 *وظائف وصلتك:* {stats['total_notifications']}\n"
        f"✅ *تقديمات مكتملة:* {stats['total_applications']}\n"
        "━━━━━━━━━━━━━━━━\n"
        "_استمر في التقديم، النجاح قادم_ 💪"
    )

    if suggestion:
        text += f"\n\n{suggestion}"

    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )


async def show_recent_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض أحدث الوظائف"""
    query = update.callback_query
    await query.answer()
    jobs = get_recent_jobs(5)

    if not jobs:
        await query.edit_message_text(
            "📭 *لا توجد وظائف متاحة حالياً*\n\nسنُشعرك فور نزول وظائف جديدة 🔔",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )
        return

    from keyboards.keyboards import get_job_card_keyboard
    from utils.notifier import build_job_card_text

    await query.edit_message_text(
        f"💼 *أحدث {len(jobs)} وظائف:*",
        parse_mode=ParseMode.MARKDOWN
    )
    for job in jobs:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=build_job_card_text(job),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_job_card_keyboard(
                job["id"],
                job.get("apply_link"),
                job.get("apply_email")
            )
        )


async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات الإشعارات"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)
    creds = get_email_credentials(telegram_id)

    notif = bool(user.get("notifications_enabled", 1))
    auto = bool(user.get("auto_apply_enabled", 0))
    email_status = f"📧 `{creds['sender_email']}`" if creds else "📧 _لم يُربط بعد_"

    await query.edit_message_text(
        "🔔 *إعدادات الإشعارات والتقديم*\n\n"
        f"{email_status}\n\n"
        "اضغط للتبديل:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_notification_settings_keyboard(notif, auto)
    )


async def show_my_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض تقديمات المستخدم"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id

    from database.db import get_connection
    conn = get_connection()
    apps = conn.execute("""
        SELECT a.apply_method, a.applied_at, j.title, j.company, j.region
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.user_telegram_id = ?
        ORDER BY a.applied_at DESC
        LIMIT 10
    """, (telegram_id,)).fetchall()
    conn.close()

    if not apps:
        await query.edit_message_text(
            "📋 *تقديماتك*\n\nلم تقدّم على أي وظيفة بعد!\n\nابحث عن وظائف وقدّم عليها 💼",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )
        return

    method_icons = {"auto_email": "🤖", "manual": "✋", "link": "🔗"}
    text = "📋 *آخر تقديماتك:*\n\n"
    for app in apps:
        icon = method_icons.get(app["apply_method"], "📝")
        text += (
            f"{icon} *{app['company'] or 'غير محدد'}*\n"
            f"   💼 {app['title']}\n"
            f"   📍 {app['region'] or '—'} | 📅 {str(app['applied_at'])[:10]}\n"
            "─────────────\n"
        )

    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )


async def show_cv_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة السيرة الذاتية"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    from keyboards.keyboards import get_cv_options_keyboard
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    has_cv = bool(user and user.get("cv_file_id"))
    status = "✅ *لديك سيرة ذاتية محفوظة*" if has_cv else "❌ *لا توجد سيرة ذاتية بعد*"

    keyboard = [
        [InlineKeyboardButton("📎 رفع / تحديث السيرة الذاتية", callback_data="edit_cv")],
    ]
    if has_cv:
        keyboard.append([InlineKeyboardButton("📤 إرسال سيرتي لي", callback_data="send_my_cv")])
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="main_menu")])

    await query.edit_message_text(
        f"📄 *السيرة الذاتية*\n\n{status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_career_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نصائح مهنية مدعومة بالذكاء الاصطناعي"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    await query.edit_message_text(
        "🤖 _جاري توليد نصيحة مخصصة لك بالذكاء الاصطناعي..._",
        parse_mode=ParseMode.MARKDOWN
    )

    # نصائح احتياطية
    fallback_tips = [
        "📌 *خصّص سيرتك الذاتية لكل وظيفة*\nاجعل الكلمات المفتاحية تطابق الوصف الوظيفي.",
        "📌 *قدّم خلال أول 24 ساعة*\nالمتقدمون الأوائل يحظون باهتمام أكبر.",
        "📌 *أضف ملف LinkedIn قوي*\n85% من أصحاب العمل يتحققون من LinkedIn قبل المقابلة.",
        "📌 *لا تترك خانة الراتب فارغة*\nضع نطاقاً بحثت عنه مسبقاً في السوق.",
        "📌 *خطاب التقديم يُفرق*\nوظيفة مخصصة أفضل من عشر وظائف عشوائية.",
    ]

    try:
        from utils.ai_helper import get_groq_client, MODEL
        client = get_groq_client()

        if client and user:
            spec = user.get("specialization") or user.get("category") or "عام"
            exp = user.get("experience_level") or "غير محدد"
            region = user.get("region") or "السعودية"

            prompt = f"""أنت مستشار مهني خبير بسوق العمل السعودي.
قدم نصيحة مهنية عملية ومحددة لشخص يبحث عن عمل بهذه المواصفات:
- التخصص: {spec}
- الخبرة: {exp}
- المنطقة: {region}

اكتب نصيحة واحدة قصيرة ومفيدة (3-5 جمل) تتعلق بسوق العمل السعودي تحديداً.
ابدأها بـ 📌 ثم عنوان بارز، ثم الشرح."""

            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=200,
            )
            tip = response.choices[0].message.content.strip()
        else:
            import random
            tip = random.choice(fallback_tips)
    except Exception:
        import random
        tip = random.choice(fallback_tips)

    await query.edit_message_text(
        f"💡 *نصيحة مهنية مخصصة لك*\n\n{tip}\n\n_🤖 مدعوم بالذكاء الاصطناعي_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "❓ *كيف يعمل البوت؟*\n\n"
        "1️⃣ *أنشئ ملفك الشخصي* مع تحديد تخصصك ومنطقتك\n"
        "2️⃣ *ارفع سيرتك الذاتية* ليتمكن البوت من التقديم عنك\n"
        "3️⃣ *اربط Gmail* من الإعدادات للتقديم التلقائي\n"
        "4️⃣ *انتظر الإشعارات* وقدّم بضغطة واحدة!\n\n"
        "📞 للدعم تواصل مع المطوّر",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )


async def send_cv_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال السيرة الذاتية للمستخدم"""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    user = get_user(telegram_id)

    if not user or not user.get("cv_file_id"):
        await query.edit_message_text(
            "❌ *لا توجد سيرة ذاتية محفوظة*\n\nارفع سيرتك الذاتية أولاً.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )
        return

    try:
        await context.bot.send_document(
            chat_id=telegram_id,
            document=user["cv_file_id"],
            caption="📄 *سيرتك الذاتية المحفوظة*",
            parse_mode=ParseMode.MARKDOWN
        )
        await query.edit_message_text(
            "✅ *تم إرسال سيرتك الذاتية إليك!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_to_menu_keyboard()
        )
    except Exception as e:
        await query.edit_message_text(
            "❌ حدث خطأ في إرسال السيرة الذاتية. حاول مرة أخرى.",
            reply_markup=get_back_to_menu_keyboard()
        )


async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🤖 *بوت التوظيف السعودي*\n\n"
        "بوت ذكي يساعدك في إيجاد وظيفة أحلامك\n"
        "في المملكة العربية السعودية 🇸🇦\n\n"
        "🔸 يتابع قنوات التوظيف تلقائياً\n"
        "🔸 يُشعرك بالوظائف المناسبة فوراً\n"
        "🔸 يُقدّم بإيميلك الحقيقي تلقائياً\n"
        "🔸 يحفظ سيرتك الذاتية ويديرها\n\n"
        "_صُنع بـ 🤍 للباحثين عن عمل في السعودية_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_to_menu_keyboard()
    )
