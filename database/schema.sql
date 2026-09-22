-- PATH: GovScheme/database/schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    dob TEXT, marital_status TEXT, rural_urban TEXT, pin_code TEXT, family_size INTEGER, dependents INTEGER, employment_status TEXT, minority TEXT, disability_percentage REAL, health_insurance TEXT, aadhaar TEXT, bank_account TEXT, ration_card TEXT, existing_benefits TEXT,
    password_hash TEXT NOT NULL,
    phone TEXT,
    gender TEXT, age INTEGER, state TEXT, district TEXT, education TEXT,
    occupation TEXT, annual_income INTEGER, caste TEXT,
    farmer TEXT DEFAULT 'No', student TEXT DEFAULT 'No', disabled TEXT DEFAULT 'No',
    senior_citizen TEXT DEFAULT 'No', bpl TEXT DEFAULT 'No', widow TEXT DEFAULT 'No',
    land_holding_acres REAL DEFAULT 0,
    is_admin INTEGER DEFAULT 0,
    preferred_language TEXT DEFAULT 'English',
    theme_preference TEXT DEFAULT 'light', text_size TEXT DEFAULT 'normal', reduced_motion INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS schemes (
    scheme_id TEXT PRIMARY KEY,
    scheme_name TEXT NOT NULL, category TEXT, description TEXT, benefits TEXT,
    eligibility TEXT, documents_required TEXT, application_process TEXT, official_link TEXT, application_link TEXT,
    state TEXT DEFAULT 'All India', status TEXT DEFAULT 'Active', source_url TEXT,
    source_name TEXT, government_department TEXT, last_checked TEXT, last_updated TEXT,
    last_verified TEXT, source_hash TEXT,
    verification_status TEXT DEFAULT 'PENDING_REVIEW',
    min_age REAL, max_age REAL, income_limit REAL, caste_requirement TEXT,
    farmer_required INTEGER DEFAULT 0, bpl_required INTEGER DEFAULT 0,
    land_limit_required INTEGER DEFAULT 0, land_limit_acres REAL,
    disability_required INTEGER DEFAULT 0, student_required INTEGER DEFAULT 0, widow_required INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    scheme_id TEXT NOT NULL REFERENCES schemes(scheme_id),
    application_date TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'Draft', application_number TEXT, remarks TEXT,
    created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS saved_schemes (
    saved_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    scheme_id TEXT NOT NULL REFERENCES schemes(scheme_id),
    saved_date TEXT DEFAULT (datetime('now')), UNIQUE(user_id, scheme_id)
);
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL, message TEXT NOT NULL, status TEXT DEFAULT 'Unread',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS eligibility_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    scheme_id TEXT NOT NULL REFERENCES schemes(scheme_id),
    is_eligible INTEGER NOT NULL, explanation TEXT, evaluated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, scheme_id)
);
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    scheme_id TEXT NOT NULL REFERENCES schemes(scheme_id), relevance_score REAL, rank INTEGER,
    generated_at TEXT DEFAULT (datetime('now')), UNIQUE(user_id, scheme_id)
);
CREATE TABLE IF NOT EXISTS scheme_updates (
    update_id INTEGER PRIMARY KEY AUTOINCREMENT, scheme_id TEXT, source TEXT,
    change_type TEXT, old_value TEXT, new_value TEXT, candidate_payload TEXT,
    checked_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS automation_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT, job_name TEXT, status TEXT, details TEXT,
    run_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS rpa_jobs (
    rpa_job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES applications(application_id) ON DELETE CASCADE,
    status TEXT DEFAULT 'Queued', application_number TEXT, remarks TEXT,
    started_at TEXT, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    language TEXT DEFAULT 'English', created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    sender TEXT NOT NULL, message TEXT NOT NULL, language TEXT, intent TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_number TEXT NOT NULL UNIQUE, user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category TEXT NOT NULL, subject TEXT NOT NULL, description TEXT NOT NULL, language TEXT DEFAULT 'English',
    status TEXT DEFAULT 'OPEN', priority TEXT DEFAULT 'Normal', assigned_admin INTEGER REFERENCES users(user_id),
    resolution TEXT, related_application_id INTEGER REFERENCES applications(application_id),
    created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS complaint_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL, sender_id INTEGER, message TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5), comment TEXT, language TEXT DEFAULT 'English',
    voice_transcribed INTEGER DEFAULT 0, feature TEXT, page TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS admin_actions (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER NOT NULL REFERENCES users(user_id),
    action_type TEXT NOT NULL, target_type TEXT, target_id TEXT, details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key TEXT PRIMARY KEY, setting_value TEXT, updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS document_records (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    document_type TEXT NOT NULL, source TEXT DEFAULT 'DigiLocker', availability_status TEXT DEFAULT 'UNKNOWN',
    verified_at TEXT, metadata_json TEXT, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, document_type)
);

CREATE TABLE IF NOT EXISTS scheme_document_requirements (
    requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_id TEXT NOT NULL REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    description TEXT,
    source_url TEXT NOT NULL,
    source_name TEXT,
    verification_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    source_checked_at TEXT DEFAULT (datetime('now')),
    UNIQUE(scheme_id, document_type)
);

CREATE TABLE IF NOT EXISTS digilocker_connections (
    connection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'NOT_CONNECTED',
    subject_hash TEXT,
    last_checked TEXT,
    expires_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS application_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT, application_id INTEGER NOT NULL REFERENCES applications(application_id) ON DELETE CASCADE,
    status TEXT NOT NULL, remarks TEXT, created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes(category);
CREATE INDEX IF NOT EXISTS idx_schemes_status ON schemes(status);
CREATE INDEX IF NOT EXISTS idx_schemes_verification ON schemes(verification_status);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_user ON saved_schemes(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_eligibility_user ON eligibility_results(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_user ON recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_complaints_user ON complaints(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_application_events ON application_events(application_id);
