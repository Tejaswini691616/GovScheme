# PATH: GovScheme/ai/language_service.py
"""
Language configuration for the chatbot.

IMPORTANT (spec section 28): we do NOT claim STT/TTS support for a
language unless a configured provider actually supports it. Text chat
uses hand-written response templates per language (see
ai/response_generator.py), which is honest and always works offline.
Voice (STT/TTS) support is reported separately via voice_support_for()
and depends entirely on what STT_PROVIDER/TTS_PROVIDER is configured in
.env - if none is configured, voice is disabled and the UI must say so,
while text chat keeps working in all listed languages.
"""

SUPPORTED_TEXT_LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Punjabi": "pa",
    "Odia": "or",
    "Assamese": "as",
}

# Providers and their ACTUALLY verified language codes go here. This dict is
# intentionally empty for unconfigured providers so the app never fakes
# voice support.
#
# "browser_web_speech" is the DEFAULT real provider wired into this project:
# the browser's native SpeechRecognition + SpeechSynthesis APIs (Chrome/Edge).
# It needs NO API key and NO server-side integration - ai/speech_to_text.py
# and ai/text_to_speech.py stay as documented no-op fallbacks for server-side
# use, while static/js/chatbot.js talks to the browser APIs directly for
# this provider. The codes below are the BCP-47 locales Chrome's speech
# engine actually recognizes for these languages. Odia and Assamese are
# deliberately left OUT: Chrome's speech recognition/synthesis voices do not
# reliably support them at the time of writing, so we do not claim voice
# support for them (spec section 28) - text chat still works for both.
PROVIDER_VOICE_LANGUAGES = {
    "browser_web_speech": {
        "English": "en-IN", "Hindi": "hi-IN", "Bengali": "bn-IN", "Tamil": "ta-IN",
        "Telugu": "te-IN", "Marathi": "mr-IN", "Gujarati": "gu-IN", "Kannada": "kn-IN",
        "Malayalam": "ml-IN", "Punjabi": "pa-IN",
    },
    "azure_speech": {
        "English": "en-IN", "Hindi": "hi-IN", "Bengali": "bn-IN", "Tamil": "ta-IN",
        "Telugu": "te-IN", "Marathi": "mr-IN", "Gujarati": "gu-IN", "Kannada": "kn-IN",
        "Malayalam": "ml-IN", "Punjabi": "pa-IN", "Odia": "or-IN", "Assamese": "as-IN",
    },
}


def get_supported_text_languages():
    return list(SUPPORTED_TEXT_LANGUAGES.keys())


def is_text_language_supported(language: str) -> bool:
    return language in SUPPORTED_TEXT_LANGUAGES


def voice_support_for(language: str, provider: str) -> bool:
    """Returns True only if `provider` has a verified language code for
    `language`. With no provider configured, always returns False."""
    if not provider:
        return False
    codes = PROVIDER_VOICE_LANGUAGES.get(provider, {})
    return language in codes


def detect_language_hint(text: str) -> str:
    # Bengali and Assamese share the same Unicode block. Use distinctive
    # lexical hints first, then script detection, and fall back to English.
    text = text or ""
    assamese_hints = ["মই", "মোৰ", "আপোনাৰ", "আঁচনি", "নগ'ল", "কৃষক", "অসম"]
    bengali_hints = ["আমি", "আমার", "আপনার", "প্রকল্প", "পাওয়া", "কৃষক"]
    if any(token in text for token in assamese_hints):
        return "Assamese"
    if any(token in text for token in bengali_hints):
        return "Bengali"
    ranges = {
        "Hindi": (0x0900, 0x097F), "Gujarati": (0x0A80, 0x0AFF),
        "Punjabi": (0x0A00, 0x0A7F), "Odia": (0x0B00, 0x0B7F),
        "Tamil": (0x0B80, 0x0BFF), "Telugu": (0x0C00, 0x0C7F),
        "Kannada": (0x0C80, 0x0CFF), "Malayalam": (0x0D00, 0x0D7F),
    }
    for lang, (lo, hi) in ranges.items():
        if any(lo <= ord(ch) <= hi for ch in text):
            return lang
    if any(0x0980 <= ord(ch) <= 0x09FF for ch in text):
        return "Bengali"
    return "English"


# ---------------------------------------------------------------------------
# Voice/text navigation commands (spec: "tell it in my local language and it
# navigates to that page"). Each entry maps a route NAME (used by the
# chatbot to build a URL via Flask's url_for) to phrases that should trigger
# it, per language. This is a small rule-based command glossary, not a
# general translator - it only needs to recognise a fixed, short set of
# "go to X" style phrases, which keeps it honest and reliable without an
# external LLM/translation API (spec section 42).
# ---------------------------------------------------------------------------
NAVIGATION_COMMANDS = {
    "dashboard.dashboard_home": {
        "English": ["dashboard", "home page", "go home", "main page"],
        "Hindi": ["डैशबोर्ड", "मुखपृष्ठ", "होम पेज", "घर जाओ"],
        "Bengali": ["ড্যাশবোর্ড", "হোম পেজ", "মূল পাতা"],
        "Tamil": ["டாஷ்போர்டு", "முகப்பு பக்கம்", "வீட்டு பக்கம்"],
        "Telugu": ["డాష్‌బోర్డ్", "హోమ్ పేజీ", "ముఖ్య పేజీ"],
        "Marathi": ["डॅशबोर्ड", "मुख्यपृष्ठ", "होम पेज"],
        "Gujarati": ["ડેશબોર્ડ", "હોમ પેજ", "મુખ્ય પૃષ્ઠ"],
        "Kannada": ["ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "ಮುಖಪುಟ", "ಹೋಮ್ ಪೇಜ್"],
        "Malayalam": ["ഡാഷ്ബോർഡ്", "ഹോം പേജ്", "മുഖ്യ പേജ്"],
        "Punjabi": ["ਡੈਸ਼ਬੋਰਡ", "ਹੋਮ ਪੇਜ", "ਮੁੱਖ ਪੰਨਾ"],
        "Odia": ["ଡ୍ୟାସବୋର୍ଡ", "ମୁଖ୍ୟପୃଷ୍ଠା", "ହୋମ୍ ପେଜ୍"],
        "Assamese": ["ডেশ্ববৰ্ড", "গৃহ পৃষ্ঠা", "মুখ্য পৃষ্ঠা"],
    },
    "scheme.schemes_list": {
        "English": ["schemes page", "browse schemes", "show schemes", "all schemes", "go to schemes"],
        "Hindi": ["योजनाएं", "योजना पेज", "सभी योजनाएं दिखाओ", "स्कीम पेज"],
        "Bengali": ["প্রকল্প পাতা", "সব প্রকল্প", "প্রকল্পগুলি দেখাও"],
        "Tamil": ["திட்டங்கள் பக்கம்", "எல்லா திட்டங்கள்", "திட்டங்களை காட்டு"],
        "Telugu": ["పథకాల పేజీ", "అన్ని పథకాలు", "పథకాలను చూపించు"],
        "Marathi": ["योजना पेज", "सर्व योजना", "योजना दाखवा"],
        "Gujarati": ["યોજના પેજ", "બધી યોજનાઓ", "યોજનાઓ બતાવો"],
        "Kannada": ["ಯೋಜನೆಗಳ ಪುಟ", "ಎಲ್ಲಾ ಯೋಜನೆಗಳು", "ಯೋಜನೆಗಳನ್ನು ತೋರಿಸು"],
        "Malayalam": ["പദ്ധതി പേജ്", "എല്ലാ പദ്ധതികളും", "പദ്ധതികൾ കാണിക്കുക"],
        "Punjabi": ["ਯੋਜਨਾ ਪੇਜ", "ਸਾਰੀਆਂ ਯੋਜਨਾਵਾਂ", "ਯੋਜਨਾਵਾਂ ਦਿਖਾਓ"],
        "Odia": ["ଯୋଜନା ପେଜ୍", "ସମସ୍ତ ଯୋଜନା", "ଯୋଜନା ଦେଖାନ୍ତୁ"],
        "Assamese": ["আঁচনি পৃষ্ঠা", "সকলো আঁচনি", "আঁচনি দেখুৱাওক"],
    },
    "application.applications_list": {
        "English": ["applications page", "my applications", "show applications", "application status page"],
        "Hindi": ["आवेदन पेज", "मेरे आवेदन", "आवेदन दिखाओ"],
        "Bengali": ["আবেদন পাতা", "আমার আবেদন", "আবেদন দেখাও"],
        "Tamil": ["விண்ணப்பங்கள் பக்கம்", "என் விண்ணப்பங்கள்"],
        "Telugu": ["దరఖాస్తుల పేజీ", "నా దరఖాస్తులు"],
        "Marathi": ["अर्ज पेज", "माझे अर्ज"],
        "Gujarati": ["અરજી પેજ", "મારી અરજીઓ"],
        "Kannada": ["ಅರ್ಜಿಗಳ ಪುಟ", "ನನ್ನ ಅರ್ಜಿಗಳು"],
        "Malayalam": ["അപേക്ഷ പേജ്", "എന്റെ അപേക്ഷകൾ"],
        "Punjabi": ["ਅਰਜ਼ੀ ਪੇਜ", "ਮੇਰੀਆਂ ਅਰਜ਼ੀਆਂ"],
        "Odia": ["ଆବେଦନ ପେଜ୍", "ମୋର ଆବେଦନ"],
        "Assamese": ["আবেদন পৃষ্ঠা", "মোৰ আবেদন"],
    },
    "scheme.saved_schemes_list": {
        "English": ["saved schemes", "my saved schemes", "bookmarks", "favourites"],
        "Hindi": ["सेव की गई योजनाएं", "मेरी पसंदीदा योजनाएं"],
        "Bengali": ["সংরক্ষিত প্রকল্প", "প্রিয় প্রকল্প"],
        "Tamil": ["சேமிக்கப்பட்ட திட்டங்கள்", "பிடித்தவை"],
        "Telugu": ["సేవ్ చేసిన పథకాలు", "ఇష్టమైనవి"],
        "Marathi": ["जतन केलेल्या योजना", "आवडत्या योजना"],
        "Gujarati": ["સાચવેલી યોજનાઓ", "પ્રિય યોજનાઓ"],
        "Kannada": ["ಉಳಿಸಿದ ಯೋಜನೆಗಳು", "ಮೆಚ್ಚಿನವು"],
        "Malayalam": ["സേവ് ചെയ്ത പദ്ധതികൾ", "പ്രിയപ്പെട്ടവ"],
        "Punjabi": ["ਸੇਵ ਕੀਤੀਆਂ ਯੋਜਨਾਵਾਂ", "ਮਨਪਸੰਦ"],
        "Odia": ["ସେଭ୍ ହୋଇଥିବା ଯୋଜନା", "ପସନ୍ଦିଦା"],
        "Assamese": ["ছেভ কৰা আঁচনি", "প্ৰিয়"],
    },
    "profile.profile_view": {
        "English": ["my profile", "profile page", "open profile", "show profile"],
        "Hindi": ["मेरी प्रोफ़ाइल", "प्रोफ़ाइल पेज", "प्रोफ़ाइल दिखाओ"],
        "Bengali": ["আমার প্রোফাইল", "প্রোফাইল পাতা"],
        "Tamil": ["என் சுயவிவரம்", "சுயவிவர பக்கம்"],
        "Telugu": ["నా ప్రొఫైల్", "ప్రొఫైల్ పేజీ"],
        "Marathi": ["माझी प्रोफाइल", "प्रोफाइल पेज"],
        "Gujarati": ["મારી પ્રોફાઇલ", "પ્રોફાઇલ પેજ"],
        "Kannada": ["ನನ್ನ ಪ್ರೊಫೈಲ್", "ಪ್ರೊಫೈಲ್ ಪುಟ"],
        "Malayalam": ["എന്റെ പ്രൊഫൈൽ", "പ്രൊഫൈൽ പേജ്"],
        "Punjabi": ["ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ", "ਪ੍ਰੋਫਾਈਲ ਪੇਜ"],
        "Odia": ["ମୋର ପ୍ରୋଫାଇଲ", "ପ୍ରୋଫାଇଲ ପେଜ୍"],
        "Assamese": ["মোৰ প্ৰ'ফাইল", "প্ৰ'ফাইল পৃষ্ঠা"],
    },
    "notification.notifications_list": {
        "English": ["notifications", "notifications page", "show notifications"],
        "Hindi": ["सूचनाएं", "नोटिफिकेशन", "सूचना पेज"],
        "Bengali": ["বিজ্ঞপ্তি", "নোটিফিকেশন"],
        "Tamil": ["அறிவிப்புகள்", "நோட்டிஃபிகேஷன்"],
        "Telugu": ["నోటిఫికేషన్‌లు", "ప్రకటనలు"],
        "Marathi": ["सूचना", "नोटिफिकेशन"],
        "Gujarati": ["સૂચનાઓ", "નોટિફિકેશન"],
        "Kannada": ["ಅಧಿಸೂಚನೆಗಳು", "ನೋಟಿಫಿಕೇಶನ್"],
        "Malayalam": ["അറിയിപ്പുകൾ", "നോട്ടിഫിക്കേഷൻ"],
        "Punjabi": ["ਸੂਚਨਾਵਾਂ", "ਨੋਟੀਫਿਕੇਸ਼ਨ"],
        "Odia": ["ବିଜ୍ଞପ୍ତି", "ନୋଟିଫିକେସନ୍"],
        "Assamese": ["জাননী", "নটিফিকেশ্যন"],
    },
    "complaint.complaints_list": {
        "English": ["complaints", "my complaints", "complaints page", "raise a complaint", "customer support page"],
        "Hindi": ["शिकायतें", "शिकायत पेज", "मेरी शिकायतें"],
        "Bengali": ["অভিযোগ", "অভিযোগ পাতা"],
        "Tamil": ["புகார்கள்", "புகார் பக்கம்"],
        "Telugu": ["ఫిర్యాదులు", "ఫిర్యాదు పేజీ"],
        "Marathi": ["तक्रारी", "तक्रार पेज"],
        "Gujarati": ["ફરિયાદો", "ફરિયાદ પેજ"],
        "Kannada": ["ದೂರುಗಳು", "ದೂರು ಪುಟ"],
        "Malayalam": ["പരാതികൾ", "പരാതി പേജ്"],
        "Punjabi": ["ਸ਼ਿਕਾਇਤਾਂ", "ਸ਼ਿਕਾਇਤ ਪੇਜ"],
        "Odia": ["ଅଭିଯୋଗ", "ଅଭିଯୋଗ ପେଜ୍"],
        "Assamese": ["অভিযোগ", "অভিযোগ পৃষ্ঠা"],
    },
    "feedback.feedback_form": {
        "English": ["feedback", "feedback page", "give feedback", "rate the app"],
        "Hindi": ["प्रतिक्रिया", "फीडबैक पेज"],
        "Bengali": ["প্রতিক্রিয়া", "ফিডব্যাক পাতা"],
        "Tamil": ["கருத்து", "பின்னூட்டம் பக்கம்"],
        "Telugu": ["అభిప్రాయం", "ఫీడ్‌బ్యాక్ పేజీ"],
        "Marathi": ["अभिप्राय", "फीडबॅक पेज"],
        "Gujarati": ["પ્રતિભાવ", "ફીડબેક પેજ"],
        "Kannada": ["ಪ್ರತಿಕ್ರಿಯೆ", "ಫೀಡ್‌ಬ್ಯಾಕ್ ಪುಟ"],
        "Malayalam": ["പ്രതികരണം", "ഫീഡ്‌ബാക്ക് പേജ്"],
        "Punjabi": ["ਫੀਡਬੈਕ", "ਫੀਡਬੈਕ ਪੇਜ"],
        "Odia": ["ମତାମତ", "ଫିଡବେକ୍ ପେଜ୍"],
        "Assamese": ["মতামত", "ফিডবেক পৃষ্ঠা"],
    },
    "settings.settings_page": {
        "English": ["settings", "settings page", "open settings", "change theme", "dark mode"],
        "Hindi": ["सेटिंग्स", "सेटिंग पेज", "थीम बदलो"],
        "Bengali": ["সেটিংস", "সেটিং পাতা"],
        "Tamil": ["அமைப்புகள்", "செட்டிங் பக்கம்"],
        "Telugu": ["సెట్టింగ్‌లు", "సెట్టింగ్ పేజీ"],
        "Marathi": ["सेटिंग्ज", "सेटिंग पेज"],
        "Gujarati": ["સેટિંગ્સ", "સેટિંગ પેજ"],
        "Kannada": ["ಸೆಟ್ಟಿಂಗ್‌ಗಳು", "ಸೆಟ್ಟಿಂಗ್ ಪುಟ"],
        "Malayalam": ["ക്രമീകരണങ്ങൾ", "സെറ്റിംഗ്സ് പേജ്"],
        "Punjabi": ["ਸੈਟਿੰਗਾਂ", "ਸੈਟਿੰਗ ਪੇਜ"],
        "Odia": ["ସେଟିଂସ୍", "ସେଟିଂ ପେଜ୍"],
        "Assamese": ["ছেটিংছ", "ছেটিং পৃষ্ঠা"],
    },
    "dashboard.help_center": {
        "English": ["help", "help page", "support page", "help and support"],
        "Hindi": ["सहायता", "मदद पेज"],
        "Bengali": ["সাহায্য", "সহায়তা পাতা"],
        "Tamil": ["உதவி", "உதவி பக்கம்"],
        "Telugu": ["సహాయం", "సహాయ పేజీ"],
        "Marathi": ["मदत", "मदत पेज"],
        "Gujarati": ["મદદ", "મદદ પેજ"],
        "Kannada": ["ಸಹಾಯ", "ಸಹಾಯ ಪುಟ"],
        "Malayalam": ["സഹായം", "സഹായ പേജ്"],
        "Punjabi": ["ਮਦਦ", "ਮਦਦ ਪੇਜ"],
        "Odia": ["ସାହାଯ୍ୟ", "ସାହାଯ୍ୟ ପେଜ୍"],
        "Assamese": ["সহায়", "সহায় পৃষ্ঠা"],
    },
}


def match_navigation_command(message: str, language: str):
    """Returns a Flask route endpoint name if the message matches a known
    navigation command in the given language (or English, always checked as
    a fallback since many users mix English route names into local-language
    sentences), else None."""
    text = message.strip().lower()
    for endpoint, phrases_by_lang in NAVIGATION_COMMANDS.items():
        candidates = phrases_by_lang.get(language, []) + phrases_by_lang.get("English", [])
        for phrase in candidates:
            if phrase.lower() in text:
                return endpoint
    return None


# ---------------------------------------------------------------------------
# Domain keyword glossary for multilingual scheme search (spec: "if I say
# something in my language, it should work like a search engine and find
# matching schemes"). The Excel scheme data itself is English-only, so full
# free-text translation isn't possible without an external translation
# service - but we CAN honestly support keyword search by mapping a set of
# common local-language domain words (farmer, student, health, etc.) to the
# English keyword used in the scheme dataset. This is a glossary, not a
# translator: unmapped words are simply not recognised rather than guessed.
# ---------------------------------------------------------------------------
DOMAIN_KEYWORD_GLOSSARY = {
    "Hindi": {
        "किसान": "farmer", "कृषि": "agriculture", "छात्र": "student", "छात्रवृत्ति": "scholarship",
        "स्वास्थ्य": "health", "बीमा": "insurance", "आवास": "housing", "घर": "housing",
        "विकलांग": "disability", "विधवा": "widow", "वृद्ध": "senior", "बुजुर्ग": "senior",
        "महिला": "women", "व्यवसाय": "business", "ऋण": "loan", "शिक्षा": "education",
        "पेंशन": "pension", "गरीब": "bpl", "रोजगार": "employment",
    },
    "Bengali": {
        "কৃষক": "farmer", "কৃষি": "agriculture", "ছাত্র": "student", "বৃত্তি": "scholarship",
        "স্বাস্থ্য": "health", "বীমা": "insurance", "আবাসন": "housing", "বাড়ি": "housing",
        "প্রতিবন্ধী": "disability", "বিধবা": "widow", "বয়স্ক": "senior", "প্রবীণ": "senior",
        "মহিলা": "women", "ব্যবসা": "business", "ঋণ": "loan", "শিক্ষা": "education",
        "পেনশন": "pension", "গরিব": "bpl", "কর্মসংস্থান": "employment",
    },
    "Tamil": {
        "விவசாயி": "farmer", "வேளாண்மை": "agriculture", "மாணவர்": "student", "உதவித்தொகை": "scholarship",
        "உடல்நலம்": "health", "காப்பீடு": "insurance", "வீட்டுவசதி": "housing", "வீடு": "housing",
        "மாற்றுத்திறனாளி": "disability", "விதவை": "widow", "மூத்த": "senior", "பெண்": "women",
        "வணிகம்": "business", "கடன்": "loan", "கல்வி": "education", "ஓய்வூதியம்": "pension",
        "ஏழை": "bpl", "வேலைவாய்ப்பு": "employment",
    },
    "Telugu": {
        "రైతు": "farmer", "వ్యవసాయం": "agriculture", "విద్యార్థి": "student", "స్కాలర్‌షిప్": "scholarship",
        "ఆరోగ్యం": "health", "బీమా": "insurance", "గృహనిర్మాణం": "housing", "ఇల్లు": "housing",
        "వికలాంగ": "disability", "వితంతువు": "widow", "వృద్ధుడు": "senior", "మహిళ": "women",
        "వ్యాపారం": "business", "రుణం": "loan", "విద్య": "education", "పింఛను": "pension",
        "పేద": "bpl", "ఉపాధి": "employment",
    },
    "Marathi": {
        "शेतकरी": "farmer", "शेती": "agriculture", "विद्यार्थी": "student", "शिष्यवृत्ती": "scholarship",
        "आरोग्य": "health", "विमा": "insurance", "घरकुल": "housing", "घर": "housing",
        "अपंग": "disability", "विधवा": "widow", "ज्येष्ठ": "senior", "महिला": "women",
        "व्यवसाय": "business", "कर्ज": "loan", "शिक्षण": "education", "पेन्शन": "pension",
        "गरीब": "bpl", "रोजगार": "employment",
    },
    "Gujarati": {
        "ખેડૂત": "farmer", "કૃષિ": "agriculture", "વિદ્યાર્થી": "student", "શિષ્યવૃત્તિ": "scholarship",
        "આરોગ્ય": "health", "વીમો": "insurance", "આવાસ": "housing", "ઘર": "housing",
        "વિકલાંગ": "disability", "વિધવા": "widow", "વરિષ્ઠ": "senior", "મહિલા": "women",
        "વ્યવસાય": "business", "લોન": "loan", "શિક્ષણ": "education", "પેન્શન": "pension",
        "ગરીબ": "bpl", "રોજગાર": "employment",
    },
    "Kannada": {
        "ರೈತ": "farmer", "ಕೃಷಿ": "agriculture", "ವಿದ್ಯಾರ್ಥಿ": "student", "ವಿದ್ಯಾರ್ಥಿವೇತನ": "scholarship",
        "ಆರೋಗ್ಯ": "health", "ವಿಮೆ": "insurance", "ವಸತಿ": "housing", "ಮನೆ": "housing",
        "ಅಂಗವಿಕಲ": "disability", "ವಿಧವೆ": "widow", "ಹಿರಿಯ": "senior", "ಮಹಿಳೆ": "women",
        "ವ್ಯಾಪಾರ": "business", "ಸಾಲ": "loan", "ಶಿಕ್ಷಣ": "education", "ಪಿಂಚಣಿ": "pension",
        "ಬಡ": "bpl", "ಉದ್ಯೋಗ": "employment",
    },
    "Malayalam": {
        "കർഷകൻ": "farmer", "കൃഷി": "agriculture", "വിദ്യാർത്ഥി": "student", "സ്കോളർഷിപ്പ്": "scholarship",
        "ആരോഗ്യം": "health", "ഇൻഷുറൻസ്": "insurance", "പാർപ്പിടം": "housing", "വീട്": "housing",
        "വികലാംഗ": "disability", "വിധവ": "widow", "മുതിർന്ന": "senior", "സ്ത്രീ": "women",
        "ബിസിനസ്": "business", "വായ്പ": "loan", "വിദ്യാഭ്യാസം": "education", "പെൻഷൻ": "pension",
        "ദരിദ്ര": "bpl", "തൊഴിൽ": "employment",
    },
    "Punjabi": {
        "ਕਿਸਾਨ": "farmer", "ਖੇਤੀਬਾੜੀ": "agriculture", "ਵਿਦਿਆਰਥੀ": "student", "ਵਜ਼ੀਫ਼ਾ": "scholarship",
        "ਸਿਹਤ": "health", "ਬੀਮਾ": "insurance", "ਰਿਹਾਇਸ਼": "housing", "ਘਰ": "housing",
        "ਅਪਾਹਜ": "disability", "ਵਿਧਵਾ": "widow", "ਬਜ਼ੁਰਗ": "senior", "ਔਰਤ": "women",
        "ਵਪਾਰ": "business", "ਕਰਜ਼ਾ": "loan", "ਸਿੱਖਿਆ": "education", "ਪੈਨਸ਼ਨ": "pension",
        "ਗਰੀਬ": "bpl", "ਰੁਜ਼ਗਾਰ": "employment",
    },
    "Odia": {
        "କୃଷକ": "farmer", "କୃଷି": "agriculture", "ଛାତ୍ର": "student", "ବୃତ୍ତି": "scholarship",
        "ସ୍ୱାସ୍ଥ୍ୟ": "health", "ବୀମା": "insurance", "ଆବାସ": "housing", "ଘର": "housing",
        "ଅକ୍ଷମ": "disability", "ବିଧବା": "widow", "ବରିଷ୍ଠ": "senior", "ମହିଳା": "women",
        "ବ୍ୟବସାୟ": "business", "ଋଣ": "loan", "ଶିକ୍ଷା": "education", "ପେନସନ": "pension",
        "ଗରିବ": "bpl", "ନିଯୁକ୍ତି": "employment",
    },
    "Assamese": {
        "কৃষক": "farmer", "কৃষি": "agriculture", "ছাত্ৰ": "student", "বৃত্তি": "scholarship",
        "স্বাস্থ্য": "health", "বীমা": "insurance", "আবাস": "housing", "ঘৰ": "housing",
        "অক্ষম": "disability", "বিধৱা": "widow", "প্ৰবীণ": "senior", "মহিলা": "women",
        "ব্যৱসায়": "business", "ঋণ": "loan", "শিক্ষা": "education", "পেঞ্চন": "pension",
        "দুখীয়া": "bpl", "নিযুক্তি": "employment",
    },
}


def translate_keywords_to_english(message: str, language: str) -> str:
    """Scans the message for known glossary words in the given language and
    returns a space-joined string of their English keyword equivalents
    (e.g. Hindi "मुझे किसान योजना चाहिए" -> "farmer"). Returns an empty
    string if no glossary words matched (caller should then fall back to
    treating the message as already-English, or report nothing found)."""
    if language == "English":
        return message
    glossary = DOMAIN_KEYWORD_GLOSSARY.get(language, {})
    found = [english for local_word, english in glossary.items() if local_word in message]
    return " ".join(dict.fromkeys(found))  # dedupe, keep order


def detect_language(text: str, preferred_language: str = "English") -> tuple[str, float]:
    """Return (language, confidence) using script plus lexical hints.

    Confidence is deliberately conservative. Ambiguous Latin-script input uses
    the user's preference instead of pretending to identify a language.
    """
    text = text or ""
    if not text.strip():
        return preferred_language if is_text_language_supported(preferred_language) else "English", 0.0
    hinted = detect_language_hint(text)
    if hinted in {"Bengali", "Assamese"}:
        distinctive = ["মই", "মোৰ", "আপোনাৰ", "আঁচনি", "অসম"] if hinted == "Assamese" else ["আমি", "আমার", "আপনার", "প্রকল্প", "পাওয়া"]
        confidence = 0.95 if any(x in text for x in distinctive) else 0.62
        return hinted, confidence
    # For non-Latin scripts, a single script match is strong enough for this
    # offline prototype. Latin-only text is intentionally low-confidence.
    if hinted != "English":
        return hinted, 0.92
    return (preferred_language if is_text_language_supported(preferred_language) else "English"), 0.45
