/**
 * React Live Preview — панель Сони (Frontend)
 */
(function (global) {
    let panelOpen = false;
    let lastPreviewData = null;
    let activeTab = 'preview';
    let viewport = 'desktop';

    const VIEWPORTS = {
        mobile: { width: 375, label: '375px' },
        tablet: { width: 768, label: '768px' },
        desktop: { width: '100%', label: '100%' },
    };

    function buildIframeHtml(code) {
        const safeCode = code || 'function App(){return <div>Нет кода</div>;}';
        return `<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"><\/script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"><\/script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"><\/script>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; -webkit-font-smoothing: antialiased; }
  #root { min-height: 100vh; }
  .preview-error {
    padding: 20px; color: #dc2626; font-family: system-ui, sans-serif;
    font-size: 13px; white-space: pre-wrap; background: #fef2f2;
    border: 1px solid #fecaca; border-radius: 8px; margin: 16px;
  }
  :focus-visible { outline: 2px solid #4f7df3; outline-offset: 2px; }
</style>
</head><body>
<div id="root" role="main"></div>
<script type="text/babel" data-presets="react">
const { useState, useEffect, useRef, useMemo, useCallback } = React;

${safeCode}

try {
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(<App />);
} catch (err) {
  document.getElementById('root').innerHTML = '<div class="preview-error" role="alert">Ошибка рендера:\\n' + (err.message || err) + '</div>';
}
<\/script>
</body></html>`;
    }

    function setLoading(on) {
        const el = document.getElementById('reactPreviewLoading');
        if (el) el.classList.toggle('show', on);
    }

    function setError(msg) {
        const el = document.getElementById('reactPreviewError');
        if (!el) return;
        if (msg) {
            el.textContent = msg;
            el.style.display = 'block';
        } else {
            el.textContent = '';
            el.style.display = 'none';
        }
    }

    function formatTimestamp(ts) {
        if (!ts) return '';
        try {
            const d = new Date(ts);
            return d.toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
        } catch (_) {
            return '';
        }
    }

    function applyViewport() {
        const wrap = document.getElementById('reactPreviewFrameWrap');
        const frame = document.getElementById('reactPreviewFrame');
        if (!wrap || !frame) return;
        const vp = VIEWPORTS[viewport] || VIEWPORTS.desktop;
        if (viewport === 'desktop') {
            wrap.style.maxWidth = '';
            wrap.style.margin = '';
            frame.style.width = '100%';
        } else {
            wrap.style.maxWidth = vp.width + 'px';
            wrap.style.margin = '0 auto';
            frame.style.width = '100%';
        }
        document.querySelectorAll('[data-viewport]').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.viewport === viewport);
        });
    }

    function setTab(tab) {
        activeTab = tab;
        const previewPane = document.getElementById('reactPreviewPane');
        const codePane = document.getElementById('reactPreviewCodePane');
        if (previewPane) previewPane.style.display = tab === 'preview' ? 'flex' : 'none';
        if (codePane) codePane.style.display = tab === 'code' ? 'block' : 'none';
        document.querySelectorAll('[data-preview-tab]').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.previewTab === tab);
        });
    }

    function renderPreview(data) {
        const iframe = document.getElementById('reactPreviewFrame');
        const codeEl = document.getElementById('reactPreviewCode');
        const titleEl = document.getElementById('reactPreviewTitle');
        const taskEl = document.getElementById('reactPreviewTaskText');
        const badge = document.getElementById('reactPreviewBadge');
        const timeEl = document.getElementById('reactPreviewTime');

        if (!iframe) return;

        lastPreviewData = data;
        setLoading(false);
        setError(null);

        if (titleEl) titleEl.textContent = data.title || 'React Preview';
        if (taskEl) taskEl.textContent = data.task ? `Задача: ${data.task}` : '';
        if (codeEl) codeEl.textContent = data.code || '';
        if (timeEl) timeEl.textContent = formatTimestamp(data.timestamp);
        if (badge) {
            const polished = data.polished ? 'Production' : 'Live';
            badge.textContent = `● ${polished}`;
            badge.classList.add('live');
            if (data.polished) badge.classList.add('production');
            else badge.classList.remove('production');
        }

        iframe.srcdoc = buildIframeHtml(data.code);
        applyViewport();

        const empty = document.getElementById('reactPreviewEmpty');
        const content = document.getElementById('reactPreviewContent');
        if (empty) empty.style.display = 'none';
        if (content) content.style.display = 'flex';

        const link = document.getElementById('siteOpenLink');
        if (link) {
            if (data.is_site && data.site_url) {
                link.href = data.site_url;
                link.style.display = 'inline-flex';
            } else {
                link.style.display = 'none';
            }
        }

        openPanel();
    }

    function openPanel() {
        const panel = document.getElementById('reactPreviewPanel');
        if (!panel) return;
        panel.classList.add('open');
        panelOpen = true;
    }

    function closePanel() {
        const panel = document.getElementById('reactPreviewPanel');
        if (!panel) return;
        panel.classList.remove('open');
        panelOpen = false;
    }

    function togglePanel() {
        if (panelOpen) closePanel();
        else openPanel();
    }

    async function loadLatest() {
        setLoading(true);
        setError(null);
        try {
            const resp = await fetch('/api/agents/frontend/preview');
            if (!resp.ok) throw new Error('Не удалось загрузить preview');
            const data = await resp.json();
            if (data.preview) {
                const p = data.preview;
                renderPreview({
                    title: p.title,
                    code: p.code,
                    task: p.task,
                    timestamp: p.timestamp,
                    is_site: p.is_site,
                    site_url: p.site_url,
                    polished: p.polished,
                });
            } else {
                setLoading(false);
            }
        } catch (e) {
            setLoading(false);
            setError(e.message || 'Ошибка загрузки');
        }
    }

    function refresh() {
        if (lastPreviewData) {
            setLoading(true);
            setTimeout(() => renderPreview(lastPreviewData), 150);
        } else {
            loadLatest();
        }
    }

    async function copyCode() {
        const code = lastPreviewData?.code || document.getElementById('reactPreviewCode')?.textContent;
        if (!code) return;
        try {
            await navigator.clipboard.writeText(code);
            if (window.UIEnhancements) UIEnhancements.toast('Код скопирован', 'success');
        } catch (_) {
            if (window.UIEnhancements) UIEnhancements.toast('Не удалось скопировать', 'error');
        }
    }

    function setViewport(vp) {
        viewport = vp in VIEWPORTS ? vp : 'desktop';
        applyViewport();
    }

    function onPreviewMessage(data) {
        renderPreview({
            title: data.title,
            code: data.code,
            task: data.task,
            timestamp: data.timestamp,
            is_site: data.is_site,
            site_url: data.site_url,
            polished: data.polished,
        });
    }

    global.ReactPreview = {
        render: renderPreview,
        open: openPanel,
        close: closePanel,
        toggle: togglePanel,
        loadLatest,
        refresh,
        copyCode,
        setTab,
        setViewport,
        onMessage: onPreviewMessage,
    };
})(window);
