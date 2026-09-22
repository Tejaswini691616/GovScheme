# PATH: GovScheme/automation/logger.py
from models.db import execute


def log_event(job_name, status, details=""):
    return execute("INSERT INTO automation_logs(job_name,status,details) VALUES (?,?,?)",
                   (job_name, status, str(details)))
