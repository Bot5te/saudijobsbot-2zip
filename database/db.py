"""
قاعدة البيانات - نماذج البيانات والعمليات الأساسية
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict


DB_PATH = "saudi_jobs_bot.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """إنشاء جداول قاعدة البيانات"""
    conn = get_connection()
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name_ar TEXT,
            full_name_en TEXT,
            region TEXT,
            category TEXT,
            specialization TEXT,
            education_level TEXT,
            experience_level TEXT,
            work_type TEXT,
            salary_range TEXT,
            email TEXT,
            phone TEXT,
            linkedin_url TEXT,
            cv_file_id TEXT,
            cv_filename TEXT,
            is_active INTEGER DEFAULT 1,
            notifications_enabled INTEGER DEFAULT 1,
            auto_apply_enabled INTEGER DEFAULT 0,
            registration_complete INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول الوظائف
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_message_id INTEGER UNIQUE,
            title TEXT NOT NULL,
            company TEXT,
            region TEXT,
            category TEXT,
            specialization TEXT,
            description TEXT,
            requirements TEXT,
            apply_link TEXT,
            apply_email TEXT,
            salary TEXT,
            work_type TEXT,
            deadline TEXT,
            is_active INTEGER DEFAULT 1,
            source_channel TEXT,
            raw_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول التقديمات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_telegram_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            apply_method TEXT,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (user_telegram_id) REFERENCES users (telegram_id),
            FOREIGN KEY (job_id) REFERENCES jobs (id),
            UNIQUE(user_telegram_id, job_id)
        )
    """)

    # جدول إشعارات الوظائف المرسلة
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_telegram_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            action TEXT DEFAULT 'sent',
            UNIQUE(user_telegram_id, job_id)
        )
    """)

    # جدول بيانات إيميل التقديم التلقائي
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_credentials (
            telegram_id INTEGER PRIMARY KEY,
            sender_email TEXT NOT NULL,
            app_password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✅ تم إنشاء قاعدة البيانات بنجاح")


# ─────────────────────────────────────────
# عمليات المستخدمين
# ─────────────────────────────────────────

def save_user(telegram_id: int, data: dict) -> bool:
    conn = get_connection()
    try:
        existing = get_user(telegram_id)
        if existing:
            fields = ", ".join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [datetime.now().isoformat(), telegram_id]
            conn.execute(
                f"UPDATE users SET {fields}, updated_at = ? WHERE telegram_id = ?",
                values
            )
        else:
            data["telegram_id"] = telegram_id
            data["created_at"] = datetime.now().isoformat()
            placeholders = ", ".join(["?" for _ in data])
            columns = ", ".join(data.keys())
            conn.execute(
                f"INSERT INTO users ({columns}) VALUES ({placeholders})",
                list(data.values())
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ في حفظ المستخدم: {e}")
        return False
    finally:
        conn.close()


def get_user(telegram_id: int) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_field(telegram_id: int, field: str, value) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE users SET {field} = ?, updated_at = ? WHERE telegram_id = ?",
            (value, datetime.now().isoformat(), telegram_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ في تحديث المستخدم: {e}")
        return False
    finally:
        conn.close()


def get_matching_users(job: dict) -> List[Dict]:
    """إيجاد المستخدمين المناسبين للوظيفة"""
    conn = get_connection()
    job_region = job.get("region", "") or ""
    job_category = job.get("category", "") or ""
    job_specialization = job.get("specialization", "") or ""

    users = conn.execute("""
        SELECT * FROM users
        WHERE registration_complete = 1
        AND notifications_enabled = 1
        AND is_active = 1
        AND (
            region = ?
            OR region = 'أي منطقة'
            OR ? = 'عن بُعد (Remote)'
            OR region = 'عن بُعد (Remote)'
        )
        AND (
            category = ?
            OR (? = '' OR ? IS NULL)
        )
    """, (
        job_region,
        job_region,
        job_category,
        job_category,
        job_category,
    )).fetchall()
    conn.close()
    return [dict(u) for u in users]


def get_user_stats(telegram_id: int) -> Dict:
    conn = get_connection()
    apps = conn.execute(
        "SELECT COUNT(*) as total FROM applications WHERE user_telegram_id = ?",
        (telegram_id,)
    ).fetchone()
    notifications = conn.execute(
        "SELECT COUNT(*) as total FROM job_notifications WHERE user_telegram_id = ?",
        (telegram_id,)
    ).fetchone()
    conn.close()
    return {
        "total_applications": apps["total"] if apps else 0,
        "total_notifications": notifications["total"] if notifications else 0
    }


# ─────────────────────────────────────────
# عمليات الوظائف
# ─────────────────────────────────────────

def save_job(job_data: dict) -> Optional[int]:
    conn = get_connection()
    try:
        channel_msg_id = job_data.get("channel_message_id")

        # إذا كانت الوظيفة موجودة مسبقاً، أرجع id الصف الموجود
        if channel_msg_id:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE channel_message_id = ?",
                (channel_msg_id,)
            ).fetchone()
            if existing:
                conn.close()
                return existing["id"]

        cursor = conn.execute("""
            INSERT INTO jobs
            (channel_message_id, title, company, region, category, specialization,
             description, requirements, apply_link, apply_email, salary,
             work_type, deadline, source_channel, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            channel_msg_id,
            job_data.get("title", "وظيفة غير محددة"),
            job_data.get("company"),
            job_data.get("region"),
            job_data.get("category"),
            job_data.get("specialization"),
            job_data.get("description"),
            job_data.get("requirements"),
            job_data.get("apply_link"),
            job_data.get("apply_email"),
            job_data.get("salary"),
            job_data.get("work_type"),
            job_data.get("deadline"),
            job_data.get("source_channel"),
            job_data.get("raw_text")
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"❌ خطأ في حفظ الوظيفة: {e}")
        return None
    finally:
        conn.close()


def get_job(job_id: int) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_jobs(limit: int = 10) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE is_active = 1 ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_application(user_id: int, job_id: int, method: str) -> bool:
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO applications
            (user_telegram_id, job_id, status, apply_method)
            VALUES (?, ?, 'applied', ?)
        """, (user_id, job_id, method))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطأ في حفظ التقديم: {e}")
        return False
    finally:
        conn.close()


def mark_notification_sent(user_id: int, job_id: int):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO job_notifications (user_telegram_id, job_id)
            VALUES (?, ?)
        """, (user_id, job_id))
        conn.commit()
    except:
        pass
    finally:
        conn.close()


def was_notified(user_id: int, job_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("""
        SELECT 1 FROM job_notifications
        WHERE user_telegram_id = ? AND job_id = ?
    """, (user_id, job_id)).fetchone()
    conn.close()
    return row is not None
