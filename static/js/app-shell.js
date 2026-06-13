/**
 * App shell — разделение workspace (/workspace) и portal (/portal)
 */
(function (global) {
    const PORTAL_VIEWS = new Set(['profile', 'admin', 'support']);

    function getShell() {
        return global.APP_SHELL || 'workspace';
    }

    function isPortal() {
        return getShell() === 'portal';
    }

    function urlForView(view) {
        if (PORTAL_VIEWS.has(view)) {
            if (view === 'profile') return '/portal?view=profile';
            return `/portal?view=${encodeURIComponent(view)}`;
        }
        if (!view || view === 'tasks') return '/workspace';
        return `/workspace?view=${encodeURIComponent(view)}`;
    }

    function redirectIfCrossShell(view) {
        const shell = getShell();
        if (shell === 'workspace' && PORTAL_VIEWS.has(view)) {
            global.location.href = urlForView(view);
            return true;
        }
        if (shell === 'portal' && !PORTAL_VIEWS.has(view)) {
            global.location.href = urlForView(view);
            return true;
        }
        return false;
    }

    function navTo(view) {
        if (redirectIfCrossShell(view)) return;
        if (typeof global.switchView === 'function') global.switchView(view);
    }

    global.AppShell = { getShell, isPortal, urlForView, redirectIfCrossShell, navTo, PORTAL_VIEWS };
})(window);
