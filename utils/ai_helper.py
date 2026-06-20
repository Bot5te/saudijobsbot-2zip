"""
مساعد الذكاء الاصطناعي - Groq AI Integration
يستخدم Groq للتحليل الذكي للوظائف والمطابقة وتوليد خطابات التقديم
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = "llama-3.1-8b-instant"


def get_groq_client():
    """إنشاء عميل Groq"""
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"❌ فشل إنشاء عميل Groq: {e}")
        return None


def ai_parse_job(text: str) -> Optional[dict]:
    """
    تحليل ذكي لنص إعلان الوظيفة باستخدام Groq
    يستخرج: المسمى، الشركة، المنطقة، التخصص، الراتب، الموعد النهائي
    """
    client = get_groq_client()
    if not client:
        return None

    prompt = f"""أنت محلل وظائف خبير في السوق السعودي. حلل النص التالي واستخرج معلومات الوظيفة بدقة.

النص:
\"\"\"
{text[:2000]}
\"\"\"

أرجع JSON فقط بهذا الشكل (لا تضف أي نص آخر):
{{
  "title": "المسمى الوظيفي بالعربية",
  "company": "اسم الشركة أو المؤسسة",
  "region": "المدينة أو المنطقة في السعودية (مثل: الرياض، جدة، الدمام، عن بُعد)",
  "category": "التخصص الرئيسي (مثل: تقنية المعلومات، الهندسة، الصحة، الإدارة، التعليم)",
  "specialization": "التخصص الدقيق (مثل: مطور بايثون، محاسب، ممرض)",
  "salary": "الراتب أو النطاق المذكور أو null",
  "work_type": "نوع الدوام: حضوري أو عن بُعد أو هجين أو دوام جزئي",
  "deadline": "الموعد النهائي للتقديم أو null",
  "requirements": "أهم متطلبات الوظيفة في جملة أو جملتين",
  "is_job_post": true
}}

إذا لم يكن النص إعلان وظيفة، أرجع: {{"is_job_post": false}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()

        # استخراج JSON من الرد
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        data = json.loads(raw)
        return data if data.get("is_job_post", True) else None

    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ فشل تحليل JSON من Groq: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ خطأ في Groq AI parse: {e}")
        return None


def ai_match_score(user: dict, job: dict) -> int:
    """
    حساب درجة تطابق ذكية بين المستخدم والوظيفة (0-100)
    يأخذ بعين الاعتبار: التخصص، الخبرة، المنطقة، نوع الدوام، الراتب
    """
    client = get_groq_client()
    if not client:
        return _basic_match_score(user, job)

    user_profile = f"""
- التخصص: {user.get('category', '')} / {user.get('specialization', '')}
- الخبرة: {user.get('experience_level', '')}
- المنطقة: {user.get('region', '')}
- المؤهل: {user.get('education_level', '')}
- نوع الدوام المفضل: {user.get('work_type', '')}
- الراتب المتوقع: {user.get('salary_range', '')}
""".strip()

    job_info = f"""
- المسمى: {job.get('title', '')}
- الشركة: {job.get('company', '')}
- التخصص: {job.get('category', '')} / {job.get('specialization', '')}
- المنطقة: {job.get('region', '')}
- الراتب: {job.get('salary', '')}
- نوع الدوام: {job.get('work_type', '')}
- المتطلبات: {job.get('requirements', '')}
""".strip()

    prompt = f"""قيّم مدى تطابق هذا المرشح مع هذه الوظيفة في السوق السعودي.

ملف المرشح:
{user_profile}

تفاصيل الوظيفة:
{job_info}

أرجع رقماً فقط من 0 إلى 100 يمثل نسبة التطابق. لا تضف أي نص آخر."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10,
        )
        score_text = response.choices[0].message.content.strip()
        score = int(''.join(filter(str.isdigit, score_text))[:3])
        return min(100, max(0, score))
    except Exception as e:
        logger.warning(f"⚠️ فشل حساب درجة التطابق: {e}")
        return _basic_match_score(user, job)


def _basic_match_score(user: dict, job: dict) -> int:
    """حساب درجة تطابق بسيطة بدون AI"""
    score = 50
    if user.get("category") and user.get("category") == job.get("category"):
        score += 30
    if user.get("region") == job.get("region"):
        score += 15
    elif user.get("region") in ("أي منطقة", "عن بُعد (Remote)"):
        score += 5
    if user.get("work_type") and job.get("work_type") and \
       user.get("work_type") in (job.get("work_type", ""), "🔄 أي نوع"):
        score += 5
    return min(100, score)


def ai_generate_cover_letter(user: dict, job: dict) -> str:
    """
    توليد خطاب تقديم مخصص باستخدام Groq AI
    """
    client = get_groq_client()
    if not client:
        return _default_cover_letter(user, job)

    prompt = f"""اكتب خطاب تقديم وظيفة احترافي باللغة العربية للمعلومات التالية.

معلومات المتقدم:
- الاسم: {user.get('full_name_ar', 'المتقدم')}
- التخصص: {user.get('specialization', user.get('category', ''))}
- الخبرة: {user.get('experience_level', '')}
- المؤهل: {user.get('education_level', '')}

تفاصيل الوظيفة:
- المسمى: {job.get('title', 'الوظيفة')}
- الشركة: {job.get('company', 'الشركة')}
- المنطقة: {job.get('region', '')}
- المتطلبات: {job.get('requirements', '')}

اكتب خطاباً قصيراً ومحترفاً (3-4 فقرات) يبرز:
1. سبب التقديم واهتمام المتقدم بالوظيفة
2. أبرز مؤهلاته وخبراته المرتبطة
3. دعوة للمقابلة

الخطاب يجب أن يبدأ بـ "السلام عليكم ورحمة الله وبركاته" وينتهي بالتوقيع."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ خطأ في توليد خطاب التقديم: {e}")
        return _default_cover_letter(user, job)


def _default_cover_letter(user: dict, job: dict) -> str:
    """خطاب تقديم افتراضي بدون AI"""
    name = user.get('full_name_ar') or user.get('full_name_en') or 'المتقدم'
    job_title = job.get('title', 'الوظيفة')
    company = job.get('company', 'الشركة')
    spec = user.get('specialization') or user.get('category', '')
    exp = user.get('experience_level', '')
    edu = user.get('education_level', '')

    return f"""السلام عليكم ورحمة الله وبركاته،

أتقدم بطلبي للانضمام إلى فريقكم المتميز في وظيفة {job_title} بـ{company}.

أنا {name}، أحمل {edu} في مجال {spec}، ولدي {exp} من الخبرة العملية. أؤمن بأن مؤهلاتي وخبراتي تتوافق مع متطلبات هذه الوظيفة، وأنا متحمس للمساهمة في نجاح مؤسستكم.

أرجو مراجعة سيرتي الذاتية المرفقة، وأنا مستعد لأي مقابلة في الوقت المناسب لكم.

مع خالص التقدير والاحترام،
{name}"""


def ai_suggest_improvements(user: dict) -> str:
    """
    اقتراحات ذكية لتحسين الملف الشخصي
    """
    client = get_groq_client()
    if not client:
        return "💡 أكمل ملفك الشخصي وارفع سيرتك الذاتية لزيادة فرصك!"

    profile_completeness = []
    if not user.get("cv_file_id"):
        profile_completeness.append("لا توجد سيرة ذاتية")
    if not user.get("linkedin_url"):
        profile_completeness.append("لا يوجد رابط LinkedIn")
    if not user.get("email"):
        profile_completeness.append("لا يوجد بريد إلكتروني")

    if not profile_completeness:
        return "✅ ملفك الشخصي مكتمل! استمر في التقديم على الوظائف."

    prompt = f"""باحث وظيفي في السعودية، تخصصه {user.get('specialization', user.get('category', 'غير محدد'))}, 
خبرته {user.get('experience_level', 'غير محددة')}.

نواقص في ملفه: {', '.join(profile_completeness)}

اكتب نصيحة واحدة قصيرة (جملة أو جملتين) بالعربية تشجعه على إكمال ملفه وتوضح فائدة ذلك."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150,
        )
        return "💡 " + response.choices[0].message.content.strip()
    except Exception:
        return "💡 أكمل ملفك الشخصي وارفع سيرتك الذاتية لزيادة فرصك!"
