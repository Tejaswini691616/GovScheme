# PATH: GovScheme/models/complaint_model.py
"""
Grievance/customer-care system (master prompt: "CUSTOMER CARE / GRIEVANCE
SYSTEM"). Complaint numbers look like SG-2026-00001 - year plus a
zero-padded per-year sequence, generated from the count of complaints
already created this year (safe for a single-writer SQLite prototype;
a high-concurrency production deployment would want a dedicated sequence
table instead).
"""
import datetime

from models.db import query, query_one, execute

VALID_CATEGORIES = [
    "Application Issue", "Eligibility Issue", "Wrong Scheme Information",
    "Website Problem", "Chatbot Problem", "Voice Problem",
    "Translation Problem", "RPA Problem", "Other",
]

VALID_STATUSES = [
    "OPEN", "AI_ASSISTING", "WAITING_FOR_USER", "ESCALATED",
    "IN_PROGRESS", "RESOLVED", "CLOSED",
]


def _generate_complaint_number() -> str:
    year = datetime.date.today().year
    row = query_one("SELECT COUNT(*) as c FROM complaints WHERE complaint_number LIKE ?", (f"SG-{year}-%",))
    seq = (row["c"] if row else 0) + 1
    return f"SG-{year}-{seq:05d}"


def create_complaint(user_id: int, category: str, subject: str, description: str,
                      language: str = "English", related_application_id: int = None) -> dict:
    if category not in VALID_CATEGORIES:
        category = "Other"
    complaint_number = _generate_complaint_number()
    complaint_id = execute("""
        INSERT INTO complaints (complaint_number, user_id, category, subject, description,
            language, status, related_application_id)
        VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
    """, (complaint_number, user_id, category, subject, description, language, related_application_id))
    add_complaint_message(complaint_id, "user", user_id, description)
    return {"complaint_id": complaint_id, "complaint_number": complaint_number}


def add_complaint_message(complaint_id: int, sender_type: str, sender_id, message: str):
    execute("""
        INSERT INTO complaint_messages (complaint_id, sender_type, sender_id, message)
        VALUES (?, ?, ?, ?)
    """, (complaint_id, sender_type, sender_id, message))
    execute("UPDATE complaints SET updated_at = datetime('now') WHERE complaint_id = ?", (complaint_id,))


def get_complaint(complaint_id: int):
    return query_one("SELECT * FROM complaints WHERE complaint_id = ?", (complaint_id,))


def get_complaints_for_user(user_id: int):
    return query("SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC", (user_id,))


def get_complaint_messages(complaint_id: int):
    return query("SELECT * FROM complaint_messages WHERE complaint_id = ? ORDER BY created_at ASC", (complaint_id,))


def get_all_complaints():
    return query("""
        SELECT c.*, u.full_name as user_name, u.email as user_email
        FROM complaints c JOIN users u ON c.user_id = u.user_id
        ORDER BY c.created_at DESC
    """)


def update_complaint_status(complaint_id: int, status: str, resolution: str = None, assigned_admin: int = None):
    if status not in VALID_STATUSES:
        return
    execute("""
        UPDATE complaints SET status = ?, resolution = COALESCE(?, resolution),
            assigned_admin = COALESCE(?, assigned_admin), updated_at = datetime('now')
        WHERE complaint_id = ?
    """, (status, resolution, assigned_admin, complaint_id))
