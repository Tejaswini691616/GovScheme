// PATH: GovScheme/static/js/chatbot.js
(function () {
  const fab = document.getElementById('sgChatFab');
  const panel = document.getElementById('sgChatPanel');
  if (!fab || !panel) return;
  const close = document.getElementById('sgChatClose');
  const clear = document.getElementById('sgChatClear');
  const input = document.getElementById('sgChatInput');
  const send = document.getElementById('sgChatSend');
  const mic = document.getElementById('sgChatMic');
  const messages = document.getElementById('sgChatMessages');
  const status = document.getElementById('sgChatStatus');
  const language = document.getElementById('sgChatLanguage');
  let recognition = null;
  let voices = [];
  let voiceCapabilities = {};
  let ttsCapabilities = {};

  function addMessage(text, who='bot', action=null) {
    const el = document.createElement('div'); el.className = `sg-chat-bubble ${who}`;
    el.textContent = text; messages.appendChild(el);
    if (action) {
      const a = document.createElement('button'); a.className='btn btn-sm btn-outline-success mt-2';
      a.textContent = action.label || 'Open'; a.onclick = () => executeAction(action); el.appendChild(a);
    }
    messages.scrollTop = messages.scrollHeight;
  }
  function setStatus(t) { status.textContent = t || ''; }
  function executeAction(action) {
    if (!action) return;
    if (action.type === 'navigate' || action.type === 'search_schemes') window.location.href = action.url;
    else if (action.type === 'offer_complaint') {
      if (confirm('Would you like me to raise this with customer support?')) {
        fetch('/api/complaints/raise-from-chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({description:action.draft_description,language:language.value})})
          .then(r=>r.json()).then(d=>addMessage(d.success ? `Complaint created: ${d.complaint_number}` : (d.error || 'Could not raise complaint.')));
      }
    }
  }
  function speak(text) {
    if (!('speechSynthesis' in window) || ttsCapabilities[language.value] === false) return;
    window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(text);
    const langMap={English:'en-IN',Hindi:'hi-IN',Bengali:'bn-IN',Tamil:'ta-IN',Telugu:'te-IN',Marathi:'mr-IN',Gujarati:'gu-IN',Kannada:'kn-IN',Malayalam:'ml-IN',Punjabi:'pa-IN',Odia:'or-IN',Assamese:'as-IN'};
    u.lang=langMap[language.value] || 'en-IN'; voices=window.speechSynthesis.getVoices();
    const v=voices.find(x=>x.lang.toLowerCase().startsWith(u.lang.toLowerCase().slice(0,2))); if(v) u.voice=v;
    u.onstart=()=>setStatus('Speaking'); u.onend=()=>setStatus(''); window.speechSynthesis.speak(u);
  }
  async function sendMessage() {
    const text=input.value.trim(); if(!text) return; input.value=''; addMessage(text,'user'); setStatus('Understanding…');
    try {
      const r=await fetch('/api/chat/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,language:language.value})});
      const d=await r.json(); if(!r.ok) throw new Error(d.error||'Chat failed');
      addMessage(d.reply || 'I could not generate a response.', 'bot', d.action); speak(d.reply || '');
    } catch(e) { addMessage('The assistant is temporarily unavailable. Please try again or use the scheme search.', 'bot'); }
    finally { setStatus(''); }
  }
  fab.onclick=()=>panel.classList.toggle('open'); close.onclick=()=>panel.classList.remove('open');
  clear.onclick=()=>{messages.innerHTML=''; addMessage('Chat cleared. What would you like to do?');};
  send.onclick=sendMessage; input.addEventListener('keydown',e=>{if(e.key==='Enter')sendMessage();});
  language.addEventListener('change',()=>localStorage.setItem('smartgov-chat-language',language.value));
  const saved=localStorage.getItem('smartgov-chat-language'); if(saved) language.value=saved;

  fetch('/api/chat/languages').then(r=>r.json()).then(d=>{ voiceCapabilities=d.voice_supported||{}; ttsCapabilities=d.tts_supported||{}; updateMicCapability(); }).catch(()=>{});
  function updateMicCapability(){ if(!mic) return; if(voiceCapabilities[language.value]===false){mic.disabled=true; mic.title='Voice input is unavailable for this language with the configured provider. Use text chat instead.';} else if(recognition){mic.disabled=false; mic.title='Voice input';} }

  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(SR){
    recognition=new SR(); recognition.interimResults=false; recognition.continuous=false;
    mic.onclick=()=>{ if(voiceCapabilities[language.value]===false) return; if(mic.dataset.listening==='1') return; recognition.lang=({English:'en-IN',Hindi:'hi-IN',Bengali:'bn-IN',Tamil:'ta-IN',Telugu:'te-IN',Marathi:'mr-IN',Gujarati:'gu-IN',Kannada:'kn-IN',Malayalam:'ml-IN',Punjabi:'pa-IN',Odia:'or-IN',Assamese:'as-IN'})[language.value]||'en-IN'; mic.dataset.listening='1'; setStatus('Listening…'); try{recognition.start();}catch(e){} };
    recognition.onresult=e=>{input.value=e.results[0][0].transcript;setStatus('Transcribed');sendMessage();};
    recognition.onerror=()=>{setStatus('Microphone/voice service unavailable. You can type instead.');mic.dataset.listening='0';}; recognition.onend=()=>{mic.dataset.listening='0'; if(status.textContent==='Listening…')setStatus('');};
  } else { mic.disabled=true; mic.title='Voice input is not supported by this browser.'; }
  language.addEventListener('change', updateMicCapability);
})();
