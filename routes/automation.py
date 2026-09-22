# PATH: GovScheme/routes/automation.py
from routes.auth_routes import admin_required
from flask import Blueprint, jsonify
from automation.scheduler import run_scheme_update_check
automation_bp=Blueprint("automation",__name__)
@automation_bp.post("/admin/automation/check")
@admin_required
def check(): return jsonify(success=True, result=run_scheme_update_check())
