# PATH: GovScheme/routes/home.py
from flask import Blueprint, redirect, url_for
home_bp=Blueprint("home",__name__)
@home_bp.get("/home")
def home(): return redirect(url_for("auth.login"))
