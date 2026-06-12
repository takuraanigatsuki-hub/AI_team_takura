/** Auto theme по времени суток + studio lighting */
(function (global) {
    function hourTheme() {
        const h = new Date().getHours();
        return (h >= 7 && h < 19) ? 'light' : 'dark';
    }

    function apply() {
        const theme = hourTheme();
        const html = document.documentElement;
        const current = html.getAttribute('data-theme') || 'dark';
        if (current === theme) return;
        html.setAttribute('data-theme', theme);
        const btn = document.getElementById('themeToggle');
        if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
        if (window.StudioApp) StudioApp.setTheme(theme === 'dark');
        if (window.StudioApp?.setDayNight) StudioApp.setDayNight(theme === 'light');
    }

    function start() {
        apply();
        setInterval(apply, 5 * 60 * 1000);
    }

    global.AutoTheme = { start, apply, hourTheme };
})(window);
