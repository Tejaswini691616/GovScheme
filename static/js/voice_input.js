// PATH: GovScheme/static/js/voice_input.js
/**
 * Reusable browser-native speech-to-text helper (Web Speech API - the same
 * zero-key, zero-cost provider used by the main chatbot). Attaches a mic
 * button to any textarea/input so voice can be used anywhere in the app,
 * not just the chatbot widget - e.g. complaints, feedback.
 *
 * Usage:
 *   attachVoiceToField({
 *     buttonId: 'complaintVoiceBtn',
 *     fieldId: 'description',
 *     statusId: 'complaintVoiceStatus',
 *     localeCode: 'en-IN'   // or read from a language <select>
 *   });
 */
function attachVoiceToField(opts) {
  const btn = document.getElementById(opts.buttonId);
  const field = document.getElementById(opts.fieldId);
  const statusEl = opts.statusId ? document.getElementById(opts.statusId) : null;
  if (!btn || !field) return;

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    btn.disabled = true;
    btn.title = "Voice input isn't supported in this browser. Please type instead.";
    return;
  }

  let recognizing = false;
  btn.addEventListener('click', () => {
    if (recognizing) return;
    const localeCode = (typeof opts.getLocaleCode === 'function') ? opts.getLocaleCode() : (opts.localeCode || 'en-IN');
    if (!localeCode) {
      if (statusEl) statusEl.textContent = "Voice input isn't available for the selected language yet. Please type instead.";
      return;
    }
    const recognition = new SR();
    recognition.lang = localeCode;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      recognizing = true;
      btn.classList.add('text-danger');
      if (statusEl) statusEl.textContent = 'Listening... speak now.';
    };
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      field.value = (field.value ? field.value + ' ' : '') + transcript;
      if (statusEl) statusEl.textContent = 'Transcribed - feel free to edit before submitting.';
    };
    recognition.onerror = () => {
      if (statusEl) statusEl.textContent = "Sorry, I couldn't understand that. Please try again or type instead.";
    };
    recognition.onend = () => {
      recognizing = false;
      btn.classList.remove('text-danger');
    };

    try {
      recognition.start();
    } catch (err) {
      if (statusEl) statusEl.textContent = 'Microphone permission is required for voice input. You can continue typing.';
    }
  });
}
