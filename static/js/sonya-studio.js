/**
 * Sonya Design Studio — проекты, превью, комментарии, публикация
 */
(function (global) {
    let projects = [];
    let activeId = null;
    let activeProject = null;
    let commentMode = false;
    let pendingPin = null;

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    async function parseApiError(r) {
        try {
            const d = await r.json();
            if (typeof d.detail === 'string') {
                return d.detail === 'Not Found'
                    ? 'Studio API не найден — перезапустите сервер (python main.py)'
                    : d.detail;
            }
            if (Array.isArray(d.detail)) {
                return d.detail.map((x) => x.msg || JSON.stringify(x)).join(', ');
            }
        } catch (_) { /* ignore */ }
        if (r.status === 404) return 'Studio API недоступен — перезапустите сервер';
        return r.statusText || 'Ошибка';
    }

    async function postSonyaCreate() {
        const attempts = [
            { url: '/api/sonya/studio/create', label: 'studio/create' },
            { url: '/api/sonya/projects/create-new', label: 'create-new' },
            { url: '/api/figma/studio/trigger?action=create', label: 'figma/trigger' },
        ];
        let lastErr = 'Не удалось создать проект';
        for (const { url } of attempts) {
            try {
                const r = await fetch(url, { method: 'POST', credentials: 'same-origin' });
                const d = await r.json().catch(() => ({}));
                if (!r.ok) {
                    lastErr = await parseApiError(r);
                    continue;
                }
                if (d.project?.id) return d.project;
                if (d.ok === false) {
                    lastErr = 'Соня не смогла создать проект';
                    continue;
                }
            } catch (e) {
                lastErr = e.message;
            }
        }
        throw new Error(lastErr);
    }

    function statusLabel(st) {
        return { draft: 'Черновик', review: 'На ревью', published: 'Опубликован' }[st] || st;
    }

    async function loadProjects(selectId) {
        const listEl = document.getElementById('ssProjectList');
        if (listEl) listEl.innerHTML = global.UICore ? UICore.loadingState('Загрузка…', { compact: true }) : '<div class="dash-loading">Загрузка…</div>';
        try {
            const r = await fetch('/api/sonya/projects', { credentials: 'same-origin' });
            if (r.status === 401) {
                if (listEl) {
                    listEl.innerHTML = global.UICore ? UICore.authRequiredState({
                        title: 'Studio проекты',
                        text: 'Войдите для доступа к Sonya Studio',
                    }) : '<div class="panel-empty">🔐 Войдите для Studio проектов</div>';
                }
                return;
            }
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const d = await r.json();
            projects = d.projects || [];
            renderProjectList();
            const urlProject = new URLSearchParams(location.search).get('project');
            const id = selectId || urlProject || activeId || (projects[0] && projects[0].id);
            if (id) await openProject(id);
            else clearCanvas();
        } catch (e) {
            if (listEl) {
                listEl.innerHTML = global.UICore
                    ? UICore.errorState(e.message, { retryOnclick: 'SonyaStudio.load()' })
                    : `<div class="panel-error">${esc(e.message)}</div>`;
            }
        }
    }

    function renderProjectList() {
        const el = document.getElementById('ssProjectList');
        if (!el) return;
        if (!projects.length) {
            el.innerHTML = global.UICore ? UICore.emptyState({
                icon: '✨',
                title: 'Нет проектов',
                text: 'Создайте первый дизайн-проект',
                primaryLabel: 'Новый проект',
                primaryOnclick: 'SonyaStudio.createProject()',
            }) : '<div class="panel-empty">Нет проектов.<br>Нажмите «Новый проект».</div>';
            return;
        }
        el.innerHTML = projects.map((p) => `
            <button type="button" class="ss-project-item ${p.id === activeId ? 'active' : ''}" data-id="${p.id}">
                <strong>${esc(p.title)}</strong>
                <small>${statusLabel(p.status)} · v${p.version_count || 1}${p.open_comments ? ` · 💬 ${p.open_comments}` : ''}</small>
            </button>`).join('');
        el.querySelectorAll('.ss-project-item').forEach((btn) => {
            btn.addEventListener('click', () => openProject(btn.dataset.id));
        });
    }

    async function openProject(id) {
        activeId = id;
        renderProjectList();
        try {
            const r = await fetch(`/api/sonya/projects/${id}`);
            const data = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(await parseApiError(r));
            activeProject = data;
            renderProject();
        } catch (e) {
            if (window.UIEnhancements) UIEnhancements.toast(e.message, 'error');
        }
    }

    function clearCanvas() {
        activeProject = null;
        const frame = document.getElementById('ssPreviewFrame');
        const layer = document.getElementById('ssCommentLayer');
        if (frame) frame.srcdoc = '<html><body style="margin:0;background:#0e1016;color:#888;display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui">Выберите или создайте проект</body></html>';
        if (layer) layer.innerHTML = '';
        const meta = document.getElementById('ssProjectMeta');
        if (meta) meta.innerHTML = '';
        const comments = document.getElementById('ssCommentsList');
        if (comments) comments.innerHTML = '';
        const versions = document.getElementById('ssVersionsList');
        if (versions) versions.innerHTML = '';
    }

    function renderProject() {
        if (!activeProject) return;
        const p = activeProject;
        const ver = p.current_version || {};

        const meta = document.getElementById('ssProjectMeta');
        if (meta) {
            meta.innerHTML = `
                <h2>${esc(p.title)}</h2>
                <p class="muted">${esc(p.description || ver.task || '')}</p>
                <div class="ss-badges">
                    <span class="ss-badge status-${p.status}">${statusLabel(p.status)}</span>
                    <span class="ss-badge">v${ver.version_num || 1}</span>
                    ${p.open_comments ? `<span class="ss-badge warn">💬 ${p.open_comments}</span>` : ''}
                </div>
                <div class="color-row ss-colors">${(p.colors || []).slice(0, 6).map((c) => `<span class="color-swatch" style="background:${c}" title="${c}"></span>`).join('')}</div>`;
        }

        const frame = document.getElementById('ssPreviewFrame');
        if (frame && ver.react_code && global.ReactPreview?.buildIframeHtml) {
            frame.srcdoc = ReactPreview.buildIframeHtml(ver.react_code);
        }

        renderCommentPins();
        renderCommentsList();
        renderVersionsList();
        renderDiffControls();
        renderHandoff();
    }

    function renderDiffControls() {
        const fromEl = document.getElementById('ssDiffFrom');
        const toEl = document.getElementById('ssDiffTo');
        const outEl = document.getElementById('ssDiffOutput');
        if (!fromEl || !toEl || !activeProject) return;
        const versions = (activeProject.versions || []).slice().sort((a, b) => a.version_num - b.version_num);
        const opts = versions.map((v) => `<option value="${v.version_num}">v${v.version_num}</option>`).join('');
        fromEl.innerHTML = opts;
        toEl.innerHTML = opts;
        if (versions.length >= 2) {
            fromEl.value = String(versions[versions.length - 2].version_num);
            toEl.value = String(versions[versions.length - 1].version_num);
        } else if (versions.length === 1) {
            fromEl.value = toEl.value = String(versions[0].version_num);
        }
        if (outEl && !outEl.dataset.loaded) {
            outEl.textContent = versions.length >= 2 ? 'Нажмите «Сравнить»' : 'Нужно минимум 2 версии';
        }
    }

    async function compareVersions() {
        if (!activeId) return;
        const fromRef = document.getElementById('ssDiffFrom')?.value || '1';
        const toRef = document.getElementById('ssDiffTo')?.value || '';
        const outEl = document.getElementById('ssDiffOutput');
        if (outEl) outEl.textContent = 'Загрузка diff…';
        try {
            const q = new URLSearchParams({ from_ref: fromRef, to_ref: toRef });
            const r = await fetch(`/api/sonya/projects/${activeId}/diff?${q}`);
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка diff');
            const s = d.summary || {};
            const header = [
                `v${d.from?.version_num} → v${d.to?.version_num}`,
                `+${s.lines_added || 0} / -${s.lines_removed || 0} строк`,
                s.colors_added?.length ? `цвета +: ${s.colors_added.join(', ')}` : '',
                s.colors_removed?.length ? `цвета −: ${s.colors_removed.join(', ')}` : '',
                s.task_changed ? 'задача изменена' : '',
                d.diff_truncated ? '(diff обрезан)' : '',
            ].filter(Boolean).join(' · ');
            if (outEl) {
                outEl.dataset.loaded = '1';
                outEl.textContent = `${header}\n\n${d.diff || '(нет изменений в коде)'}`;
            }
        } catch (e) {
            if (outEl) outEl.textContent = e.message;
        }
    }

    function downloadHandoff() {
        if (!activeId) return;
        window.location.href = `/api/sonya/projects/${activeId}/handoff/download`;
    }

    function renderCommentPins() {
        const layer = document.getElementById('ssCommentLayer');
        if (!layer || !activeProject) return;
        const comments = activeProject.comments || [];
        layer.innerHTML = comments.map((c, i) => `
            <button type="button" class="ss-pin ${c.status}${c.status === 'open' ? ' open' : ''}"
                style="left:${c.x * 100}%;top:${c.y * 100}%"
                title="${esc(c.author)}: ${esc(c.text)}"
                data-idx="${i}">${c.status === 'open' ? '💬' : '✓'}</button>`).join('');
    }

    function renderCommentsList() {
        const el = document.getElementById('ssCommentsList');
        if (!el || !activeProject) return;
        const comments = activeProject.comments || [];
        if (!comments.length) {
            el.innerHTML = '<p class="muted">Кликните «Комментарий» и отметьте место на макете</p>';
            return;
        }
        el.innerHTML = comments.map((c) => `
            <div class="ss-comment ${c.status}">
                <div class="ss-comment-head"><strong>${esc(c.author)}</strong><span class="muted">${c.status === 'open' ? 'открыт' : 'исправлен'}</span></div>
                <p>${esc(c.text)}</p>
                <small class="muted">📍 ${Math.round(c.x * 100)}%, ${Math.round(c.y * 100)}%</small>
            </div>`).join('');
    }

    function renderVersionsList() {
        const el = document.getElementById('ssVersionsList');
        if (!el || !activeProject) return;
        el.innerHTML = (activeProject.versions || []).slice().reverse().map((v) => `
            <div class="ss-version">
                <strong>v${v.version_num}</strong> · ${esc(v.title)}
                <small class="muted">${esc(v.created_by)} · ${(v.created_at || '').slice(0, 16).replace('T', ' ')}</small>
            </div>`).join('');
    }

    function renderHandoff() {
        const el = document.getElementById('ssHandoff');
        if (!el || !activeProject) return;
        const h = activeProject.figma_handoff;
        if (!h) {
            el.innerHTML = '<p class="muted">После публикации здесь появятся tokens и инструкции для Figma</p>';
            return;
        }
        el.innerHTML = `
            <p class="muted">Опубликовано ${(h.published_at || '').slice(0, 16).replace('T', ' ')}</p>
            ${h.figma_url ? `<p><a href="${esc(h.figma_url)}" target="_blank" rel="noopener">Figma ↗</a></p>` : ''}
            <pre class="token-preview">${esc(h.css_tokens || '')}</pre>
            <p class="muted">${esc(h.instructions || '')}</p>
            <p class="muted"><a href="/api/sonya/projects/${activeId}/handoff/download">⬇ Скачать handoff.zip</a></p>`;
    }

    function toggleCommentMode() {
        commentMode = !commentMode;
        pendingPin = null;
        const wrap = document.getElementById('ssCanvasWrap');
        const btn = document.getElementById('ssCommentModeBtn');
        if (wrap) wrap.classList.toggle('comment-mode', commentMode);
        if (btn) {
            btn.classList.toggle('active', commentMode);
            btn.textContent = commentMode ? '✓ Указать место…' : '💬 Комментарий';
        }
        if (!commentMode) hideCommentForm();
    }

    function hideCommentForm() {
        const form = document.getElementById('ssCommentForm');
        if (form) form.classList.add('hidden');
        pendingPin = null;
    }

    function setupCanvasClick() {
        const wrap = document.getElementById('ssCanvasWrap');
        if (!wrap || wrap.dataset.bound) return;
        wrap.dataset.bound = '1';
        wrap.addEventListener('click', (e) => {
            if (!commentMode || !activeProject) return;
            if (e.target.closest('.ss-comment-form-inner')) return;
            const rect = wrap.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            pendingPin = { x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)) };
            showCommentForm(e.clientX, e.clientY);
        });
    }

    function showCommentForm(clientX, clientY) {
        const form = document.getElementById('ssCommentForm');
        const input = document.getElementById('ssCommentInput');
        if (!form || !input) return;
        form.classList.remove('hidden');
        const wrap = document.getElementById('ssCanvasWrap');
        const rect = wrap.getBoundingClientRect();
        form.style.left = `${Math.min(rect.width - 260, Math.max(8, clientX - rect.left))}px`;
        form.style.top = `${Math.min(rect.height - 120, Math.max(8, clientY - rect.top))}px`;
        input.value = '';
        input.focus();
    }

    async function submitComment() {
        if (!activeId || !pendingPin) return;
        const input = document.getElementById('ssCommentInput');
        const text = input?.value?.trim();
        if (!text) return;
        try {
            const r = await fetch(`/api/sonya/projects/${activeId}/comments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ text, x: pendingPin.x, y: pendingPin.y }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            activeProject = d.project;
            commentMode = false;
            const wrap = document.getElementById('ssCanvasWrap');
            const btn = document.getElementById('ssCommentModeBtn');
            if (wrap) wrap.classList.remove('comment-mode');
            if (btn) { btn.classList.remove('active'); btn.textContent = '💬 Комментарий'; }
            hideCommentForm();
            renderProject();
            renderProjectList();
            if (window.UIEnhancements) UIEnhancements.toast('Комментарий добавлен', 'success');
        } catch (e) {
            alert(e.message);
        }
    }

    async function applyComments() {
        if (!activeId) return;
        try {
            const r = await fetch(`/api/sonya/projects/${activeId}/apply-comments`, { method: 'POST' });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            activeProject = d.project;
            renderProject();
            renderProjectList();
            if (window.UIEnhancements) UIEnhancements.toast('Соня применила правки', 'success');
            if (d.project?.current_version && window.ReactPreview) {
                ReactPreview.render({
                    title: d.project.current_version.title,
                    code: d.project.current_version.react_code,
                    task: d.project.current_version.task,
                });
            }
        } catch (e) {
            alert(e.message);
        }
    }

    async function publishProject() {
        if (!activeId) return;
        const figmaUrl = document.getElementById('ssFigmaUrl')?.value?.trim() || '';
        if (!confirm('Опубликовать текущую версию для handoff в Figma?')) return;
        try {
            const r = await fetch(`/api/sonya/projects/${activeId}/publish`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ figma_url: figmaUrl }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            activeProject = d.project;
            renderProject();
            renderProjectList();
            if (window.UIEnhancements) UIEnhancements.toast('Проект опубликован', 'success');
        } catch (e) {
            alert(e.message);
        }
    }

    async function createProject() {
        const title = prompt('Название проекта', 'Новый UI проект');
        if (title === null) return;
        const task = prompt('Задача для Сони (опционально)', 'Landing page для SaaS с hero и CTA') || '';
        try {
            const r = await fetch('/api/sonya/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ title, task }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            await loadProjects(d.project.id);
            if (window.UIEnhancements) UIEnhancements.toast('Проект создан', 'success');
        } catch (e) {
            alert(e.message);
        }
    }

    async function askSonyaNew() {
        try {
            const project = await postSonyaCreate();
            await loadProjects(project.id);
            if (window.UIEnhancements) UIEnhancements.toast('Соня создала проект', 'success');
        } catch (e) {
            alert(e.message);
        }
    }

    function onStudioMessage(data) {
        if (data.project?.id) loadProjects(data.project.id);
        else if (data.project_id) loadProjects(data.project_id);
    }

    function init() {
        setupCanvasClick();
        document.getElementById('ssCommentSubmit')?.addEventListener('click', submitComment);
        document.getElementById('ssCommentCancel')?.addEventListener('click', () => {
            commentMode = false;
            toggleCommentMode();
        });
        document.getElementById('ssCommentInput')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitComment(); }
        });
    }

    global.SonyaStudio = {
        init,
        load: loadProjects,
        openProject,
        createProject,
        askSonyaNew,
        createBySonya: postSonyaCreate,
        applyComments,
        publishProject,
        compareVersions,
        downloadHandoff,
        toggleCommentMode,
        onMessage: onStudioMessage,
    };
})(window);
