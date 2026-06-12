/** Auth helpers — сессия, профиль, logout */
(function (global) {
    let currentUser = null;

    async function fetchMe() {
        try {
            const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
            if (!r.ok) {
                currentUser = null;
                updateHeader();
                return null;
            }
            currentUser = await r.json();
            updateHeader();
            applyUserTheme(currentUser);
            return currentUser;
        } catch (_) {
            currentUser = null;
            updateHeader();
            return null;
        }
    }

    function applyUserTheme(user) {
        if (!user?.theme || user.theme === 'auto') return;
        if (localStorage.getItem('ai-team-room-theme')) return;
        if (window.applyTheme) applyTheme(user.theme);
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
        const name = escape(currentUser.name || currentUser.email.split('@')[0]);
        const sub = currentUser.subscription || {};
        const bal = sub.balance_display != null ? sub.balance_display : (sub.balance ?? '—');
        const tierShort = sub.tier_emoji ? `${sub.tier_emoji}` : '';
        el.innerHTML = `
            <span class="hdr-balance" title="Баланс кредитов">${tierShort} ${bal} кр.</span>
            <button type="button" class="hdr-btn" onclick="switchView('profile')" title="Личный кабинет">👤 ${name}</button>
            <button type="button" class="hdr-btn" onclick="Auth.logout()">Выход</button>
            <a href="/" class="hdr-btn hdr-icon user-home" title="Главный сайт">🏠</a>`;
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.Auth = { fetchMe, getUser, isLoggedIn, logout, updateHeader };
})(window);
