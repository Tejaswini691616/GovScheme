# PATH: GovScheme/ai/response_generator.py
"""
Builds chatbot response TEXT from real data (scheme DB, eligibility engine,
recommendation service). Never invents scheme facts (spec section 40/47).

Multilingual note (honesty, spec section 28/29): the underlying scheme
dataset (names, descriptions, criteria) is only available in English in
the source Excel workbook. We translate the surrounding UI phrases
("Here are your recommended schemes:", "Why recommended:", etc.) into the
selected language using the PHRASES dictionary below - all 12 target
languages (spec section 28) now have a full phrase set. Scheme names and
data fields stay in English with a one-line note, rather than silently
mistranslating factual government-scheme content with no verified
translation source. This is a deliberate, disclosed limitation - not a bug.
These translations were written for this prototype and have not been
reviewed by native speakers of every listed language; treat them as a
solid first draft and have a fluent speaker sanity-check the phrasing
before using this in a real deployment.
"""

PHRASES = {
    "English": {
        "recommended_header": "Here are your top recommended schemes:",
        "why_recommended": "Why recommended:",
        "no_recommendations": "I couldn't find any schemes you're potentially eligible for right now based on your profile.",
        "eligible_yes": "Based on the configured prototype criteria, you appear potentially eligible for {scheme}.",
        "eligible_no": "Based on the configured prototype criteria, you do not currently appear eligible for {scheme}.",
        "not_found": "I couldn't find that scheme in the Yojana Bharath database.",
        "disclaimer": "This is a prototype assessment, not an official government decision. Please verify with the official source before applying.",
        "missing_profile": "I need a bit more profile information to answer that. Please complete your profile.",
        "data_note": "(Scheme details are shown in English as sourced from the official dataset.)",
    },
    "Hindi": {
        "recommended_header": "आपके लिए अनुशंसित योजनाएं:",
        "why_recommended": "अनुशंसा का कारण:",
        "no_recommendations": "आपकी प्रोफ़ाइल के आधार पर फिलहाल कोई योजना नहीं मिली जिसके लिए आप संभावित रूप से पात्र हों।",
        "eligible_yes": "कॉन्फ़िगर किए गए प्रोटोटाइप मानदंडों के अनुसार, आप {scheme} के लिए संभावित रूप से पात्र प्रतीत होते हैं।",
        "eligible_no": "कॉन्फ़िगर किए गए प्रोटोटाइप मानदंडों के अनुसार, आप वर्तमान में {scheme} के लिए पात्र नहीं दिखते।",
        "not_found": "यह योजना Yojana Bharath डेटाबेस में नहीं मिली।",
        "disclaimer": "यह एक प्रोटोटाइप मूल्यांकन है, आधिकारिक सरकारी निर्णय नहीं। कृपया आवेदन करने से पहले आधिकारिक स्रोत से पुष्टि करें।",
        "missing_profile": "इसका उत्तर देने के लिए मुझे थोड़ी और प्रोफ़ाइल जानकारी चाहिए। कृपया अपनी प्रोफ़ाइल पूरी करें।",
        "data_note": "(योजना विवरण आधिकारिक डेटासेट के अनुसार अंग्रेज़ी में दिखाए गए हैं।)",
    },
    "Bengali": {
        "recommended_header": "আপনার জন্য প্রস্তাবিত প্রকল্পগুলি:",
        "why_recommended": "সুপারিশের কারণ:",
        "no_recommendations": "আপনার প্রোফাইলের ভিত্তিতে এই মুহূর্তে এমন কোনো প্রকল্প পাওয়া যায়নি যার জন্য আপনি সম্ভাব্যভাবে যোগ্য।",
        "eligible_yes": "কনফিগার করা প্রোটোটাইপ মানদণ্ড অনুযায়ী, আপনি সম্ভবত {scheme}-এর জন্য যোগ্য।",
        "eligible_no": "কনফিগার করা প্রোটোটাইপ মানদণ্ড অনুযায়ী, আপনি বর্তমানে {scheme}-এর জন্য যোগ্য নন।",
        "not_found": "এই প্রকল্পটি Yojana Bharath ডেটাবেসে পাওয়া যায়নি।",
        "disclaimer": "এটি একটি প্রোটোটাইপ মূল্যায়ন, সরকারি সিদ্ধান্ত নয়। আবেদন করার আগে দয়া করে সরকারি উৎস থেকে যাচাই করুন।",
        "missing_profile": "এর উত্তর দিতে আমার আরও কিছু প্রোফাইল তথ্য দরকার। দয়া করে আপনার প্রোফাইল সম্পূর্ণ করুন।",
        "data_note": "(প্রকল্পের বিবরণ মূল ডেটাসেট অনুযায়ী ইংরেজিতে দেখানো হয়েছে।)",
    },
    "Tamil": {
        "recommended_header": "உங்களுக்கு பரிந்துரைக்கப்படும் திட்டங்கள்:",
        "why_recommended": "பரிந்துரைக்கான காரணம்:",
        "no_recommendations": "உங்கள் சுயவிவரத்தின் அடிப்படையில் தற்போது நீங்கள் தகுதி பெறக்கூடிய திட்டங்கள் எதுவும் கிடைக்கவில்லை.",
        "eligible_yes": "கட்டமைக்கப்பட்ட முன்மாதிரி அளவுகோல்களின்படி, நீங்கள் {scheme}-க்கு தகுதி பெற்றிருக்கலாம்.",
        "eligible_no": "கட்டமைக்கப்பட்ட முன்மாதிரி அளவுகோல்களின்படி, நீங்கள் தற்போது {scheme}-க்கு தகுதியற்றவராக உள்ளீர்கள்.",
        "not_found": "இந்த திட்டம் Yojana Bharath தரவுத்தளத்தில் கிடைக்கவில்லை.",
        "disclaimer": "இது ஒரு முன்மாதிரி மதிப்பீடு, அரசாங்க முடிவு அல்ல. விண்ணப்பிக்கும் முன் அதிகாரப்பூர்வ மூலத்தில் உறுதிப்படுத்தவும்.",
        "missing_profile": "இதற்கு பதிலளிக்க எனக்கு கொஞ்சம் கூடுதல் சுயவிவரத் தகவல் தேவை. தயவுசெய்து உங்கள் சுயவிவரத்தை முடிக்கவும்.",
        "data_note": "(திட்ட விவரங்கள் அதிகாரப்பூர்வ தரவுத்தொகுப்பின்படி ஆங்கிலத்தில் காட்டப்படுகின்றன.)",
    },
    "Telugu": {
        "recommended_header": "మీ కోసం సిఫార్సు చేయబడిన పథకాలు:",
        "why_recommended": "సిఫార్సుకు కారణం:",
        "no_recommendations": "మీ ప్రొఫైల్ ఆధారంగా ప్రస్తుతం మీరు అర్హులయ్యే పథకాలు ఏవీ కనుగొనబడలేదు.",
        "eligible_yes": "కాన్ఫిగర్ చేసిన ప్రోటోటైప్ ప్రమాణాల ప్రకారం, మీరు {scheme} కోసం అర్హులుగా కనిపిస్తున్నారు.",
        "eligible_no": "కాన్ఫిగర్ చేసిన ప్రోటోటైప్ ప్రమాణాల ప్రకారం, మీరు ప్రస్తుతం {scheme} కోసం అర్హులు కాదు.",
        "not_found": "ఈ పథకం Yojana Bharath డేటాబేస్‌లో కనుగొనబడలేదు.",
        "disclaimer": "ఇది ఒక ప్రోటోటైప్ మదింపు, అధికారిక ప్రభుత్వ నిర్ణయం కాదు. దరఖాస్తు చేయడానికి ముందు అధికారిక మూలం నుండి ధృవీకరించండి.",
        "missing_profile": "దీనికి సమాధానం ఇవ్వడానికి నాకు కొంచెం ఎక్కువ ప్రొఫైల్ సమాచారం అవసరం. దయచేసి మీ ప్రొఫైల్‌ను పూర్తి చేయండి.",
        "data_note": "(పథక వివరాలు అధికారిక డేటాసెట్ ప్రకారం ఆంగ్లంలో చూపబడ్డాయి.)",
    },
    "Marathi": {
        "recommended_header": "तुमच्यासाठी शिफारस केलेल्या योजना:",
        "why_recommended": "शिफारशीचे कारण:",
        "no_recommendations": "तुमच्या प्रोफाइलच्या आधारे सध्या तुम्ही पात्र ठरू शकाल अशी कोणतीही योजना सापडली नाही.",
        "eligible_yes": "कॉन्फिगर केलेल्या प्रोटोटाइप निकषांनुसार, तुम्ही {scheme} साठी संभाव्यतः पात्र दिसता.",
        "eligible_no": "कॉन्फिगर केलेल्या प्रोटोटाइप निकषांनुसार, तुम्ही सध्या {scheme} साठी पात्र दिसत नाही.",
        "not_found": "ही योजना Yojana Bharath डेटाबेसमध्ये सापडली नाही.",
        "disclaimer": "हे एक प्रोटोटाइप मूल्यांकन आहे, अधिकृत सरकारी निर्णय नाही. अर्ज करण्यापूर्वी कृपया अधिकृत स्रोताकडून पडताळणी करा.",
        "missing_profile": "याचे उत्तर देण्यासाठी मला थोडी अधिक प्रोफाइल माहिती हवी आहे. कृपया तुमचे प्रोफाइल पूर्ण करा.",
        "data_note": "(योजनेचा तपशील अधिकृत डेटासेटनुसार इंग्रजीत दाखवला आहे.)",
    },
    "Gujarati": {
        "recommended_header": "તમારા માટે ભલામણ કરેલી યોજનાઓ:",
        "why_recommended": "ભલામણનું કારણ:",
        "no_recommendations": "તમારી પ્રોફાઇલના આધારે હાલમાં તમે પાત્ર બની શકો તેવી કોઈ યોજના મળી નથી.",
        "eligible_yes": "કન્ફિગર કરેલા પ્રોટોટાઇપ માપદંડો અનુસાર, તમે {scheme} માટે સંભવિતપણે પાત્ર જણાઓ છો.",
        "eligible_no": "કન્ફિગર કરેલા પ્રોટોટાઇપ માપદંડો અનુસાર, તમે હાલમાં {scheme} માટે પાત્ર નથી.",
        "not_found": "આ યોજના Yojana Bharath ડેટાબેઝમાં મળી નથી.",
        "disclaimer": "આ એક પ્રોટોટાઇપ મૂલ્યાંકન છે, સત્તાવાર સરકારી નિર્ણય નથી. અરજી કરતા પહેલા કૃપા કરીને સત્તાવાર સ્ત્રોત પાસેથી ખાતરી કરો.",
        "missing_profile": "આનો જવાબ આપવા માટે મને થોડી વધુ પ્રોફાઇલ માહિતીની જરૂર છે. કૃપા કરીને તમારી પ્રોફાઇલ પૂર્ણ કરો.",
        "data_note": "(યોજનાની વિગતો સત્તાવાર ડેટાસેટ મુજબ અંગ્રેજીમાં દર્શાવવામાં આવી છે.)",
    },
    "Kannada": {
        "recommended_header": "ನಿಮಗಾಗಿ ಶಿಫಾರಸು ಮಾಡಲಾದ ಯೋಜನೆಗಳು:",
        "why_recommended": "ಶಿಫಾರಸಿಗೆ ಕಾರಣ:",
        "no_recommendations": "ನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ಆಧಾರದ ಮೇಲೆ ಪ್ರಸ್ತುತ ನೀವು ಅರ್ಹರಾಗಬಹುದಾದ ಯಾವುದೇ ಯೋಜನೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ.",
        "eligible_yes": "ಕಾನ್ಫಿಗರ್ ಮಾಡಲಾದ ಮೂಲಮಾದರಿ ಮಾನದಂಡಗಳ ಪ್ರಕಾರ, ನೀವು {scheme} ಗೆ ಅರ್ಹರಾಗಿ ಕಾಣಿಸುತ್ತೀರಿ.",
        "eligible_no": "ಕಾನ್ಫಿಗರ್ ಮಾಡಲಾದ ಮೂಲಮಾದರಿ ಮಾನದಂಡಗಳ ಪ್ರಕಾರ, ನೀವು ಪ್ರಸ್ತುತ {scheme} ಗೆ ಅರ್ಹರಲ್ಲ.",
        "not_found": "ಈ ಯೋಜನೆ Yojana Bharath ಡೇಟಾಬೇಸ್‌ನಲ್ಲಿ ಕಂಡುಬಂದಿಲ್ಲ.",
        "disclaimer": "ಇದು ಒಂದು ಮೂಲಮಾದರಿ ಮೌಲ್ಯಮಾಪನ, ಅಧಿಕೃತ ಸರ್ಕಾರಿ ನಿರ್ಧಾರವಲ್ಲ. ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ಮೊದಲು ದಯವಿಟ್ಟು ಅಧಿಕೃತ ಮೂಲದಿಂದ ಪರಿಶೀಲಿಸಿ.",
        "missing_profile": "ಇದಕ್ಕೆ ಉತ್ತರಿಸಲು ನನಗೆ ಸ್ವಲ್ಪ ಹೆಚ್ಚಿನ ಪ್ರೊಫೈಲ್ ಮಾಹಿತಿ ಬೇಕು. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ಅನ್ನು ಪೂರ್ಣಗೊಳಿಸಿ.",
        "data_note": "(ಯೋಜನೆಯ ವಿವರಗಳನ್ನು ಅಧಿಕೃತ ಡೇಟಾಸೆಟ್ ಪ್ರಕಾರ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ತೋರಿಸಲಾಗಿದೆ.)",
    },
    "Malayalam": {
        "recommended_header": "നിങ്ങൾക്കായി ശുപാർശ ചെയ്ത പദ്ധതികൾ:",
        "why_recommended": "ശുപാർശയുടെ കാരണം:",
        "no_recommendations": "നിങ്ങളുടെ പ്രൊഫൈൽ അടിസ്ഥാനമാക്കി നിലവിൽ നിങ്ങൾക്ക് യോഗ്യതയുള്ള പദ്ധതികളൊന്നും കണ്ടെത്തിയില്ല.",
        "eligible_yes": "കോൺഫിഗർ ചെയ്ത പ്രോട്ടോടൈപ്പ് മാനദണ്ഡങ്ങൾ അനുസരിച്ച്, നിങ്ങൾ {scheme}-ന് യോഗ്യനായി കാണപ്പെടുന്നു.",
        "eligible_no": "കോൺഫിഗർ ചെയ്ത പ്രോട്ടോടൈപ്പ് മാനദണ്ഡങ്ങൾ അനുസരിച്ച്, നിങ്ങൾ നിലവിൽ {scheme}-ന് യോഗ്യനല്ല.",
        "not_found": "ഈ പദ്ധതി Yojana Bharath ഡാറ്റാബേസിൽ കണ്ടെത്തിയില്ല.",
        "disclaimer": "ഇത് ഒരു പ്രോട്ടോടൈപ്പ് വിലയിരുത്തലാണ്, ഔദ്യോഗിക സർക്കാർ തീരുമാനമല്ല. അപേക്ഷിക്കുന്നതിന് മുമ്പ് ഔദ്യോഗിക ഉറവിടത്തിൽ നിന്ന് സ്ഥിരീകരിക്കുക.",
        "missing_profile": "ഇതിന് ഉത്തരം നൽകാൻ എനിക്ക് കുറച്ചുകൂടി പ്രൊഫൈൽ വിവരങ്ങൾ ആവശ്യമാണ്. ദയവായി നിങ്ങളുടെ പ്രൊഫൈൽ പൂർത്തിയാക്കുക.",
        "data_note": "(പദ്ധതി വിശദാംശങ്ങൾ ഔദ്യോഗിക ഡാറ്റാസെറ്റ് പ്രകാരം ഇംഗ്ലീഷിൽ കാണിച്ചിരിക്കുന്നു.)",
    },
    "Punjabi": {
        "recommended_header": "ਤੁਹਾਡੇ ਲਈ ਸਿਫਾਰਸ਼ ਕੀਤੀਆਂ ਯੋਜਨਾਵਾਂ:",
        "why_recommended": "ਸਿਫਾਰਸ਼ ਦਾ ਕਾਰਨ:",
        "no_recommendations": "ਤੁਹਾਡੀ ਪ੍ਰੋਫਾਈਲ ਦੇ ਆਧਾਰ 'ਤੇ ਇਸ ਵੇਲੇ ਕੋਈ ਵੀ ਯੋਜਨਾ ਨਹੀਂ ਮਿਲੀ ਜਿਸ ਲਈ ਤੁਸੀਂ ਯੋਗ ਹੋ ਸਕਦੇ ਹੋ।",
        "eligible_yes": "ਕੌਂਫਿਗਰ ਕੀਤੇ ਪ੍ਰੋਟੋਟਾਈਪ ਮਾਪਦੰਡਾਂ ਅਨੁਸਾਰ, ਤੁਸੀਂ {scheme} ਲਈ ਸੰਭਾਵੀ ਤੌਰ 'ਤੇ ਯੋਗ ਜਾਪਦੇ ਹੋ।",
        "eligible_no": "ਕੌਂਫਿਗਰ ਕੀਤੇ ਪ੍ਰੋਟੋਟਾਈਪ ਮਾਪਦੰਡਾਂ ਅਨੁਸਾਰ, ਤੁਸੀਂ ਇਸ ਵੇਲੇ {scheme} ਲਈ ਯੋਗ ਨਹੀਂ ਹੋ।",
        "not_found": "ਇਹ ਯੋਜਨਾ Yojana Bharath ਡੇਟਾਬੇਸ ਵਿੱਚ ਨਹੀਂ ਮਿਲੀ।",
        "disclaimer": "ਇਹ ਇੱਕ ਪ੍ਰੋਟੋਟਾਈਪ ਮੁਲਾਂਕਣ ਹੈ, ਅਧਿਕਾਰਤ ਸਰਕਾਰੀ ਫੈਸਲਾ ਨਹੀਂ। ਅਰਜ਼ੀ ਦੇਣ ਤੋਂ ਪਹਿਲਾਂ ਕਿਰਪਾ ਕਰਕੇ ਅਧਿਕਾਰਤ ਸਰੋਤ ਤੋਂ ਪੁਸ਼ਟੀ ਕਰੋ।",
        "missing_profile": "ਇਸਦਾ ਜਵਾਬ ਦੇਣ ਲਈ ਮੈਨੂੰ ਥੋੜ੍ਹੀ ਹੋਰ ਪ੍ਰੋਫਾਈਲ ਜਾਣਕਾਰੀ ਚਾਹੀਦੀ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਪ੍ਰੋਫਾਈਲ ਪੂਰੀ ਕਰੋ।",
        "data_note": "(ਯੋਜਨਾ ਦੇ ਵੇਰਵੇ ਅਧਿਕਾਰਤ ਡੇਟਾਸੈੱਟ ਅਨੁਸਾਰ ਅੰਗਰੇਜ਼ੀ ਵਿੱਚ ਦਿਖਾਏ ਗਏ ਹਨ।)",
    },
    "Odia": {
        "recommended_header": "ଆପଣଙ୍କ ପାଇଁ ସୁପାରିଶ କରାଯାଇଥିବା ଯୋଜନାଗୁଡ଼ିକ:",
        "why_recommended": "ସୁପାରିଶର କାରଣ:",
        "no_recommendations": "ଆପଣଙ୍କ ପ୍ରୋଫାଇଲ ଆଧାରରେ ବର୍ତ୍ତମାନ ଆପଣ ଯୋଗ୍ୟ ହୋଇପାରୁଥିବା କୌଣସି ଯୋଜନା ମିଳିଲା ନାହିଁ।",
        "eligible_yes": "କନଫିଗର କରାଯାଇଥିବା ପ୍ରୋଟୋଟାଇପ ମାନଦଣ୍ଡ ଅନୁସାରେ, ଆପଣ {scheme} ପାଇଁ ସମ୍ଭାବ୍ୟ ଭାବେ ଯୋଗ୍ୟ ଜଣାପଡ଼ୁଛନ୍ତି।",
        "eligible_no": "କନଫିଗର କରାଯାଇଥିବା ପ୍ରୋଟୋଟାଇପ ମାନଦଣ୍ଡ ଅନୁସାରେ, ଆପଣ ବର୍ତ୍ତମାନ {scheme} ପାଇଁ ଯୋଗ୍ୟ ନୁହଁନ୍ତି।",
        "not_found": "ଏହି ଯୋଜନା Yojana Bharath ଡାଟାବେସରେ ମିଳିଲା ନାହିଁ।",
        "disclaimer": "ଏହା ଏକ ପ୍ରୋଟୋଟାଇପ ମୂଲ୍ୟାଙ୍କନ, ସରକାରୀ ନିଷ୍ପତ୍ତି ନୁହେଁ। ଆବେଦନ କରିବା ପୂର୍ବରୁ ଦୟାକରି ସରକାରୀ ଉତ୍ସରୁ ନିଶ୍ଚିତ କରନ୍ତୁ।",
        "missing_profile": "ଏହାର ଉତ୍ତର ଦେବାକୁ ମୋତେ ଅଳ୍ପ ଅଧିକ ପ୍ରୋଫାଇଲ ସୂଚନା ଆବଶ୍ୟକ। ଦୟାକରି ଆପଣଙ୍କ ପ୍ରୋଫାଇଲ ସମ୍ପୂର୍ଣ୍ଣ କରନ୍ତୁ।",
        "data_note": "(ଯୋଜନା ବିବରଣୀ ଅଧିକାରିକ ଡାଟାସେଟ ଅନୁଯାୟୀ ଇଂରାଜୀରେ ଦେଖାଯାଇଛି। ଏହି ଭାଷା ପାଇଁ ଭଏସ୍ ସହାୟତା ଏବେ ଉପଲବ୍ଧ ନାହିଁ, କେବଳ ଟେକ୍ସଟ୍ ଚାଟ୍।)",
    },
    "Assamese": {
        "recommended_header": "আপোনাৰ বাবে পৰামৰ্শ দিয়া আঁচনিসমূহ:",
        "why_recommended": "পৰামৰ্শৰ কাৰণ:",
        "no_recommendations": "আপোনাৰ প্ৰ'ফাইলৰ ওপৰত ভিত্তি কৰি বৰ্তমান আপুনি যোগ্য হ'ব পৰা কোনো আঁচনি পোৱা নগ'ল।",
        "eligible_yes": "কনফিগাৰ কৰা প্ৰ'ট'টাইপ মাপকাঠী অনুসৰি, আপুনি {scheme}ৰ বাবে যোগ্য বুলি দেখা গৈছে।",
        "eligible_no": "কনফিগাৰ কৰা প্ৰ'ট'টাইপ মাপকাঠী অনুসৰি, আপুনি বৰ্তমান {scheme}ৰ বাবে যোগ্য নহয়।",
        "not_found": "এই আঁচনিটো Yojana Bharath ডেটাবেছত পোৱা নগ'ল।",
        "disclaimer": "এইটো এটা প্ৰ'ট'টাইপ মূল্যাংকন, চৰকাৰী সিদ্ধান্ত নহয়। আবেদন কৰাৰ আগতে অনুগ্ৰহ কৰি চৰকাৰী উৎসৰ পৰা নিশ্চিত কৰক।",
        "missing_profile": "ইয়াৰ উত্তৰ দিবলৈ মোক অলপ অধিক প্ৰ'ফাইল তথ্যৰ প্ৰয়োজন। অনুগ্ৰহ কৰি আপোনাৰ প্ৰ'ফাইল সম্পূৰ্ণ কৰক।",
        "data_note": "(আঁচনিৰ বিৱৰণ চৰকাৰী ডাটাছেট অনুসৰি ইংৰাজীত দেখুওৱা হৈছে। এই ভাষাৰ বাবে ভইচ সহায়তা বৰ্তমান উপলব্ধ নহয়, কেৱল টেক্সট চেট।)",
    },
}

FALLBACK_NOTE = "(This language's chat interface phrases are not yet fully translated in this prototype; showing English text.)"


def _phrases(language: str) -> dict:
    return PHRASES.get(language, PHRASES["English"])


def render_recommendations(recommendations: list, language: str = "English") -> str:
    p = _phrases(language)
    if not recommendations:
        return p["no_recommendations"]

    lines = [p["recommended_header"], ""]
    for i, rec in enumerate(recommendations, start=1):
        scheme = rec["scheme"]
        result = rec["result"]
        lines.append(f"{i}. {scheme['scheme_name']} (Model Relevance Score: {rec['relevance_score']}%)")
        if result.matched:
            lines.append(f"   {p['why_recommended']}")
            for m in result.matched:
                lines.append(f"   ✓ {m}")
        lines.append("")
    lines.append(p["disclaimer"])
    if language != "English":
        lines.append(p["data_note"])
    return "\n".join(lines)


def render_eligibility(scheme_name: str, result, language: str = "English") -> str:
    p = _phrases(language)
    lines = []
    if result.is_eligible:
        lines.append(p["eligible_yes"].format(scheme=scheme_name))
    else:
        lines.append(p["eligible_no"].format(scheme=scheme_name))
    lines.append("")
    lines.append(result.explanation_text())
    lines.append("")
    lines.append(p["disclaimer"])
    return "\n".join(lines)


def render_scheme_details(scheme: dict, language: str = "English") -> str:
    p = _phrases(language)
    lines = [
        f"**{scheme['scheme_name']}**",
        f"Category: {scheme.get('category') or 'N/A'}",
        f"Eligibility criteria: {scheme.get('eligibility') or 'Not specified in dataset.'}",
        f"Official link: {scheme.get('official_link') or 'Official link not available in current dataset.'}",
        "",
        p["disclaimer"],
    ]
    if language != "English":
        lines.append(p["data_note"])
    return "\n".join(lines)


def not_found_message(language: str = "English") -> str:
    return _phrases(language)["not_found"]


def missing_profile_message(language: str = "English") -> str:
    return _phrases(language)["missing_profile"]
