/**
 * Sidebar navigation — role-based (guest / member / admin)
 */
(function (global) {
    const NAV_GUEST = [
        { group: 'Inbox', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Ещё', items: [
            { view: 'studio', icon: '🎮', label: '3D Студия' },
        ]},
    ];

    const NAV_MEMBER = [
        { group: 'Inbox', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Обзор', items: [
            { view: 'dashboard', icon: '📊', label: 'Dashboard' },
            { view: 'projects', icon: '📦', label: 'Проекты' },
        ]},
        { group: 'Планирование', items: [
            { view: 'sprint', icon: '🏃', label: 'Sprint' },
            { view: 'timeline', icon: '⏱', label: 'Timeline' },
        ]},
        { group: 'Студия', advanced: true, items: [
            { view: 'studio', icon: '🎮', label: '3D' },
            { view: 'sonya-studio', icon: '✨', label: 'Studio' },
        ]},
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет' },
        ]},
    ];

    const NAV_ADMIN = [
        { group: 'Inbox', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Обзор', items: [
            { view: 'dashboard', icon: '📊', label: 'Dashboard' },
            { view: 'projects', icon: '📦', label: 'Проекты' },
            { view: 'sprint', icon: '🏃', label: 'Sprint' },
            { view: 'timeline', icon: '⏱', label: 'Timeline' },
        ]},
        { group: 'Студия', items: [
            { view: 'studio', icon: '🎮', label: '3D' },
            { view: 'sonya-studio', icon: '✨', label: 'Studio' },
        ]},
        { group: 'Advanced', advanced: true, items: [
            { view: 'agent-learning', icon: '🔬', label: 'Обучение', adminLearning: true },
            { view: 'admin', icon: '🛡', label: 'Admin', admin: true },
        ]},
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет' },
        ]},
    ];

    const NAV_INVESTOR = [
        { group: 'Inbox', items: [
            { view: 'investor', icon: '💼', label: 'Investor', primary: true },
            { view: 'profile', icon: '👤', label: 'Кабинет' },
        ]},
        { group: 'Просмотр', items: [
            { view: 'studio', icon: '🎮', label: '3D' },
            { view: 'dashboard', icon: '📊', label: 'Dashboard' },
        ]},
    ];

    function getNav(user) {
        const mode = global.UICore?.getUiMode?.(user) || 'guest';
        if (mode === 'guest') return NAV_GUEST;
        if (mode === 'investor') return NAV_INVESTOR;
        if (mode === 'admin') return NAV_ADMIN;
        return NAV_MEMBER;
    }

    function isMobileNav() {
        return window.matchMedia('(max-width: 900px)').matches;
    }

    function openMobileSidebar() {
        document.body.classList.add('sidebar-open');
        document.getElementById('sidebarOverlay')?.classList.remove('hidden');
        document.getElementById('mobileNavToggle')?.setAttribute('aria-expanded', 'true');
    }

    function closeMobileSidebar() {
        document.body.classList.remove('sidebar-open');
        document.getElementById('sidebarOverlay')?.classList.add('hidden');
        document.getElementById('mobileNavToggle')?.setAttribute('aria-expanded', 'false');
    }

    function canShow(item, user) {
        if (item.admin && !global.Auth?.canAccessAdmin?.(user)) return false;
        if (item.adminLearning && !global.Auth?.canViewAgentLearning?.(user)) return false;
        if (item.role === 'investor') {
            if (!user) return false;
            return user.is_investor || user.can_view_investor_portal || global.Auth?.canAccessAdmin?.(user);
        }
        if (user?.role === 'investor' || user?.is_investor) {
            if (!['investor', 'profile', 'studio', 'dashboard'].includes(item.view)) return false;
        }
        if (user && global.ProfileCabinet?.canAccessView && !ProfileCabinet.canAccessView(user, item.view)) {
            if (!['profile', 'tasks', 'chat', 'kanban', 'studio'].includes(item.view)) return false;
        }
        return true;
    }

    function render() {
        const el = document.getElementById('appSidebarNav');
        if (!el) return;
        const user = global.Auth?.getUser?.();
        const NAV = getNav(user);
        el.innerHTML = NAV.map((g) => {
            const items = g.items.filter((i) => canShow(i, user));
            if (!items.length) return '';
            const adv = g.advanced ? ' sb-group-advanced' : '';
            return `<div class="sb-group${adv}"><div class="sb-group-label">${g.group}</div>${items.map((i) =>
                `<button type="button" class="sb-item${i.primary ? ' sb-primary' : ''}" data-view="${i.view}" onclick="SidebarNav.onNavClick('${i.view}')" title="${i.label}">
                    <span class="sb-icon">${i.icon}</span><span class="sb-label">${i.label}</span>
                </button>`).join('')}</div>`;
        }).join('');
    }

    function onNavClick(view) {
        if (isMobileNav()) closeMobileSidebar();
        if (typeof global.switchView === 'function') global.switchView(view);
    }

    function setActive(view) {
        document.querySelectorAll('.sb-item[data-view]').forEach((b) => {
            b.classList.toggle('active', b.dataset.view === view || (view === 'learning' && b.dataset.view === 'agent-learning'));
        });
        if (global.UICore) UICore.setMobileTabActive(view);
    }

    function updateBadges(counts = {}) {
        document.querySelectorAll('.sb-item[data-view="tasks"] .sb-badge').forEach((b) => b.remove());
        const n = counts.awaiting || 0;
        if (n > 0) {
            const btn = document.querySelector('.sb-item[data-view="tasks"]');
            if (btn) {
                const badge = document.createElement('span');
                badge.className = 'sb-badge';
                badge.textContent = n > 99 ? '99+' : String(n);
                badge.title = 'Ждут вашего решения';
                btn.appendChild(badge);
            }
        }
        if (global.UICore) UICore.updateMobileBadges?.(n);
    }

    function setDensity(mode) {
        document.documentElement.setAttribute('data-density', mode);
        localStorage.setItem('ai-team-density', mode);
    }

    function initDensity() {
        const saved = localStorage.getItem('ai-team-density') || 'comfortable';
        setDensity(saved);
        document.getElementById('densitySelect')?.addEventListener('change', (e) => setDensity(e.target.value));
    }

    function toggleSidebar() {
        if (isMobileNav()) {
            if (document.body.classList.contains('sidebar-open')) closeMobileSidebar();
            else openMobileSidebar();
            return;
        }
        document.body.classList.toggle('sidebar-collapsed');
        localStorage.setItem('ai-team-sidebar-collapsed', document.body.classList.contains('sidebar-collapsed') ? '1' : '');
    }

    function init() {
        if (localStorage.getItem('ai-team-sidebar-collapsed') === '1') {
            document.body.classList.add('sidebar-collapsed');
        }
        initDensity();
        render();
        document.getElementById('sidebarToggle')?.addEventListener('click', toggleSidebar);
        document.getElementById('mobileNavToggle')?.addEventListener('click', toggleSidebar);
        document.getElementById('sidebarOverlay')?.addEventListener('click', closeMobileSidebar);
        window.addEventListener('resize', () => {
            if (!isMobileNav()) closeMobileSidebar();
        });
    }

    global.SidebarNav = { render, setActive, init, setDensity, onNavClick, closeMobileSidebar, updateBadges, getNav };
    document.addEventListener('DOMContentLoaded', init);
})(window);
