# PATH: GovScheme/database/admin_bootstrap.py
"""
Admin bootstrap/synchronization mechanism (master prompt: "ADMIN USERS").

Safe to run any number of times (idempotent):
- If an email in Config.ADMIN_EMAILS already has a user account, it is
  promoted to admin (is_admin=1) if not already.
- If it doesn't have an account yet, a new admin account is created with a
  freshly generated random password, printed ONCE to the console/log (never
  stored in plaintext, never written to a file). The owner should log in
  and change it immediately from Profile settings.
- Accounts that are no longer listed in ADMIN_EMAIL_1..4 are NOT
  automatically demoted, since an admin may be added under a temporary env
  configuration and demoting silently could lock someone out unexpectedly;
  demotion is a deliberate admin action instead (see routes/admin_routes.py).

This is called from database/build_db.py (fresh installs) AND from
app.py at process startup (so a running deployment picks up newly-added
ADMIN_EMAIL_* values from .env without a manual rebuild step).
"""
import secrets

from werkzeug.security import generate_password_hash


def sync_admins(conn=None):
    """
    conn: an optional sqlite3.Connection to reuse (e.g. from build_db.py,
    which already has one open). If not given, opens/closes its own via
    models.db.get_connection().
    Returns a list of (email, action) tuples for logging/printing.
    """
    from config import Config

    own_connection = conn is None
    if own_connection:
        from models.db import get_connection
        conn = get_connection()

    results = []
    cur = conn.cursor()
    for email in Config.ADMIN_EMAILS:
        existing = cur.execute("SELECT user_id, is_admin FROM users WHERE lower(email) = ?", (email,)).fetchone()
        if existing:
            user_id = existing["user_id"] if hasattr(existing, "keys") else existing[0]
            is_admin = existing["is_admin"] if hasattr(existing, "keys") else existing[1]
            if not is_admin:
                cur.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
                results.append((email, "promoted"))
            else:
                results.append((email, "already_admin"))
        else:
            temp_password = secrets.token_urlsafe(9)  # ~12 char random password
            cur.execute("""
                INSERT INTO users (full_name, email, password_hash, is_admin, preferred_language)
                VALUES (?, ?, ?, 1, 'English')
            """, (email.split("@")[0].title(), email, generate_password_hash(temp_password)))
            results.append((email, f"created (temporary password: {temp_password})"))

    conn.commit()
    if own_connection:
        conn.close()

    for email, action in results:
        print(f"[admin_bootstrap] {email}: {action}")
    return results


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sync_admins()
