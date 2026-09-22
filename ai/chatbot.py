# PATH: GovScheme/ai/chatbot.py
"""Grounded, profile-aware chatbot and safe action planner."""
import re
from ai.intent_classifier import classify_intent
from ai.recommendation_model import get_recommendations, get_all_eligibility_results
from ai.response_generator import render_recommendations, render_eligibility, render_scheme_details, not_found_message
from ai.language_service import match_navigation_command, translate_keywords_to_english
from models.scheme_model import get_all_schemes
from services.semantic_search import semantic_search

NAVIGATION_LABELS={
    "dashboard.dashboard_home":"Dashboard","scheme.schemes_list":"Schemes","application.applications_list":"Applications",
    "scheme.saved_schemes_list":"Saved Schemes","profile.profile_view":"Profile","notification.notifications_list":"Notifications",
    "complaint.complaints_list":"Complaints","feedback.feedback_form":"Feedback","settings.settings_page":"Settings",
    "dashboard.help_center":"Help & Support",
    "documents.document_readiness":"Document Readiness",
}
LOCAL_LABELS={
 "Hindi":{"Dashboard":"डैशबोर्ड","Schemes":"योजनाएं","Applications":"आवेदन","Saved Schemes":"सहेजी गई योजनाएं","Profile":"प्रोफ़ाइल","Notifications":"सूचनाएं","Complaints":"शिकायतें","Feedback":"प्रतिक्रिया","Settings":"सेटिंग्स","Help & Support":"सहायता और समर्थन"},
 "Tamil":{"Dashboard":"டாஷ்போர்டு","Schemes":"திட்டங்கள்","Applications":"விண்ணப்பங்கள்","Saved Schemes":"சேமித்த திட்டங்கள்","Profile":"சுயவிவரம்","Notifications":"அறிவிப்புகள்","Complaints":"புகார்கள்","Feedback":"கருத்து","Settings":"அமைப்புகள்","Help & Support":"உதவி"},
 "Telugu":{"Dashboard":"డాష్‌బోర్డ్","Schemes":"పథకాలు","Applications":"దరఖాస్తులు","Saved Schemes":"సేవ్ చేసిన పథకాలు","Profile":"ప్రొఫైల్","Notifications":"నోటిఫికేషన్లు","Complaints":"ఫిర్యాదులు","Feedback":"అభిప్రాయం","Settings":"సెట్టింగ్‌లు","Help & Support":"సహాయం"},
 "Bengali":{"Dashboard":"ড্যাশবোর্ড","Schemes":"প্রকল্প","Applications":"আবেদন","Saved Schemes":"সংরক্ষিত প্রকল্প","Profile":"প্রোফাইল","Notifications":"বিজ্ঞপ্তি","Complaints":"অভিযোগ","Feedback":"প্রতিক্রিয়া","Settings":"সেটিংস","Help & Support":"সহায়তা"}
}
CONF={"English":"Opening {page} for you.","Hindi":"आपके लिए {page} खोल रहा हूँ।","Bengali":"আপনার জন্য {page} খুলছি।","Tamil":"உங்களுக்காக {page} திறக்கிறேன்.","Telugu":"మీ కోసం {page} తెరుస్తున్నాను.","Marathi":"तुमच्यासाठी {page} उघडत आहे.","Gujarati":"તમારા માટે {page} ખોલી રહ્યો છું.","Kannada":"ನಿಮಗಾಗಿ {page} ತೆರೆಯುತ್ತಿದ್ದೇನೆ.","Malayalam":"നിങ്ങൾക്കായി {page} തുറക്കുന്നു.","Punjabi":"ਤੁਹਾਡੇ ਲਈ {page} ਖੋਲ੍ਹ ਰਿਹਾ ਹਾਂ।","Odia":"ଆପଣଙ୍କ ପାଇଁ {page} ଖୋଲୁଛି।","Assamese":"আপোনাৰ বাবে {page} খুলি আছোঁ।"}


def _find_scheme(message, language="English"):
    q=message.lower()
    for s in get_all_schemes():
        name=s["scheme_name"].lower()
        if name in q or any(w in q for w in name.split() if len(w)>4): return s
    hits=semantic_search(message, language=language, limit=1)
    return hits[0] if hits and hits[0].get("search_score",0)>=20 else None


def handle_message(message, user_row=None, language="English"):
    message=(message or "").strip(); language=language if language else "English"
    nav=match_navigation_command(message, language)
    if nav:
        return {"reply":CONF.get(language,CONF["English"]).format(page=LOCAL_LABELS.get(language,{}).get(NAVIGATION_LABELS.get(nav,nav), NAVIGATION_LABELS.get(nav,nav))),"intent":"NAVIGATE","action":{"type":"navigate","endpoint":nav,"label":NAVIGATION_LABELS.get(nav,nav)}}

    intent=classify_intent(message)
    translated_message = translate_keywords_to_english(message, language) if language != "English" else ""
    if translated_message:
        translated_intent = classify_intent(translated_message)
        # Prefer the translated semantic intent when the native-script input
        # was not directly recognised. This keeps navigation, application
        # process and scheme-category commands useful in local languages.
        if intent == "GENERAL_SCHEME_QUERY" or translated_intent != "GENERAL_SCHEME_QUERY":
            intent = translated_intent

    if intent in {"RECOMMENDATIONS","WHY_RECOMMENDED"}:
        if not user_row: return {"reply":"Please log in so I can use your profile.","intent":intent}
        return {"reply":render_recommendations(get_recommendations(user_row,5),language),"intent":intent,"action":{"type":"navigate","endpoint":"scheme.schemes_list","label":"Recommended schemes"}}

    if intent=="ELIGIBILITY":
        if not user_row: return {"reply":"Please log in so I can check your profile.","intent":intent}
        scheme=_find_scheme(message,language)
        if not scheme: return {"reply":"Please mention the scheme name you want me to check.","intent":intent}
        match=next((r for s,r in get_all_eligibility_results(user_row) if s["scheme_id"]==scheme["scheme_id"]),None)
        return {"reply":render_eligibility(scheme["scheme_name"],match,language),"intent":intent,"action":{"type":"navigate","endpoint":"scheme.scheme_details","scheme_id":scheme["scheme_id"],"label":"Open scheme details"}}

    if intent == "DOCUMENT_READINESS":
        if not user_row:
            return {"reply":"Please log in so I can check your document readiness.","intent":intent}
        scheme = _find_scheme(message, language)
        if scheme:
            from services.document_readiness import get_readiness
            readiness = get_readiness(user_row, scheme["scheme_id"])
            if readiness["percentage"] is None:
                reply = {
                    "English": f"I cannot calculate document readiness for {scheme['scheme_name']} yet because its required documents have not been verified from an official source.",
                    "Hindi": f"{scheme['scheme_name']} के दस्तावेज़ों की आवश्यकताएं अभी आधिकारिक स्रोत से सत्यापित नहीं हैं, इसलिए मैं तैयारी प्रतिशत की गणना नहीं कर सकता।",
                    "Bengali": f"{scheme['scheme_name']} প্রকল্পের নথির প্রয়োজনীয়তা এখনও সরকারি উৎস থেকে যাচাই করা হয়নি, তাই প্রস্তুতির শতাংশ গণনা করা যাচ্ছে না।",
                }.get(language, f"Document readiness for {scheme['scheme_name']} is not available until its requirements are verified from an official source.")
            else:
                missing = [i["document_type"] for i in readiness["items"] if i["status"] == "MISSING"]
                available = [i["document_type"] for i in readiness["items"] if i["status"] in {"AVAILABLE","VERIFIED"}]
                reply = f"Document readiness for {scheme['scheme_name']}: {readiness['percentage']}%. Available: {', '.join(available) or 'none'}. Missing: {', '.join(missing) or 'none'}."
            return {"reply":reply,"intent":intent,"action":{"type":"navigate","endpoint":"documents.document_readiness","label":"Open document readiness","scheme_id":scheme["scheme_id"]}}
        return {"reply":"I can check document readiness for a selected scheme using verified requirements and authorized DigiLocker metadata.","intent":intent,"action":{"type":"navigate","endpoint":"documents.document_readiness","label":"Open document readiness"}}

    if intent in {"SCHEME_DETAILS","BENEFITS","DOCUMENTS"}:
        scheme=_find_scheme(message,language)
        return {"reply":render_scheme_details(scheme,language) if scheme else not_found_message(language),"intent":intent,
                "action":{"type":"navigate","endpoint":"scheme.scheme_details","scheme_id":scheme["scheme_id"],"label":"Open scheme"} if scheme else None}

    if intent=="APPLICATION_STATUS":
        if not user_row: return {"reply":"Please log in to see your applications.","intent":intent}
        from models.application_model import get_applications_for_user
        apps=get_applications_for_user(user_row["user_id"])
        if not apps: reply="You do not have any applications yet."
        else: reply="\n".join(f"{a['scheme_name']}: {a['status']} — {a.get('application_number') or 'No reference yet'}" for a in apps[:5])
        return {"reply":reply,"intent":intent,"action":{"type":"navigate","endpoint":"application.applications_list","label":"Open applications"}}

    if intent=="COMPLAINT_STATUS":
        if not user_row: return {"reply":"Please log in so I can check your customer-care history.","intent":intent}
        from models.complaint_model import get_complaints_for_user, get_complaint_messages
        complaints=get_complaints_for_user(user_row["user_id"])
        if not complaints:
            return {"reply":"You do not have any customer-care complaints yet.","intent":intent,"action":{"type":"navigate","endpoint":"complaint.complaints_list","label":"Open complaints"}}
        c=complaints[0]; msgs=get_complaint_messages(c["complaint_id"]); admin_msgs=[m for m in msgs if m["sender_type"]=="admin"]
        reply=f"Complaint {c['complaint_number']} is {c['status']}."
        if admin_msgs: reply += f" Latest support response: {admin_msgs[-1]['message']}"
        else: reply += " There is no admin response yet."
        return {"reply":reply,"intent":intent,"action":{"type":"navigate","endpoint":"complaint.complaint_details","complaint_id":c["complaint_id"],"label":"Open complaint"}}

    if intent=="COMPLAINT":
        if user_row:
            from models.application_model import get_applications_for_user
            apps=get_applications_for_user(user_row["user_id"])
            if apps and any(token in message.lower() for token in ["application", "apply", "stuck", "pending", "status"]):
                a=apps[0]
                status=str(a.get("status") or "Unknown")
                if status in {"Queued", "Running", "Submitted", "Pending", "Under Review", "Draft"}:
                    reply=f"I checked your latest application record for {a['scheme_name']}. Its current recorded status is {status}. The available system information does not show a failure or final decision. You can open the application timeline for the latest recorded event."
                elif status in {"Needs Manual Action", "Failed"}:
                    reply=f"I checked your latest application record for {a['scheme_name']}. Its recorded status is {status}. The system has flagged it for manual attention rather than claiming a successful submission. Please review the remarks and official portal."
                else:
                    reply=f"I checked your latest application record for {a['scheme_name']}. Its current recorded status is {status}. I can only explain the status stored by SmartGov AI and cannot infer a government decision."
                return {"reply":reply,"intent":"AI_CUSTOMER_CARE","action":{"type":"navigate","endpoint":"application.application_details","application_id":a["application_id"],"label":"Open application timeline"}}
        return {"reply":"I can check available application information, but I cannot invent a resolution. Would you like me to raise this with customer support?","intent":intent,"action":{"type":"offer_complaint","draft_description":message}}

    if intent in {"SAVED_SCHEMES","NEW_SCHEMES"}:
        endpoint = "scheme.saved_schemes_list" if intent == "SAVED_SCHEMES" else "scheme.scheme_updates"
        label = "Saved Schemes" if intent == "SAVED_SCHEMES" else "New & Updated Schemes"
        return {"reply":"I can open that for you.","intent":intent,"action":{"type":"navigate","endpoint":endpoint,"label":label}}

    if intent == "APPLICATION_PROCESS":
        scheme = _find_scheme(message, language)
        if scheme:
            return {
                "reply": (f"For {scheme['scheme_name']}, first review the configured eligibility criteria, "
                          "prepare the documents shown on the scheme page, then use the official government portal "
                          "or the clearly labelled SmartGov AI demo application path."),
                "intent": intent,
                "action": {"type":"navigate", "endpoint":"scheme.scheme_details",
                           "scheme_id":scheme["scheme_id"], "label":"Open scheme details"}
            }
        return {"reply":"Open the Schemes page, choose a scheme, review its eligibility and documents, and then use its official application portal when available.",
                "intent":intent,"action":{"type":"navigate","endpoint":"scheme.schemes_list","label":"Open schemes"}}

    if intent in {"FARMER_SCHEMES","STUDENT_SCHEMES","SENIOR_CITIZEN_SCHEMES","DISABILITY_SCHEMES","WOMEN_SCHEMES","HOUSING","HEALTH","EDUCATION","STATE_SEARCH","CATEGORY_SEARCH","SCHEME_SEARCH"}:
        translated = translate_keywords_to_english(message, language)
        query_text = translated or message
        results = semantic_search(query_text, language=language, user_id=user_row.get("user_id") if user_row else None, limit=8)
        if results:
            lines=["Here are the closest scheme matches:"]+[f"{i}. {s['scheme_name']} — {s.get('category') or 'General'} (search relevance {s['search_score']}%)" for i,s in enumerate(results,1)]
            return {"reply":"\n".join(lines),"intent":"SCHEME_SEARCH","action":{"type":"search_schemes","keyword":query_text}}

    translated=translate_keywords_to_english(message,language)
    results=semantic_search(message if not translated else translated, language=language, user_id=user_row.get("user_id") if user_row else None, limit=8)
    if results:
        lines=["Here are the closest scheme matches:"]+[f"{i}. {s['scheme_name']} — {s.get('category') or 'General'} (search relevance {s['search_score']}%)" for i,s in enumerate(results,1)]
        return {"reply":"\n".join(lines),"intent":"SCHEME_SEARCH","action":{"type":"search_schemes","keyword":message}}
    return {"reply":"I could not find a verified scheme match in the available catalogue. Try a benefit, occupation, problem or scheme name.","intent":"GENERAL_SCHEME_QUERY"}
