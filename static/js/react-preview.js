/**
 * React Live Preview — панель Сони (Frontend)
 */
(function (global) {
    let panelOpen = false;

    function buildIframeHtml(code) {
        const safeCode = code || 'function App(){return <div>Нет кода</div>;}';
        return `<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"><\/script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"><\/script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"><\/script>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; }
  #root { min-height: 100vh; }
  .preview-error { padding: 16px; color: #dc2626; font-family: system-ui; font-size: 13px; white-space: pre-wrap; }
</style>
</head><body>
<div id="root"></div>
<script type="text/babel" data-presets="react">
const { useState, useEffect, useRef, useMemo, useCallback } = React;

${safeCode}

try {
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(<App />);
} catch (err) {
  document.getElementById('root').innerHTML = '<div class="preview-error">Ошибка рендера:\\n' + err.message + '</div>';
}
<\/script>
</body></html>`;
    }

    function renderPreview(data) {
        const iframe = document.getElementById('reactPreviewFrame');
        const codeEl = document.getElementById('reactPreviewCode');
        const titleEl = document.getElementById('reactPreviewTitle');
        const taskEl = document.getElementById('reactPreviewTaskText');
        const badge = document.getElementById('reactPreviewBadge');

        if (!iframe) return;

        if (titleEl) titleEl.textContent = data.title || 'React Preview';
        if (taskEl) taskEl.textContent = data.task ? `Задача: ${data.task}` : '';
        if (codeEl) codeEl.textContent = data.code || '';
        if (badge) {
            badge.textContent = '● Live';
            badge.classList.add('live');
        }

        iframe.srcdoc = buildIframeHtml(data.code);

        const empty = document.getElementById('reactPreviewEmpty');
        const content = document.getElementById('reactPreviewContent');
        if (empty) empty.style.display = 'none';
        if (content) content.style.display = 'flex';

        openPanel();

        if (data.is_site && data.site_url) {
            const link = document.getElementById('siteOpenLink');
            if (link) {
                link.href = data.site_url;
                link.style.display = 'inline-flex';
            }
        }
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
        try {
            const resp = await fetch('/api/agents/frontend/preview');
            if (!resp.ok) return;
            const data = await resp.json();
            if (data.preview) renderPreview(data.preview);
        } catch (_) {}
    }

    function onPreviewMessage(data) {
        renderPreview({
            title: data.title,
            code: data.code,
            task: data.task,
            timestamp: data.timestamp,
        });
    }

    global.ReactPreview = {
        render: renderPreview,
        buildIframeHtml,
        open: openPanel,
        close: closePanel,
        toggle: togglePanel,
        loadLatest,
        onMessage: onPreviewMessage,
    };
})(window);
