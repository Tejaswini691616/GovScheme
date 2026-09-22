# PATH: GovScheme/ai/text_to_speech.py
import requests
from config import Config
from ai.language_service import PROVIDER_VOICE_LANGUAGES

class TextToSpeechError(Exception): pass
class TextToSpeechService:
    def is_available_for(self, language): raise NotImplementedError
    def synthesize(self, text, language): raise NotImplementedError
class UnavailableTTSService(TextToSpeechService):
    def is_available_for(self, language): return False
    def synthesize(self, text, language): raise TextToSpeechError("Text-to-speech is not configured.")
class BrowserWebSpeechTTSService(TextToSpeechService):
    def is_available_for(self, language):
        return language in PROVIDER_VOICE_LANGUAGES.get("browser_web_speech", {})
    def synthesize(self, text, language): raise TextToSpeechError("Browser speech synthesis runs in the browser.")

AZURE_VOICES={
    "English":"en-IN-NeerjaNeural","Hindi":"hi-IN-SwaraNeural","Bengali":"bn-IN-TanishaaNeural",
    "Tamil":"ta-IN-PallaviNeural","Telugu":"te-IN-ShrutiNeural","Marathi":"mr-IN-AarohiNeural",
    "Gujarati":"gu-IN-DhwaniNeural","Kannada":"kn-IN-SapnaNeural","Malayalam":"ml-IN-SobhanaNeural",
    "Punjabi":"pa-IN-VaaniNeural","Odia":"or-IN-SubhasiniNeural","Assamese":"as-IN-YashicaNeural",
}

class AzureTTSService(TextToSpeechService):
    def is_available_for(self, language): return bool(Config.TTS_API_KEY and Config.TTS_REGION and language in AZURE_VOICES)
    def synthesize(self, text, language):
        if not self.is_available_for(language): raise TextToSpeechError(f"Azure TTS is not configured for {language}.")
        voice=AZURE_VOICES[language]; locale=PROVIDER_VOICE_LANGUAGES["azure_speech"][language]
        body=f'''<speak version="1.0" xml:lang="{locale}" xmlns="http://www.w3.org/2001/10/synthesis"><voice name="{voice}">{text}</voice></speak>'''
        url=f"https://{Config.TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
        try:
            r=requests.post(url,headers={"Ocp-Apim-Subscription-Key":Config.TTS_API_KEY,"Content-Type":"application/ssml+xml","X-Microsoft-OutputFormat":"audio-24khz-48kbitrate-mono-mp3"},data=body.encode("utf-8"),timeout=30)
            r.raise_for_status(); return r.content
        except Exception as exc: raise TextToSpeechError(f"Azure TTS request failed: {exc}") from exc

def get_tts_service():
    if Config.TTS_PROVIDER == "browser_web_speech": return BrowserWebSpeechTTSService()
    if Config.TTS_PROVIDER in {"azure", "azure_speech"}: return AzureTTSService()
    return UnavailableTTSService()
