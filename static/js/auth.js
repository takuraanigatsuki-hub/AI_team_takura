/** Auth helpers — сессия, профиль, logout */
(function (global) {
    let currentUser = null;

    async function fetchMe() {
        try {
            const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
            if (!r.ok) {
                currentUser = null;
                return null;
            }
            currentUser = await r.json();
            updateHeader();
            return currentUser;
        } catch (_) {
            currentUser = null;
            return null;
        }
    }

    function getUser() {
        return currentUser;
    }

    function isLoggedIn() {
        return !!currentUser;
    }

    async function logout() {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
        currentUser = null;
        location.href = '/';
    }

    function updateHeader() {
        const el = document.getElementById('userMenu');
        if (!el) return;
        if (!currentUser) {
            el.innerHTML = `
                <a href="/" class="hdr-btn">На сайт</a>
                <a href="/?auth=login" class="hdr-btn">Вход</a>`;
            return;
        }
        el.innerHTML = `
            <span class="user-name" title="${escape(currentUser.email)}">👤 ${escape(currentUser.name || currentUser.email)}</span>
            <button type="button" class="hdr-btn" onclick="Auth.logout()">Выход</button>
            <a href="/" class="hdr-btn hdr-icon user-home" title="Главный сайт">🏠</a>`;
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.Auth = { fetchMe, getUser, isLoggedIn, logout, updateHeader };
})(window);
