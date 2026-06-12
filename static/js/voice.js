/** Voice room — TTS standup + STT для задач */
(function (global) {
    function speak(text) {
        if (!window.speechSynthesis) {
            if (window.UIEnhancements) UIEnhancements.toast('Speech API недоступен', 'warn');
            return;
        }
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = 'ru-RU';
        u.rate = 1.05;
        window.speechSynthesis.speak(u);
    }

    async function readStandup() {
        try {
            const r = await fetch('/api/standup', { credentials: 'same-origin' });
            const d = await r.json();
            const parts = (d.sections || []).map((s) => `${s.title}. ${s.items?.join('. ') || ''}`);
            speak(parts.join('. ') || d.summary || 'Standup готов');
        } catch (e) {
            if (window.UIEnhancements) UIEnhancements.toast('Standup TTS: ' + e, 'error');
        }
    }

    let recognition = null;

    function startListening(onText) {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            if (window.UIEnhancements) UIEnhancements.toast('STT недоступен в этом браузере', 'warn');
            return;
        }
        if (recognition) recognition.stop();
        recognition = new SR();
        recognition.lang = 'ru-RU';
        recognition.interimResults = false;
        recognition.onresult = (e) => {
            const text = e.results[0][0].transcript;
            if (onText) onText(text);
            else {
                const input = document.getElementById('messageInput');
                if (input) {
                    input.value = text;
                    input.focus();
                }
            }
        };
        recognition.start();
        if (window.UIEnhancements) UIEnhancements.toast('🎤 Слушаю…', 'info');
    }

    global.VoiceRoom = { speak, readStandup, startListening };
})(window);
