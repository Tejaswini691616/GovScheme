# PATH: GovScheme/models/notification_model.py
from models.db import query, query_one, execute


def create_notification(user_id: int, title: str, message: str):
    return execute("""
        INSERT INTO notifications (user_id, title, message, status)
        VALUES (?, ?, ?, 'Unread')
    """, (user_id, title, message))


def get_notifications_for_user(user_id: int):
    return query("""
        SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))


def mark_as_read(notification_id: int, user_id: int = None):
    # Always scope a citizen notification update to its owner. The optional
    # user_id keeps the model backward-compatible for internal callers, while
    # route handlers should pass the current session user.
    if user_id is None:
        execute("UPDATE notifications SET status = 'Read' WHERE notification_id = ?", (notification_id,))
    else:
        execute("UPDATE notifications SET status = 'Read' WHERE notification_id = ? AND user_id = ?", (notification_id, user_id))


def mark_all_as_read(user_id: int):
    execute("UPDATE notifications SET status = 'Read' WHERE user_id = ?", (user_id,))


def unread_count(user_id: int) -> int:
    row = query_one("SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND status = 'Unread'", (user_id,))
    return row["c"] if row else 0
