# PATH: GovScheme/routes/chatbot_routes.py
from flask import Blueprint, request, jsonify, session, render_template, url_for
from models.user_model import get_user_by_id
from models.db import execute, query
from ai.chatbot import handle_message
from ai.language_service import get_supported_text_languages, voice_support_for, PROVIDER_VOICE_LANGUAGES, detect_language
from ai.speech_to_text import get_stt_service, SpeechToTextError
from ai.text_to_speech import get_tts_service, TextToSpeechError
from config import Config

chatbot_bp=Blueprint("chatbot",__name__)

@chatbot_bp.route("/chatbot")
def chatbot_widget(): return render_template("chatbot/chatbot.html", languages=get_supported_text_languages())

def _get_or_create_session(user_id,language):
    if user_id:
        rows=query("SELECT session_id FROM chat_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 1",(user_id,))
        if rows:return rows[0]["session_id"]
    return execute("INSERT INTO chat_sessions(user_id,language) VALUES(?,?)",(user_id,language))


def _resolve_action(action):
    if not action:return None
    allowed={"dashboard.dashboard_home","scheme.schemes_list","scheme.saved_schemes_list","application.applications_list","profile.profile_view","notification.notifications_list","complaint.complaints_list","feedback.feedback_form","settings.settings_page","dashboard.help_center","scheme.scheme_updates","documents.document_readiness"}
    endpoint=action.get("endpoint")
    if endpoint not in allowed:return None
    try:
        if action.get("scheme_id"):
            kwargs={"scheme_id":action["scheme_id"]}
        elif action.get("application_id"):
            kwargs={"application_id":action["application_id"]}
        elif action.get("complaint_id"):
            kwargs={"complaint_id":action["complaint_id"]}
        else:
            kwargs={}
        return {"type":action["type"],"url":url_for(endpoint,**kwargs),"label":action.get("label")}
    except Exception:return None

@chatbot_bp.post("/api/chat/message")
def chat_message():
    data=request.get_json(silent=True) or {}; message=(data.get("message") or "").strip(); language=data.get("language") or "English"
    if not message:return jsonify(success=False,error="Empty message"),400
    if language not in get_supported_text_languages():language="English"
    user_id=session.get("user_id"); user=get_user_by_id(user_id) if user_id else None
    sid=_get_or_create_session(user_id,language)
    execute("INSERT INTO chat_messages(session_id,sender,message,language) VALUES(?,?,?,?)",(sid,"user",message,language))
    detected, confidence = detect_language(message, language)
    if language == "English" and detected != "English":
        if confidence >= 0.75:
            language = detected
        else:
            reply = "I am not confident about the language of this message. Please choose your language from the selector."
            execute("INSERT INTO chat_messages(session_id,sender,message,language,intent) VALUES(?,?,?,?,?)", (sid,"bot",reply,language,"LANGUAGE_CONFIRMATION"))
            return jsonify(success=True,reply=reply,intent="LANGUAGE_CONFIRMATION",language=language,action=None,language_confidence=confidence)
    result=handle_message(message,user,language)
    action=_resolve_action(result.get("action"))
    if result.get("action",{}).get("type")=="search_schemes":
        action={"type":"search_schemes","url":url_for("scheme.schemes_list",q=result["action"].get("keyword","")),"label":"Open search results"}
    execute("INSERT INTO chat_messages(session_id,sender,message,language,intent) VALUES(?,?,?,?,?)",(sid,"bot",result["reply"],language,result["intent"]))
    return jsonify(success=True,reply=result["reply"],intent=result["intent"],language=language,action=action,language_confidence=confidence)

@chatbot_bp.get("/api/chat/languages")
def chat_languages():
    return jsonify(
        text_languages=get_supported_text_languages(),
        voice_provider=Config.STT_PROVIDER or None,
        voice_supported={l:voice_support_for(l,Config.STT_PROVIDER) for l in get_supported_text_languages()},
        tts_supported={l:get_tts_service().is_available_for(l) for l in get_supported_text_languages()},
        voice_locale_codes=PROVIDER_VOICE_LANGUAGES.get(Config.STT_PROVIDER,{}),
    )

@chatbot_bp.post("/api/chat/voice-input")
@chatbot_bp.post("/api/chat/voice")
def voice_input():
    language=request.form.get("language","English"); audio=request.files.get("audio")
    if not audio:return jsonify(success=False,error="No audio provided"),400
    stt=get_stt_service()
    if not stt.is_available():return jsonify(success=False,error="Voice input is not configured; use text chat."),503
    try:return jsonify(success=True,text=stt.transcribe(audio.read(),language))
    except SpeechToTextError as exc:return jsonify(success=False,error="transcription_failed",message=str(exc)),502

@chatbot_bp.post("/api/chat/voice-output")
def voice_output():
    data=request.get_json(silent=True) or {}; text=data.get("text",""); language=data.get("language","English")
    tts=get_tts_service()
    if not tts.is_available_for(language):return jsonify(success=False,error="Voice output unavailable for this language."),503
    try:return tts.synthesize(text,language),200,{"Content-Type":"audio/mpeg"}
    except TextToSpeechError as exc:return jsonify(success=False,error=str(exc)),502
