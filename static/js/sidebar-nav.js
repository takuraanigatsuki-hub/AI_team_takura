/**
 * Sidebar navigation — role-based (guest / member / admin / investor)
 * Структура вдохновлена Snow Dashboard UI Kit
 */
(function (global) {
    const NAV_GUEST = [
        { group: 'Работа', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Студия', items: [
            { view: 'studio', icon: '🎮', label: '3D Студия' },
        ]},
    ];

    const NAV_MEMBER = [
        { group: 'Работа', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Аналитика', items: [
            { view: 'dashboard', icon: '📊', label: 'Dashboard' },
            { view: 'projects', icon: '📦', label: 'Проекты' },
            { view: 'timeline', icon: '⏱', label: 'Timeline' },
        ]},
        { group: 'Планирование', items: [
            { view: 'sprint', icon: '🏃', label: 'Sprint' },
        ]},
        { group: 'Студия', advanced: true, items: [
            { view: 'studio', icon: '🎮', label: '3D' },
            { view: 'sonya-studio', icon: '✨', label: 'Sonya Studio' },
        ]},
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет' },
            { view: 'investor', icon: '💼', label: 'Investor', investor: true },
        ]},
    ];

    const NAV_SUPPORT = [
        { group: 'Поддержка', items: [
            { view: 'support', icon: '💬', label: 'Тикеты', primary: true, supportPanel: true },
        ]},
        { group: 'Работа', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox' },
            { view: 'chat', icon: '💬', label: 'Чат' },
        ]},
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет' },
        ]},
    ];

    const NAV_ADMIN = [
        { group: 'Работа', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Аналитика', items: [
            { view: 'dashboard', icon: '📊', label: 'Dashboard' },
            { view: 'projects', icon: '📦', label: 'Проекты' },
            { view: 'timeline', icon: '⏱', label: 'Timeline' },
        ]},
        { group: 'Планирование', items: [
            { view: 'sprint', icon: '🏃', label: 'Sprint' },
        ]},
        { group: 'Студия', items: [
            { view: 'studio', icon: '🎮', label: '3D' },
            { view: 'sonya-studio', icon: '✨', label: 'Sonya Studio' },
            { view: 'design', icon: '🎨', label: 'Design Lab', adminLearning: true },
        ]},
        { group: 'Система', advanced: true, items: [
            { view: 'support', icon: '💬', label: 'Поддержка', supportPanel: true },
            { view: 'agent-learning', icon: '🔬', label: 'Обучение', adminLearning: true },
            { view: 'admin', icon: '🛡', label: 'Admin', admin: true },
            { view: 'investor', icon: '💼', label: 'Investor', investor: true },
        ]},
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет' },
        ]},
    ];

    const NAV_INVESTOR = [
        { group: 'Обзор', items: [
            { view: 'investor', icon: '💼', label: 'Investor', primary: true },
            { view: 'dashboard', icon: '📊', label: 'Dashboard' },
        ]},
        { group: 'Просмотр', items: [
            { view: 'studio', icon: '🎮', label: '3D' },
            { view: 'projects', icon: '📦', label: 'Проекты' },
        ]},
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет' },
        ]},
    ];

    function getNav(user) {
        const mode = global.UICore?.getUiMode?.(user) || 'guest';
        if (mode === 'guest') return NAV_GUEST;
        if (mode === 'investor') return NAV_INVESTOR;
        if (mode === 'support') return NAV_SUPPORT;
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
        if (item.supportPanel && !global.Auth?.canManageTickets?.(user) && !user?.is_support) return false;
        if (item.adminLearning && !global.Auth?.canViewAgentLearning?.(user)) return false;
        if (item.investor && !global.Auth?.canViewInvestorPortal?.(user)) return false;
        if (item.role === 'investor') {
            if (!user) return false;
            return user.is_investor || user.can_view_investor_portal || global.Auth?.canAccessAdmin?.(user);
        }
        if (user?.role === 'investor' || user?.is_investor) {
            if (!['investor', 'profile', 'studio', 'dashboard', 'projects'].includes(item.view)) return false;
        }
        if (user && global.ProfileCabinet?.canAccessView && !ProfileCabinet.canAccessView(user, item.view)) {
            if (!['profile', 'tasks', 'chat', 'kanban', 'studio'].includes(item.view)) return false;
        }
        return true;
    }

    function renderItem(i) {
        if (i.action === 'search') {
            return `<button type="button" class="sb-item sb-action" onclick="FeaturePack?.openGlobalSearch?.()" title="Поиск">
                <span class="sb-icon">${i.icon}</span><span class="sb-label">${i.label}</span></button>`;
        }
        if (i.action === 'commands') {
            return `<button type="button" class="sb-item sb-action" onclick="FeaturePack?.openCommandPalette?.()" title="Команды">
                <span class="sb-icon">${i.icon}</span><span class="sb-label">${i.label}</span></button>`;
        }
        return `<button type="button" class="sb-item${i.primary ? ' sb-primary' : ''}" data-view="${i.view}" onclick="SidebarNav.onNavClick('${i.view}')" title="${i.label}">
            <span class="sb-icon">${i.icon}</span><span class="sb-label">${i.label}</span>
        </button>`;
    }

    function render() {
        const el = document.getElementById('appSidebarNav');
        if (!el) return;
        const user = global.Auth?.getUser?.();
        const NAV = getNav(user);
        const quickBar = `<div class="sb-quick">
            <button type="button" class="sb-quick-btn sb-quick-unified" onclick="FeaturePack?.openCommandPalette?.()" title="Разделы, команды и поиск — Ctrl+K">
                <span class="sb-quick-icon" aria-hidden="true">⌘</span>
                <span class="sb-quick-label">Быстрый доступ</span>
                <kbd class="sb-quick-kbd">K</kbd>
            </button>
        </div>`;
        el.innerHTML = quickBar + NAV.map((g) => {
            const items = g.items.filter((i) => canShow(i, user));
            if (!items.length) return '';
            const adv = g.advanced ? ' sb-group-advanced' : '';
            return `<div class="sb-group${adv}"><div class="sb-group-label">${g.group}</div>${items.map(renderItem).join('')}</div>`;
        }).join('');
    }

    function onNavClick(view) {
        if (isMobileNav()) closeMobileSidebar();
        if (typeof global.switchView === 'function') global.switchView(view);
    }

    function setActive(view) {
        document.querySelectorAll('.sb-item[data-view]').forEach((b) => {
            b.classList.toggle('active', b.dataset.view === view || (view === 'agent-learning' && b.dataset.view === 'agent-learning') || (view === 'agent-learning' && b.dataset.view === 'design'));
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

    function updateCollapseBtn() {
        const btn = document.getElementById('sidebarToggle');
        if (!btn || isMobileNav()) return;
        const collapsed = document.body.classList.contains('sidebar-collapsed');
        btn.textContent = collapsed ? '▶' : '◀';
        btn.title = collapsed ? 'Развернуть панель' : 'Свернуть панель';
        btn.setAttribute('aria-label', btn.title);
    }

    function initDensity() {
        setDensity(localStorage.getItem('ai-team-density') || 'comfortable');
    }

    function toggleSidebar() {
        if (isMobileNav()) {
            if (document.body.classList.contains('sidebar-open')) closeMobileSidebar();
            else openMobileSidebar();
            return;
        }
        document.body.classList.toggle('sidebar-collapsed');
        localStorage.setItem('ai-team-sidebar-collapsed', document.body.classList.contains('sidebar-collapsed') ? '1' : '');
        updateCollapseBtn();
    }

    function init() {
        if (localStorage.getItem('ai-team-sidebar-collapsed') === '1') {
            document.body.classList.add('sidebar-collapsed');
        }
        initDensity();
        updateCollapseBtn();
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
