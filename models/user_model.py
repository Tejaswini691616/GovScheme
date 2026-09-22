# PATH: GovScheme/models/user_model.py
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import query, query_one, execute

PROFILE_FIELDS=["full_name","phone","gender","age","dob","marital_status","state","district","rural_urban","pin_code","family_size","dependents","education","occupation","employment_status","annual_income","caste","minority","farmer","land_holding_acres","bpl","disabled","disability_percentage","health_insurance","student","senior_citizen","widow","aadhaar","bank_account","ration_card","existing_benefits","preferred_language"]

def create_user(data):
    fields=[f for f in PROFILE_FIELDS if f in data and f not in {"full_name","email"}]
    columns=["full_name","email","password_hash"]+fields
    values=[data.get("full_name"),data.get("email"),generate_password_hash(data["password"])] + [data.get(f) for f in fields]
    placeholders=",".join("?" for _ in columns)
    return execute(f"INSERT INTO users({','.join(columns)}) VALUES({placeholders})",tuple(values))

def get_user_by_email(email): return query_one("SELECT * FROM users WHERE lower(email)=?",((email or "").strip().lower(),))
def get_user_by_id(user_id): return query_one("SELECT * FROM users WHERE user_id=?",(user_id,))
def verify_password(user_row,password): return bool(user_row and check_password_hash(user_row["password_hash"],password or ""))

def update_user_profile(user_id,data):
    fields=[f for f in PROFILE_FIELDS if f in data]
    if not fields:return
    execute(f"UPDATE users SET {','.join(f+'=?' for f in fields)} WHERE user_id=?",tuple(data[f] for f in fields)+(user_id,))

def change_password(user_id,new_password): execute("UPDATE users SET password_hash=? WHERE user_id=?",(generate_password_hash(new_password),user_id))
def change_email(user_id,new_email): execute("UPDATE users SET email=? WHERE user_id=?",(new_email.strip().lower(),user_id))
def change_phone(user_id,new_phone): execute("UPDATE users SET phone=? WHERE user_id=?",(new_phone.strip(),user_id))

def citizen_dict_for_engine(user):
    return {"age":user.get("age"),"annual_family_income":user.get("annual_income"),"annual_income":user.get("annual_income"),"caste":user.get("caste"),"farmer":user.get("farmer"),"bpl":user.get("bpl"),"disability":user.get("disabled"),"student":user.get("student"),"widow":user.get("widow"),"land_holding_acres":user.get("land_holding_acres"),"gender":user.get("gender"),"state":user.get("state"),"district":user.get("district"),"rural_urban":user.get("rural_urban"),"education":user.get("education"),"occupation":user.get("occupation"),"employment_status":user.get("employment_status"),"family_size":user.get("family_size"),"dependents":user.get("dependents"),"minority":user.get("minority"),"disability_percentage":user.get("disability_percentage"),"senior_citizen":user.get("senior_citizen")}
