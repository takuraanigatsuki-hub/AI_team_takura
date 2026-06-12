/** Звуки и haptic feedback */
(function (global) {
    let enabled = localStorage.getItem('soundEnabled') !== 'false';
    let ctx = null;

    function ac() {
        if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
        return ctx;
    }

    function tone(freq, dur, type = 'sine', vol = 0.08) {
        if (!enabled) return;
        try {
            const c = ac();
            const o = c.createOscillator();
            const g = c.createGain();
            o.type = type;
            o.frequency.value = freq;
            g.gain.value = vol;
            o.connect(g);
            g.connect(c.destination);
            o.start();
            g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + dur);
            o.stop(c.currentTime + dur);
        } catch (_) {}
    }

    function vibrate(ms) {
        if (navigator.vibrate) navigator.vibrate(ms);
    }

    global.SoundFX = {
        taskDone() { tone(880, 0.12); tone(1100, 0.15, 'sine', 0.06); vibrate(40); },
        gitPush() { tone(520, 0.1); tone(780, 0.18, 'triangle', 0.07); vibrate([30, 40, 30]); },
        connect() { tone(660, 0.08, 'sine', 0.05); },
        deploy() { tone(440, 0.1); tone(660, 0.1); tone(880, 0.2, 'sine', 0.07); vibrate(50); },
        pipelineDone() { tone(523, 0.1); tone(659, 0.1); tone(784, 0.25); vibrate(60); },
        toggle() { enabled = !enabled; localStorage.setItem('soundEnabled', enabled); return enabled; },
        isEnabled: () => enabled,
    };
})(window);
