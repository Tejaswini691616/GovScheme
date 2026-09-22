# PATH: GovScheme/routes/eligibility.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from routes.auth_routes import login_required
from models.user_model import get_user_by_id, update_user_profile, citizen_dict_for_engine
from models.scheme_model import get_all_schemes
from models.db import execute
from ai.eligibility_engine import evaluate_all_schemes

eligibility_bp=Blueprint("eligibility",__name__)

@eligibility_bp.route("/eligibility",methods=["GET","POST"])
@login_required
def eligibility():
    user=get_user_by_id(session["user_id"])
    if request.method=="GET": return render_template("eligibility/assessment.html",user=user)
    f=request.form
    def num(name, cast=float):
        v=f.get(name); return cast(v) if v not in (None,"") else None
    updates={
      "gender":f.get("gender"),"dob":f.get("dob"),"age":num("age",int),"marital_status":f.get("marital_status"),
      "state":f.get("state"),"district":f.get("district"),"rural_urban":f.get("rural_urban"),"pin_code":f.get("pin_code"),
      "family_size":num("family_size",int),"dependents":num("dependents",int),"education":f.get("education"),"occupation":f.get("occupation"),
      "employment_status":f.get("employment_status"),"annual_income":num("annual_family_income",float),"caste":f.get("caste"),
      "minority":f.get("minority"),"farmer":f.get("farmer","No"),"land_holding_acres":num("land_holding_acres"),"bpl":f.get("bpl","No"),
      "disabled":f.get("disability","No"),"disability_percentage":num("disability_percentage"),"health_insurance":f.get("health_insurance"),
      "student":f.get("student","No"),"senior_citizen":f.get("senior_citizen","No"),"widow":f.get("widow","No"),
      "aadhaar":f.get("aadhaar"),"bank_account":f.get("bank_account"),"ration_card":f.get("ration_card"),"existing_benefits":f.get("existing_benefits")}
    update_user_profile(user["user_id"],updates)
    user=get_user_by_id(user["user_id"]); citizen=citizen_dict_for_engine(user)
    results=evaluate_all_schemes(citizen,get_all_schemes())
    for result in results:
        execute("""INSERT INTO eligibility_results(user_id,scheme_id,is_eligible,explanation,evaluated_at) VALUES(?,?,?,?,datetime('now'))
                   ON CONFLICT(user_id,scheme_id) DO UPDATE SET is_eligible=excluded.is_eligible, explanation=excluded.explanation, evaluated_at=datetime('now')""",
                (user["user_id"],result.scheme_id,int(result.is_eligible),result.explanation_text()))
    flash("Eligibility checked using the configured prototype rules.","success")
    paired=list(zip(get_all_schemes(),results))
    return render_template("eligibility/results.html", user=user, results=paired, eligible_count=sum(1 for _, r in paired if r.is_eligible), ineligible_count=sum(1 for _, r in paired if not r.is_eligible))
