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

    function statusLabel(st) {
        return { draft: 'Черновик', review: 'На ревью', published: 'Опубликован' }[st] || st;
    }

    async function loadProjects(selectId) {
        const listEl = document.getElementById('ssProjectList');
        if (listEl) listEl.innerHTML = '<div class="panel-empty">Загрузка…</div>';
        try {
            const r = await fetch('/api/sonya/projects');
            const d = await r.json();
            projects = d.projects || [];
            renderProjectList();
            const id = selectId || activeId || (projects[0] && projects[0].id);
            if (id) await openProject(id);
            else clearCanvas();
        } catch (e) {
            if (listEl) listEl.innerHTML = `<div class="panel-error">${esc(e.message)}</div>`;
        }
    }

    function renderProjectList() {
        const el = document.getElementById('ssProjectList');
        if (!el) return;
        if (!projects.length) {
            el.innerHTML = '<div class="panel-empty">Нет проектов.<br>Нажмите «Новый проект».</div>';
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
            if (!r.ok) throw new Error('Проект не найден');
            activeProject = await r.json();
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
        renderHandoff();
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
            <p class="muted">${esc(h.instructions || '')}</p>`;
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
            const r = await fetch('/api/sonya/projects/create-new', { method: 'POST' });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            await loadProjects(d.project.id);
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
        applyComments,
        publishProject,
        toggleCommentMode,
        onMessage: onStudioMessage,
    };
})(window);
