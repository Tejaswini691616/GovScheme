# PATH: GovScheme/models/application_model.py
from models.db import query, query_one, execute

VALID_STATUSES=["Draft","Queued","Running","Submitted","Under Review","Approved","Rejected","Completed","Failed","Needs Manual Action"]

def create_application(user_id, scheme_id):
    app_id=execute("INSERT INTO applications(user_id,scheme_id,status) VALUES(?,?,?)",(user_id,scheme_id,"Draft"))
    add_application_event(app_id,"Draft","Application created")
    return app_id

def add_application_event(application_id,status,remarks=None):
    execute("INSERT INTO application_events(application_id,status,remarks) VALUES(?,?,?)",(application_id,status,remarks))

def get_application(application_id):
    return query_one("SELECT a.*,s.scheme_name,s.official_link,s.application_link,s.source_name,s.last_verified,s.verification_status FROM applications a JOIN schemes s ON a.scheme_id=s.scheme_id WHERE a.application_id=?",(application_id,))

def get_application_events(application_id):
    return query("SELECT * FROM application_events WHERE application_id=? ORDER BY created_at ASC",(application_id,))

def get_applications_for_user(user_id):
    return query("SELECT a.*,s.scheme_name,s.official_link,s.application_link FROM applications a JOIN schemes s ON a.scheme_id=s.scheme_id WHERE a.user_id=? ORDER BY a.created_at DESC",(user_id,))

def update_application_status(application_id,status,application_number=None,remarks=None):
    if status not in VALID_STATUSES: status="Needs Manual Action"
    execute("UPDATE applications SET status=?,application_number=COALESCE(?,application_number),remarks=COALESCE(?,remarks),updated_at=datetime('now') WHERE application_id=?",(status,application_number,remarks,application_id))
    add_application_event(application_id,status,remarks)
