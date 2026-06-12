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
            if (window.AdminPanel) AdminPanel.updateNavVisibility(currentUser);
            updateNavVisibility(currentUser);
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

    function roleBadgeHtml(user) {
        if (!user) return '';
        const role = user.role || 'member';
        const labels = {
            owner: '👑 Владелец',
            admin: '🛡 Админ',
            tech_admin: '⚙ Тех. админ',
            support: '💬 Поддержка',
            member: '👤 Пользователь',
        };
        const cls = {
            owner: 'role-badge role-owner',
            admin: 'role-badge role-admin',
            tech_admin: 'role-badge role-tech',
            support: 'role-badge role-support',
            member: 'role-badge role-user',
        };
        const text = user.role_label || labels[role] || labels.member;
        return `<span class="${cls[role] || cls.member}" title="${escape(text)}">${labels[role] || labels.member}</span>`;
    }

    function canAccessAdmin(user) {
        if (!user) return false;
        if (user.is_owner || user.role === 'owner') return true;
        if (user.role === 'admin' || user.role === 'tech_admin') return true;
        const p = user.privileges || [];
        return p.includes('admin') || p.includes('manage_users') || p.includes('manage_settings');
    }

    function canViewAgentLearning(user) {
        if (!user) return false;
        if (user.can_view_agent_learning) return true;
        return user.role === 'owner' || user.role === 'admin' || user.role === 'tech_admin';
    }

    function updateNavVisibility(user) {
        const showAdmin = canAccessAdmin(user);
        const showLearning = canViewAgentLearning(user);
        document.getElementById('adminNavTab')?.classList.toggle('hidden', !showAdmin);
        document.getElementById('agentLearningNavTab')?.classList.toggle('hidden', !showLearning);
    }

    function updateHeader() {
        const el = document.getElementById('userMenu');
        const summary = document.getElementById('userMenuSummary');
        if (!el) return;
        if (!currentUser) {
            if (summary) summary.textContent = '👤';
            el.innerHTML = `
                <a href="/" class="dropdown-item">На сайт</a>
                <a href="/?auth=login" class="dropdown-item">Вход</a>
                <button type="button" class="dropdown-item" onclick="switchView('profile')">👤 Кабинет</button>`;
            return;
        }
        const name = escape(currentUser.name || currentUser.email.split('@')[0]);
        const sub = currentUser.subscription || {};
        const bal = sub.balance_display != null ? sub.balance_display : (sub.balance ?? '—');
        const tierShort = sub.tier_emoji ? `${sub.tier_emoji}` : '';
        const adminBtn = canAccessAdmin(currentUser)
            ? `<button type="button" class="dropdown-item" onclick="switchView('admin')">🛡 Admin</button>` : '';
        if (summary) summary.textContent = name.slice(0, 1).toUpperCase();
        el.innerHTML = `
            <div class="dropdown-section-label">${name} · ${tierShort} ${bal} кр.</div>
            <button type="button" class="dropdown-item" onclick="switchView('profile')">👤 Кабинет</button>
            ${adminBtn}
            <button type="button" class="dropdown-item" onclick="Auth.logout()">Выход</button>
            <div class="dropdown-divider"></div>
            <a href="/" class="dropdown-item">На сайт</a>`;
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.Auth = { fetchMe, getUser, isLoggedIn, logout, updateHeader, updateNavVisibility, roleBadgeHtml, canAccessAdmin, canViewAgentLearning };
})(window);
