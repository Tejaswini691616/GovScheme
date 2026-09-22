# PATH: GovScheme/ai/speech_to_text.py
import requests
from config import Config
from ai.language_service import PROVIDER_VOICE_LANGUAGES

class SpeechToTextError(Exception): pass
class SpeechToTextService:
    def is_available(self): raise NotImplementedError
    def transcribe(self, audio_bytes, language): raise NotImplementedError

class UnavailableSTTService(SpeechToTextService):
    def is_available(self): return False
    def transcribe(self, audio_bytes, language): raise SpeechToTextError("Speech-to-text is not configured.")

class BrowserWebSpeechSTTService(SpeechToTextService):
    def is_available(self): return True
    def transcribe(self, audio_bytes, language): raise SpeechToTextError("Browser speech recognition must transcribe in the browser.")

class AzureSTTService(SpeechToTextService):
    def is_available(self): return bool(Config.STT_API_KEY and Config.STT_REGION)
    def transcribe(self, audio_bytes, language):
        if not self.is_available(): raise SpeechToTextError("Azure Speech credentials are not configured.")
        locale=PROVIDER_VOICE_LANGUAGES["azure_speech"].get(language)
        if not locale: raise SpeechToTextError(f"Azure STT language is not configured for {language}.")
        url=f"https://{Config.STT_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
        try:
            r=requests.post(url,params={"language":locale,"format":"simple"},headers={"Ocp-Apim-Subscription-Key":Config.STT_API_KEY,"Content-Type":"audio/wav; codecs=audio/pcm; samplerate=16000"},data=audio_bytes,timeout=30)
            r.raise_for_status(); data=r.json(); text=data.get("DisplayText") or data.get("NBest", [{}])[0].get("Display")
            if not text: raise SpeechToTextError("No speech was recognized.")
            return text
        except SpeechToTextError: raise
        except Exception as exc: raise SpeechToTextError(f"Azure STT request failed: {exc}") from exc

def get_stt_service():
    if Config.STT_PROVIDER == "browser_web_speech": return BrowserWebSpeechSTTService()
    if Config.STT_PROVIDER in {"azure", "azure_speech"}: return AzureSTTService()
    return UnavailableSTTService()
