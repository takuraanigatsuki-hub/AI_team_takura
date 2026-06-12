/**
 * Глобальный поиск по сайту — задачи, проекты, чат, обучение, Sonya Studio
 */
(function (global) {
    const TYPE_LABELS = {
        task: '📋 Задача',
        project: '📦 Проект',
        message: '💬 Чат',
        learning: '📚 Обучение',
        sonya: '✨ Studio',
    };

    let debounceTimer = null;
    let activeController = null;

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function close() {
        document.getElementById('siteSearchOverlay')?.remove();
    }

    function navigate(result) {
        close();
        if (!result?.view) return;
        switchView(result.view);
        if (result.view === 'chat' && result.title) {
            const inp = document.getElementById('chatSearch');
            if (inp) {
                inp.value = result.title.slice(0, 40);
                if (window.filterChatMessages) filterChatMessages(inp.value);
            }
        }
        if (result.view === 'learning' && result.title) {
            const inp = document.getElementById('learningSearch');
            if (inp) {
                inp.value = result.title.slice(0, 40);
                if (window.filterLearningMessages) filterLearningMessages(inp.value);
            }
        }
        if (result.view === 'tasks' && result.title) {
            const inp = document.getElementById('tasksSearch');
            if (inp) {
                inp.value = result.title.slice(0, 40);
                if (window.filterTasksSearch) filterTasksSearch(inp.value);
            }
        }
        if (result.view === 'projects' && result.title) {
            const inp = document.getElementById('projectsSearch');
            if (inp) {
                inp.value = result.title.slice(0, 40);
                if (window.ProjectsUI?.setSearch) ProjectsUI.setSearch(inp.value);
            }
        }
        if (result.view === 'sonya-studio' && result.id && window.SonyaStudio?.openProject) {
            SonyaStudio.openProject(result.id);
        }
        if (window.UIEnhancements) UIEnhancements.toast(`→ ${TYPE_LABELS[result.type] || result.view}`, 'info', 2500);
    }

    function renderResults(listEl, results, query) {
        if (!listEl) return;
        if (!query || query.trim().length < 2) {
            listEl.innerHTML = '<div class="search-hint">Введите минимум 2 символа</div>';
            return;
        }
        if (!results.length) {
            listEl.innerHTML = `<div class="search-hint">Ничего не найдено по «${esc(query)}»</div>`;
            return;
        }
        listEl.innerHTML = results.map((r, i) => `
            <button type="button" class="search-result" data-i="${i}">
                <span class="search-result-type">${TYPE_LABELS[r.type] || r.type}</span>
                <span class="search-result-title">${esc(r.title)}</span>
                ${r.snippet ? `<span class="search-result-snippet">${esc(r.snippet)}</span>` : ''}
                ${r.meta ? `<span class="search-result-meta">${esc(r.meta)}</span>` : ''}
            </button>`).join('');
        listEl.querySelectorAll('.search-result').forEach((btn) => {
            btn.onclick = () => navigate(results[+btn.dataset.i]);
        });
    }

    async function runSearch(query, listEl) {
        if (activeController) activeController.abort();
        activeController = new AbortController();
        listEl.innerHTML = global.UICore
            ? `<div class="search-hint">${UICore.loadingState('Поиск…')}</div>`
            : '<div class="search-hint dash-loading">Поиск…</div>';
        try {
            const r = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=30`, {
                credentials: 'same-origin',
                signal: activeController.signal,
            });
            if (r.status === 401) {
                listEl.innerHTML = '<div class="search-hint">Войдите, чтобы искать по своим задачам и сообщениям</div>';
                return;
            }
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const d = await r.json();
            renderResults(listEl, d.results || [], query);
        } catch (e) {
            if (e.name !== 'AbortError') {
                listEl.innerHTML = `<div class="search-hint search-error">${esc(e.message)}</div>`;
            }
        }
    }

    function open(prefill = '') {
        close();
        const overlay = document.createElement('div');
        overlay.id = 'siteSearchOverlay';
        overlay.className = 'site-search-overlay';
        overlay.onclick = (e) => { if (e.target === overlay) close(); };
        overlay.innerHTML = `
            <div class="site-search-panel" role="dialog" aria-label="Поиск по сайту">
                <div class="site-search-head">
                    <span aria-hidden="true">🔍</span>
                    <input type="search" id="siteSearchInput" placeholder="Поиск задач, проектов, сообщений…" autocomplete="off">
                    <kbd class="search-kbd">Esc</kbd>
                </div>
                <div class="search-results" id="siteSearchResults">
                    <div class="search-hint">Введите минимум 2 символа</div>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        const input = overlay.querySelector('#siteSearchInput');
        const listEl = overlay.querySelector('#siteSearchResults');
        input.value = prefill;
        input.focus();
        if (prefill.trim().length >= 2) runSearch(prefill.trim(), listEl);

        input.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const q = input.value.trim();
            debounceTimer = setTimeout(() => runSearch(q, listEl), 220);
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') close();
            if (e.key === 'Enter') {
                const first = listEl.querySelector('.search-result');
                if (first) first.click();
            }
        });
    }

    function bindKeyboard() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'f') {
                e.preventDefault();
                open();
            }
        });
    }

    function init() {
        bindKeyboard();
    }

    global.SiteSearch = { open, close, init };
})(window);
