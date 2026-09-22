// PATH: GovScheme/static/js/i18n.js
(function () {
  const translations = {
    Hindi: {Dashboard:'डैशबोर्ड', Schemes:'योजनाएं', Applications:'आवेदन', 'Saved Schemes':'सहेजी गई योजनाएं', Notifications:'सूचनाएं', Profile:'प्रोफ़ाइल', Settings:'सेटिंग्स', 'Help & Support':'सहायता और समर्थन', Logout:'लॉग आउट', Feedback:'प्रतिक्रिया', 'Government Schemes':'सरकारी योजनाएं', 'Check My Eligibility':'मेरी पात्रता जांचें', 'View Details':'विवरण देखें', Search:'खोजें'},
    Bengali: {Dashboard:'ড্যাশবোর্ড', Schemes:'প্রকল্প', Applications:'আবেদন', 'Saved Schemes':'সংরক্ষিত প্রকল্প', Notifications:'বিজ্ঞপ্তি', Profile:'প্রোফাইল', Settings:'সেটিংস', 'Help & Support':'সহায়তা ও সমর্থন', Logout:'লগ আউট', Feedback:'প্রতিক্রিয়া', Search:'অনুসন্ধান', 'New & Updated Schemes':'নতুন ও আপডেট প্রকল্প', 'Customer Care':'গ্রাহক সহায়তা'},
    Tamil: {Dashboard:'டாஷ்போர்டு', Schemes:'திட்டங்கள்', Applications:'விண்ணப்பங்கள்', 'Saved Schemes':'சேமித்த திட்டங்கள்', Notifications:'அறிவிப்புகள்', Profile:'சுயவிவரம்', Settings:'அமைப்புகள்', 'Help & Support':'உதவி மற்றும் ஆதரவு', Logout:'வெளியேறு', Feedback:'கருத்து', Search:'தேடல்', 'New & Updated Schemes':'புதிய மற்றும் புதுப்பிக்கப்பட்ட திட்டங்கள்', 'Customer Care':'வாடிக்கையாளர் உதவி'},
    Telugu: {Dashboard:'డాష్‌బోర్డ్', Schemes:'పథకాలు', Applications:'దరఖాస్తులు', 'Saved Schemes':'సేవ్ చేసిన పథకాలు', Notifications:'నోటిఫికేషన్లు', Profile:'ప్రొఫైల్', Settings:'సెట్టింగ్‌లు', 'Help & Support':'సహాయం & మద్దతు', Logout:'లాగ్ అవుట్', Feedback:'అభిప్రాయం', Search:'శోధన', 'New & Updated Schemes':'కొత్త మరియు నవీకరించిన పథకాలు', 'Customer Care':'కస్టమర్ సహాయం'},
    Marathi: {Dashboard:'डॅशबोर्ड', Schemes:'योजना', Applications:'अर्ज', 'Saved Schemes':'जतन केलेल्या योजना', Notifications:'सूचना', Profile:'प्रोफाइल', Settings:'सेटिंग्ज', 'Help & Support':'मदत आणि समर्थन', Logout:'लॉग आउट', Feedback:'अभिप्राय', Search:'शोधा', 'New & Updated Schemes':'नवीन आणि अद्ययावत योजना', 'Customer Care':'ग्राहक सहाय्य'},
    Gujarati: {Dashboard:'ડેશબોર્ડ', Schemes:'યોજનાઓ', Applications:'અરજીઓ', 'Saved Schemes':'સાચવેલી યોજનાઓ', Notifications:'સૂચનાઓ', Profile:'પ્રોફાઇલ', Settings:'સેટિંગ્સ', 'Help & Support':'મદદ અને સહાય', Logout:'લૉગ આઉટ', Feedback:'પ્રતિસાદ', Search:'શોધો', 'New & Updated Schemes':'નવી અને અપડેટ કરેલી યોજનાઓ', 'Customer Care':'ગ્રાહક સહાય'},
    Kannada: {Dashboard:'ಡ್ಯಾಶ್‌ಬೋರ್ಡ್', Schemes:'ಯೋಜನೆಗಳು', Applications:'ಅರ್ಜಿಗಳು', 'Saved Schemes':'ಉಳಿಸಿದ ಯೋಜನೆಗಳು', Notifications:'ಅಧಿಸೂಚನೆಗಳು', Profile:'ಪ್ರೊಫೈಲ್', Settings:'ಸೆಟ್ಟಿಂಗ್‌ಗಳು', 'Help & Support':'ಸಹಾಯ ಮತ್ತು ಬೆಂಬಲ', Logout:'ಲಾಗ್ ಔಟ್', Feedback:'ಪ್ರತಿಕ್ರಿಯೆ', Search:'ಹುಡುಕಿ', 'New & Updated Schemes':'ಹೊಸ ಮತ್ತು ನವೀಕರಿಸಿದ ಯೋಜನೆಗಳು', 'Customer Care':'ಗ್ರಾಹಕ ಸಹಾಯ'},
    Malayalam: {Dashboard:'ഡാഷ്ബോർഡ്', Schemes:'പദ്ധതികൾ', Applications:'അപേക്ഷകൾ', 'Saved Schemes':'സംരക്ഷിച്ച പദ്ധതികൾ', Notifications:'അറിയിപ്പുകൾ', Profile:'പ്രൊഫൈൽ', Settings:'ക്രമീകരണങ്ങൾ', 'Help & Support':'സഹായവും പിന്തുണയും', Logout:'ലോഗ് ഔട്ട്', Feedback:'അഭിപ്രായം', Search:'തിരയുക', 'New & Updated Schemes':'പുതിയതും പുതുക്കിയതുമായ പദ്ധതികൾ', 'Customer Care':'ഉപഭോക്തൃ സഹായം'},
    Punjabi: {Dashboard:'ਡੈਸ਼ਬੋਰਡ', Schemes:'ਯੋਜਨਾਵਾਂ', Applications:'ਅਰਜ਼ੀਆਂ', 'Saved Schemes':'ਸੁਰੱਖਿਅਤ ਯੋਜਨਾਵਾਂ', Notifications:'ਸੂਚਨਾਵਾਂ', Profile:'ਪ੍ਰੋਫਾਈਲ', Settings:'ਸੈਟਿੰਗਾਂ', 'Help & Support':'ਮਦਦ ਅਤੇ ਸਹਾਇਤਾ', Logout:'ਲੌਗ ਆਊਟ', Feedback:'ਫੀਡਬੈਕ', Search:'ਖੋਜੋ', 'New & Updated Schemes':'ਨਵੀਆਂ ਅਤੇ ਅਪਡੇਟ ਕੀਤੀਆਂ ਯੋਜਨਾਵਾਂ', 'Customer Care':'ਗਾਹਕ ਸਹਾਇਤਾ'},
    Odia: {Dashboard:'ଡ୍ୟାସବୋର୍ଡ', Schemes:'ଯୋଜନା', Applications:'ଆବେଦନ', 'Saved Schemes':'ସଞ୍ଚିତ ଯୋଜନା', Notifications:'ବିଜ୍ଞପ୍ତି', Profile:'ପ୍ରୋଫାଇଲ', Settings:'ସେଟିଂସ', 'Help & Support':'ସହାୟତା ଓ ସମର୍ଥନ', Logout:'ଲଗଆଉଟ', Feedback:'ମତାମତ', Search:'ଖୋଜନ୍ତୁ', 'New & Updated Schemes':'ନୂତନ ଓ ଅଦ୍ୟତନ ଯୋଜନା', 'Customer Care':'ଗ୍ରାହକ ସହାୟତା'},
    Assamese: {Dashboard:'ডেশ্বব’ৰ্ড', Schemes:'আঁচনি', Applications:'আবেদন', 'Saved Schemes':'সংৰক্ষিত আঁচনি', Notifications:'জাননী', Profile:'প্ৰফাইল', Settings:'ছেটিংছ', 'Help & Support':'সহায় আৰু সমৰ্থন', Logout:'লগ আউট', Feedback:'মতামত', Search:'সন্ধান', 'New & Updated Schemes':'নতুন আৰু আপডেট কৰা আঁচনি', 'Customer Care':'গ্ৰাহক সহায়তা'}
  };
  function applyLanguage(lang) {
    document.documentElement.lang = lang === 'Hindi' ? 'hi' : (lang === 'Tamil' ? 'ta' : 'en');
    const map = translations[lang] || {};
    document.querySelectorAll('[data-i18n]').forEach(el => { if (map[el.dataset.i18n]) el.textContent = map[el.dataset.i18n]; });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { if (map[el.dataset.i18nPlaceholder]) el.placeholder = map[el.dataset.i18nPlaceholder]; });
    document.querySelectorAll('[data-language-selector]').forEach(el => { el.value = lang; });
  }
  async function setLanguage(lang) {
    const r = await fetch('/settings/language', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({language:lang})});
    if (r.ok) { localStorage.setItem('smartgov-language', lang); applyLanguage(lang); window.location.reload(); }
  }
  window.smartGovSetLanguage = setLanguage;
  document.addEventListener('DOMContentLoaded', () => {
    const initial = document.body.dataset.language || localStorage.getItem('smartgov-language') || 'English';
    applyLanguage(initial);
    document.querySelectorAll('[data-language-selector]').forEach(el => el.addEventListener('change', e => setLanguage(e.target.value)));
  });
})();
