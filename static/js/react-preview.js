/**
 * React Live Preview — production-ready panel (Соня / Frontend)
 */
(function (global) {
    let panelOpen = false;
    let currentData = null;
    let viewport = 'desktop';
    let codePanelHeight = 200;
    let fullscreen = false;
    let loadTimer = null;

    const VIEWPORTS = {
        mobile: { width: 375, label: '375px' },
        tablet: { width: 768, label: '768px' },
        desktop: { width: null, label: '100%' },
    };

    function $(id) {
        return document.getElementById(id);
    }

    function buildIframeHtml(code) {
        const safeCode = code || 'function App(){return <div style={{padding:24,fontFamily:"system-ui"}}>Нет кода</div>;}';
        return `<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"><\/script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"><\/script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"><\/script>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  #root { min-height: 100vh; }
  .preview-error {
    padding: 20px; margin: 16px; border-radius: 12px;
    background: #fef2f2; border: 1px solid #fecaca;
    color: #b91c1c; font-family: system-ui, sans-serif;
    font-size: 13px; white-space: pre-wrap; line-height: 1.5;
  }
  .preview-error strong { display: block; margin-bottom: 6px; }
</style>
</head><body>
<div id="root"><div style="padding:24px;color:#6b7280;font-family:system-ui;font-size:13px">Загрузка preview…</div></div>
<script>
window.__previewError = function(msg) {
  var el = document.getElementById('root');
  if (el) el.innerHTML = '<div class="preview-error"><strong>Ошибка рендера</strong>' + msg + '</div>';
};
window.onerror = function(msg) { window.__previewError(String(msg)); return true; };
<\/script>
<script type="text/babel" data-presets="react">
const { useState, useEffect, useRef, useMemo, useCallback } = React;

class PreviewErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (this.state.error) {
      return React.createElement('div', { className: 'preview-error' },
        React.createElement('strong', null, 'Ошибка компонента'),
        this.state.error.message
      );
    }
    return this.props.children;
  }
}

${safeCode}

try {
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(
    React.createElement(PreviewErrorBoundary, null, React.createElement(App))
  );
  if (window.parent !== window) {
    window.parent.postMessage({ type: 'react-preview-ready' }, '*');
  }
} catch (err) {
  window.__previewError(err.message);
}
<\/script>
</body></html>`;
    }

    function setLoading(on) {
        const overlay = $('reactPreviewLoading');
        if (overlay) overlay.classList.toggle('visible', on);
        const badge = $('reactPreviewBadge');
        if (badge) {
            badge.textContent = on ? '● Loading' : '● Live';
            badge.classList.toggle('live', !on);
            badge.classList.toggle('loading', on);
        }
    }

    function setError(msg) {
        const el = $('reactPreviewError');
        if (!el) return;
        if (msg) {
            el.textContent = msg;
            el.hidden = false;
        } else {
            el.hidden = true;
            el.textContent = '';
        }
    }

    function applyViewport() {
        const wrap = $('reactPreviewViewport');
        const frame = $('reactPreviewFrame');
        const label = $('reactPreviewViewportLabel');
        if (!wrap || !frame) return;

        wrap.dataset.viewport = viewport;
        const cfg = VIEWPORTS[viewport] || VIEWPORTS.desktop;

        if (cfg.width) {
            wrap.style.maxWidth = cfg.width + 'px';
            wrap.style.margin = '0 auto';
        } else {
            wrap.style.maxWidth = 'none';
            wrap.style.margin = '0';
        }
        if (label) label.textContent = cfg.label;
    }

    function setViewport(mode) {
        viewport = mode in VIEWPORTS ? mode : 'desktop';
        document.querySelectorAll('[data-preview-viewport]').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.previewViewport === viewport);
            btn.setAttribute('aria-pressed', btn.dataset.previewViewport === viewport ? 'true' : 'false');
        });
        applyViewport();
    }

    function updateSiteLink(data) {
        const link = $('siteOpenLink');
        if (!link) return;
        if (data.is_site && data.site_url) {
            link.href = data.site_url;
            link.style.display = 'inline-flex';
        } else {
            link.style.display = 'none';
        }
    }

    function renderPreview(data, opts = {}) {
        const autoOpen = opts.autoOpen !== false;
        const iframe = $('reactPreviewFrame');
        const codeEl = $('reactPreviewCode');
        const titleEl = $('reactPreviewTitle');
        const taskEl = $('reactPreviewTaskText');

        if (!iframe) return;

        currentData = data;
        setError(null);

        if (titleEl) titleEl.textContent = data.title || 'React Preview';
        if (taskEl) taskEl.textContent = data.task ? `Задача: ${data.task}` : '';
        if (codeEl) codeEl.textContent = data.code || '';

        updateSiteLink(data);

        const empty = $('reactPreviewEmpty');
        const content = $('reactPreviewContent');
        if (empty) empty.style.display = 'none';
        if (content) content.style.display = 'flex';

        setLoading(true);
        clearTimeout(loadTimer);
        loadTimer = setTimeout(() => {
            setLoading(false);
            setError('Preview не ответил — проверьте код или сеть (CDN).');
        }, 12000);

        iframe.srcdoc = buildIframeHtml(data.code);
        applyViewport();
        openPanel();
    }

    function onIframeMessage(ev) {
        if (ev.data && ev.data.type === 'react-preview-ready') {
            clearTimeout(loadTimer);
            setLoading(false);
            setError(null);
        }
    }

    function openPanel() {
        const panel = $('reactPreviewPanel');
        if (!panel) return;
        panel.classList.add('open');
        panel.setAttribute('aria-hidden', 'false');
        panelOpen = true;
        const closeBtn = panel.querySelector('.preview-close-btn');
        if (closeBtn) closeBtn.focus();
    }

    function closePanel() {
        const panel = $('reactPreviewPanel');
        if (!panel) return;
        panel.classList.remove('open');
        panel.classList.remove('fullscreen');
        panel.setAttribute('aria-hidden', 'true');
        panelOpen = false;
        fullscreen = false;
    }

    function togglePanel() {
        if (panelOpen) {
            closePanel();
            return;
        }
        if (!currentData) {
            loadLatest().then(() => {
                if (!currentData) openPanel();
            });
            return;
        }
        openPanel();
    }

    function toggleFullscreen() {
        const panel = $('reactPreviewPanel');
        if (!panel) return;
        fullscreen = !fullscreen;
        panel.classList.toggle('fullscreen', fullscreen);
        const btn = $('reactPreviewFullscreenBtn');
        if (btn) {
            btn.title = fullscreen ? 'Выйти из полноэкранного режима' : 'Полный экран';
            btn.setAttribute('aria-pressed', fullscreen ? 'true' : 'false');
        }
    }

    async function loadLatest() {
        setLoading(true);
        try {
            const resp = await fetch('/api/agents/frontend/preview');
            if (!resp.ok) {
                setLoading(false);
                return;
            }
            const data = await resp.json();
            if (data.preview) renderPreview(data.preview);
            else setLoading(false);
        } catch (e) {
            setLoading(false);
            setError('Не удалось загрузить preview: ' + e.message);
        }
    }

    function refreshPreview() {
        if (currentData) renderPreview(currentData);
        else loadLatest();
    }

    async function copyCode() {
        const code = $('reactPreviewCode')?.textContent || '';
        if (!code) return;
        try {
            await navigator.clipboard.writeText(code);
            if (window.UIEnhancements) UIEnhancements.toast('Код скопирован', 'success');
        } catch (_) {
            if (window.UIEnhancements) UIEnhancements.toast('Не удалось скопировать', 'error');
        }
    }

    function onPreviewMessage(data) {
        renderPreview({
            title: data.title,
            code: data.code,
            task: data.task,
            timestamp: data.timestamp,
            is_site: data.is_site,
            site_url: data.site_url,
        });
    }

    function initResize() {
        const handle = $('reactPreviewResize');
        const wrap = $('reactPreviewCodeWrap');
        if (!handle || !wrap) return;

        let dragging = false;
        let startY = 0;
        let startH = 0;

        handle.addEventListener('mousedown', (e) => {
            dragging = true;
            startY = e.clientY;
            startH = wrap.offsetHeight;
            handle.classList.add('dragging');
            document.body.style.cursor = 'row-resize';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            const delta = startY - e.clientY;
            codePanelHeight = Math.min(480, Math.max(100, startH + delta));
            wrap.style.height = codePanelHeight + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (!dragging) return;
            dragging = false;
            handle.classList.remove('dragging');
            document.body.style.cursor = '';
        });
    }

    function initKeyboard() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && panelOpen) {
                if (fullscreen) toggleFullscreen();
                else closePanel();
            }
        });
    }

    function init() {
        window.addEventListener('message', onIframeMessage);
        initResize();
        initKeyboard();

        const wrap = $('reactPreviewCodeWrap');
        if (wrap) wrap.style.height = codePanelHeight + 'px';

        const panel = $('reactPreviewPanel');
        if (panel) panel.setAttribute('aria-hidden', 'true');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    global.ReactPreview = {
        render: renderPreview,
        buildIframeHtml,
        open: openPanel,
        close: closePanel,
        toggle: togglePanel,
        loadLatest,
        refresh: refreshPreview,
        copyCode,
        setViewport,
        toggleFullscreen,
        onMessage: onPreviewMessage,
    };
})(window);
