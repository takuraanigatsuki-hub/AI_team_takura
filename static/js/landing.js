/** Landing page — вход, регистрация, скачивание, таб-навигация */
(function () {
    let mode = 'login';
    let currentUser = null;
    let downloadUrl = '/api/downloads/desktop/win/setup';
    let portableUrl = '/api/downloads/desktop/win/portable';
    let activeTab = 'home';

    const TAB_ALIASES = {
        capabilities: 'platform',
        pricing: 'download',
        figma: 'how',
        demo: 'how',
        start: 'download',
    };

    const modal = document.getElementById('authModal');
    const form = document.getElementById('authForm');
    const errorEl = document.getElementById('authError');

    function resolveTab(id) {
        const key = (id || 'home').toLowerCase();
        return TAB_ALIASES[key] || key;
    }

    function tabExists(id) {
        return !!document.querySelector(`[data-lp-panel="${id}"]`);
    }

    function switchTab(tabId, opts) {
        const tab = resolveTab(tabId);
        if (!tabExists(tab)) return;
        activeTab = tab;

        document.querySelectorAll('[data-lp-panel]').forEach((panel) => {
            const on = panel.dataset.lpPanel === tab;
            panel.classList.toggle('active', on);
            panel.hidden = !on;
        });

        document.querySelectorAll('[data-lp-tab]').forEach((btn) => {
            const on = btn.dataset.lpTab === tab;
            btn.classList.toggle('active', on);
            if (btn.tagName === 'BUTTON') btn.setAttribute('aria-current', on ? 'page' : 'false');
        });

        const path = tab === 'home' ? '/' : `/#${tab}`;
        if (!opts?.silent && location.pathname + location.hash !== path && (tab !== 'home' || location.hash)) {
            history.replaceState({ lpTab: tab }, '', path);
        }

        document.getElementById('lpNav')?.classList.remove('open');
        document.getElementById('lpNavToggle')?.setAttribute('aria-expanded', 'false');
        window.scrollTo({ top: 0, behavior: opts?.instant ? 'auto' : 'smooth' });

        if (tab === 'how' && opts?.playDemo) {
            setTimeout(() => window.LandingDemo?.playGuidedDemo?.(), 400);
        }
    }

    function initTabsFromUrl() {
        const hash = (location.hash || '').replace(/^#/, '');
        if (hash && tabExists(resolveTab(hash))) {
            switchTab(hash, { silent: true, instant: true });
        } else {
            switchTab('home', { silent: true, instant: true });
        }
    }

    document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-lp-tab]');
        if (!trigger) return;
        if (trigger.tagName === 'A' && trigger.getAttribute('href')?.startsWith('/api/')) return;
        e.preventDefault();
        const playDemo = trigger.dataset.lpTab === 'how' && trigger.classList.contains('lp-play-demo');
        switchTab(trigger.dataset.lpTab, { playDemo });
    });

    window.addEventListener('hashchange', () => {
        const hash = (location.hash || '').replace(/^#/, '');
        if (hash) switchTab(hash, { silent: true });
        else switchTab('home', { silent: true });
    });

    window.addEventListener('keydown', (e) => {
        if (e.target.closest('input, textarea, select') || modal?.classList.contains('hidden') === false) return;
        const map = {
            '1': 'home', '2': 'features', '3': 'platform', '4': 'how',
            '5': 'team', '6': 'integrations', '7': 'download',
        };
        if (map[e.key]) {
            e.preventDefault();
            switchTab(map[e.key], { playDemo: e.key === '4' && e.shiftKey });
        }
    });

    function openModal(m) {
        mode = m || 'login';
        updateModalUI();
        modal.classList.remove('hidden');
        document.body.classList.add('lp-modal-open');
        (mode === 'register' ? document.getElementById('authEmail') : document.getElementById('authLogin'))?.focus();
    }

    function closeModal() {
        modal.classList.add('hidden');
        document.body.classList.remove('lp-modal-open');
        errorEl.classList.add('hidden');
        form.reset();
        window.AuthFields?.clearFieldState(document.getElementById('authUsername'), document.getElementById('authUsernameHint'));
        window.AuthFields?.clearFieldState(document.getElementById('authName'), document.getElementById('authNameHint'));
    }

    function updateModalUI() {
        const isReg = mode === 'register';
        document.getElementById('authTitle').textContent = isReg ? 'Регистрация' : 'Вход';
        document.getElementById('authSub').textContent = isReg
            ? 'Создайте аккаунт — откроется мастер первой настройки'
            : 'Войдите по email или логину';
        document.getElementById('authSubmit').textContent = isReg ? 'Создать аккаунт' : 'Войти';
        document.getElementById('loginLabel').style.display = isReg ? 'none' : 'block';
        document.getElementById('authLogin').style.display = isReg ? 'none' : 'block';
        document.getElementById('authLogin').required = !isReg;
        document.getElementById('emailLabel').style.display = isReg ? 'block' : 'none';
        document.getElementById('authEmail').style.display = isReg ? 'block' : 'none';
        document.getElementById('authEmail').required = isReg;
        document.getElementById('usernameLabel').style.display = isReg ? 'block' : 'none';
        document.getElementById('authUsername').style.display = isReg ? 'block' : 'none';
        document.getElementById('authUsername').required = isReg;
        document.getElementById('nameLabel').style.display = isReg ? 'block' : 'none';
        document.getElementById('authName').style.display = isReg ? 'block' : 'none';
        document.getElementById('authName').required = isReg;
        document.getElementById('authUsernameHint').style.display = isReg ? 'block' : 'none';
        document.getElementById('authNameHint').style.display = isReg ? 'block' : 'none';
        document.getElementById('authSwitchText').textContent = isReg ? 'Уже есть аккаунт?' : 'Нет аккаунта?';
        document.getElementById('authSwitch').textContent = isReg ? 'Войти' : 'Зарегистрироваться';
    }

    function applyDownloadLinks(setupUrl, portUrl) {
        downloadUrl = setupUrl || downloadUrl;
        portableUrl = portUrl || portableUrl;
        document.querySelectorAll(
            '#lpBtnDownload, #lpBtnDownloadUser, #lpSectionDownload, #lpCtaDownload'
        ).forEach((el) => { if (el) el.setAttribute('href', downloadUrl); });
        const portable = document.getElementById('lpPortableDownload');
        if (portable) portable.setAttribute('href', portableUrl);
    }

    function parseAuthError(d, fallback) {
        const detail = d?.detail;
        if (typeof detail === 'string') return detail;
        if (Array.isArray(detail)) return detail.map((x) => x.msg || String(x)).join(', ');
        return fallback || 'Ошибка';
    }

    function canSeeAdmin(user) {
        if (!user) return false;
        return user.is_owner || user.is_admin || ['owner', 'admin', 'tech_admin'].includes(user.role);
    }

    function updateFooter(user) {
        const supportBtn = document.getElementById('lpFooterSupport');
        const cabBtn = document.getElementById('lpFooterCabinetBtn');
        const cabLink = document.getElementById('lpFooterCabinetLink');
        const adminLink = document.getElementById('lpFooterAdmin');

        supportBtn?.classList.remove('hidden');
        if (user) {
            cabBtn?.classList.add('hidden');
            cabLink?.classList.remove('hidden');
            adminLink?.classList.toggle('hidden', !canSeeAdmin(user));
        } else {
            cabBtn?.classList.remove('hidden');
            cabLink?.classList.add('hidden');
            adminLink?.classList.add('hidden');
        }
    }

    async function initDownloadLinks() {
        try {
            const r = await fetch('/api/downloads/desktop/info');
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const info = await r.json();
            const setup = info.platforms?.find((p) => p.id === 'win-setup' && p.url);
            const portable = info.platforms?.find((p) => p.id === 'win-portable' && p.url);
            applyDownloadLinks(
                (setup || portable)?.url || downloadUrl,
                portable?.url || portableUrl
            );
            const meta = document.getElementById('lpDlMeta');
            if (meta && setup?.size_mb) meta.textContent = `WebView2 · .NET 8 · ~${setup.size_mb} MB`;
        } catch (_) {
            applyDownloadLinks(downloadUrl, portableUrl);
        }
    }

    function showGuestUI() {
        currentUser = null;
        document.getElementById('lpAuthGuest')?.classList.remove('hidden');
        document.getElementById('lpAuthUser')?.classList.add('hidden');
        document.getElementById('lpHeroCtaGuest')?.classList.remove('hidden');
        document.getElementById('lpHeroCtaUser')?.classList.add('hidden');
        document.getElementById('lpDlGuest')?.classList.remove('hidden');
        document.getElementById('lpDlUser')?.classList.add('hidden');
        updateFooter(null);
    }

    function showUserUI(user) {
        currentUser = user;
        document.getElementById('lpAuthGuest')?.classList.add('hidden');
        document.getElementById('lpAuthUser')?.classList.remove('hidden');
        document.getElementById('lpHeroCtaGuest')?.classList.add('hidden');
        document.getElementById('lpHeroCtaUser')?.classList.remove('hidden');
        document.getElementById('lpDlGuest')?.classList.add('hidden');
        document.getElementById('lpDlUser')?.classList.remove('hidden');
        updateFooter(user);

        const name = user.name || user.email?.split('@')[0] || 'Пользователь';
        const pill = document.getElementById('lpUserPill');
        if (pill) {
            const tierLabel = user.is_owner
                ? (user.role_label || 'Владелец')
                : (user.subscription?.tier_name || '');
            const tierEmoji = user.subscription?.tier_emoji || '';
            const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
            const tierClass = user.is_owner ? ' lp-user-pill-tier--owner' : '';
            pill.innerHTML = `
                <span class="lp-user-pill-name" title="${esc(name)}">👤 ${esc(name)}</span>
                ${tierLabel ? `<span class="lp-user-pill-tier${tierClass}" title="${esc(tierLabel)}">${tierEmoji} ${esc(tierLabel)}</span>` : ''}`;
        }
    }

    async function initAuth() {
        try {
            const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
            if (r.ok) {
                const user = await r.json();
                showUserUI(user);
                return user;
            }
        } catch (_) { /* guest */ }
        showGuestUI();
        return null;
    }

    async function logout() {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
        showGuestUI();
    }

    function goCabinet() {
        if (currentUser) location.href = '/portal?view=profile';
        else openModal('login');
    }

    document.getElementById('btnLogin')?.addEventListener('click', () => openModal('login'));
    document.getElementById('btnRegister')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnHeroStart')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnCtaRegister')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnCtaLogin')?.addEventListener('click', () => openModal('login'));
    document.getElementById('btnHeroCabinet')?.addEventListener('click', goCabinet);
    document.getElementById('btnDlCabinet')?.addEventListener('click', goCabinet);
    document.getElementById('lpFooterCabinetBtn')?.addEventListener('click', goCabinet);
    document.getElementById('lpFooterSupport')?.addEventListener('click', () => global.SupportTickets?.open?.({ landing: true }));
    document.getElementById('btnLogout')?.addEventListener('click', logout);
    document.getElementById('authClose')?.addEventListener('click', closeModal);
    document.getElementById('authBackdrop')?.addEventListener('click', closeModal);
    document.getElementById('authSwitch')?.addEventListener('click', () => {
        mode = mode === 'login' ? 'register' : 'login';
        updateModalUI();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) closeModal();
    });

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.classList.add('hidden');
        const password = document.getElementById('authPassword').value;
        const url = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
        let body;
        if (mode === 'register') {
            const email = document.getElementById('authEmail').value.trim();
            const username = document.getElementById('authUsername').value.trim();
            const name = document.getElementById('authName').value.trim();
            if (!window.AuthFields?.fieldsAvailable(
                document.getElementById('authUsername'),
                document.getElementById('authName')
            )) {
                errorEl.textContent = 'Исправьте логин или имя — они уже заняты';
                errorEl.classList.remove('hidden');
                return;
            }
            body = { email, password, name, username };
        } else {
            body = { login: document.getElementById('authLogin').value.trim(), password };
        }

        const submitBtn = document.getElementById('authSubmit');
        if (submitBtn) submitBtn.disabled = true;
        try {
            const r = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(parseAuthError(d, 'Ошибка'));

            const next = new URLSearchParams(location.search).get('next');
            if (next && next.startsWith('/')) {
                location.href = next;
                return;
            }

            if (mode === 'login') {
                closeModal();
                showUserUI(d.user || d);
                return;
            }
            location.href = '/portal?setup=1';
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });

    const params = new URLSearchParams(location.search);
    initTabsFromUrl();
    initDownloadLinks();
    initAuth().then((user) => {
        if (user && !params.get('auth')) {
            closeModal();
        } else if (!user && params.get('auth') === 'login') {
            openModal('login');
            history.replaceState({}, '', location.pathname + location.hash);
        } else if (!user && params.get('auth') === 'register') {
            openModal('register');
            history.replaceState({}, '', location.pathname + location.hash);
        }
        if (window.LandingDemo) LandingDemo.init();
    });

    const navToggle = document.getElementById('lpNavToggle');
    const nav = document.getElementById('lpNav');
    navToggle?.addEventListener('click', () => {
        const open = nav?.classList.toggle('open');
        navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    window.LandingTabs = { switchTab, active: () => activeTab };
    window.LandingAuth = { openLogin: () => openModal('login'), openRegister: () => openModal('register') };

    if (window.AuthFields) {
        AuthFields.bindUsernameCheck(document.getElementById('authUsername'), document.getElementById('authUsernameHint'));
        AuthFields.bindNameCheck(document.getElementById('authName'), document.getElementById('authNameHint'));
    }
})();
