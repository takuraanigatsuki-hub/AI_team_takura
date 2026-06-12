/**
 * Live Pipeline — компактная панель внизу экрана
 */
(function (global) {
    let current = null;
    let activeAgentId = null;
    let hideTimer = null;
    let collapsed = false;

    function ensureBar() {
        if (document.getElementById('pipelineBar')) return;
        const bar = document.createElement('div');
        bar.id = 'pipelineBar';
        bar.className = 'pipeline-dock hidden';
        bar.innerHTML = `
            <div class="pipeline-dock-inner">
                <div class="pipeline-dock-head">
                    <div class="pipeline-dock-head-left">
                        <span class="pipeline-label">⚡ Задача в работе</span>
                        <span id="pipelinePct" class="pipeline-pct">0%</span>
                    </div>
                    <div class="pipeline-dock-head-actions">
                        <button type="button" class="pipeline-dock-btn" onclick="switchView('tasks')" title="Открыть задачи">📋</button>
                        <button type="button" class="pipeline-dock-btn" id="pipelineCollapseBtn" onclick="PipelineUI.toggleCollapse()" title="Свернуть">▼</button>
                    </div>
                </div>
                <div class="pipeline-dock-body" id="pipelineDockBody">
                    <p id="pipelineTask" class="pipeline-task-text"></p>
                    <div class="pipeline-track"><div id="pipelineFill" class="pipeline-fill"></div></div>
                    <div id="pipelineSteps" class="pipeline-steps"></div>
                </div>
            </div>`;
        const footer = document.getElementById('statusFooter');
        if (footer?.parentNode) {
            footer.parentNode.insertBefore(bar, footer);
        } else {
            document.body.appendChild(bar);
        }
    }

    function statusClass(s) {
        return ({ pending: '', active: 'step-active', done: 'step-done', failed: 'step-failed' }[s] || '');
    }

    function clearHideTimer() {
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
    }

    function scheduleHide(ms = 15000) {
        clearHideTimer();
        hideTimer = setTimeout(() => {
            hide();
        }, ms);
    }

    function hide() {
        const bar = document.getElementById('pipelineBar');
        bar?.classList.add('hidden');
        document.body.classList.remove('has-pipeline');
        current = null;
        activeAgentId = null;
        if (window.StudioApp) StudioApp.setPipelineHighlight(null);
    }

    function isStaleFinished(pipeline) {
        if (!pipeline?.finished_at) return false;
        const finished = new Date(pipeline.finished_at).getTime();
        return Number.isFinite(finished) && (Date.now() - finished > 20000);
    }

    function render(pipeline) {
        ensureBar();
        const bar = document.getElementById('pipelineBar');
        if (!pipeline || !pipeline.steps?.length || isStaleFinished(pipeline)) {
            clearHideTimer();
            hide();
            return;
        }

        current = pipeline;
        bar.classList.remove('hidden');
        document.body.classList.add('has-pipeline');
        if (pipeline.finished_at) {
            bar.classList.add('pipeline-complete');
            scheduleHide();
        } else {
            bar.classList.remove('pipeline-complete');
            clearHideTimer();
        }

        const taskEl = document.getElementById('pipelineTask');
        const pctEl = document.getElementById('pipelinePct');
        const fillEl = document.getElementById('pipelineFill');
        const stepsEl = document.getElementById('pipelineSteps');

        const taskText = (pipeline.task || 'Без названия').trim();
        if (taskEl) {
            taskEl.textContent = taskText;
            taskEl.title = taskText;
        }
        const pct = pipeline.progress || 0;
        if (pctEl) pctEl.textContent = `${pct}%`;
        if (fillEl) fillEl.style.width = `${pct}%`;

        activeAgentId = null;
        if (stepsEl) {
            stepsEl.innerHTML = pipeline.steps.map((step) => {
                if (step.status === 'active') activeAgentId = step.agent_id;
                const label = step.label ? ` — ${step.label}` : '';
                return `<div class="pipeline-step ${statusClass(step.status)}" title="${(step.label || step.name || '').replace(/"/g, '')}">
                    <span class="step-emoji">${step.emoji || '🤖'}</span>
                    <span class="step-name">${step.name || step.agent_id}${label ? '' : ''}</span>
                </div>`;
            }).join('');
        }

        if (window.StudioApp) StudioApp.setPipelineHighlight(activeAgentId);
    }

    function onUpdate(data) {
        if (data.pipeline === null || data.pipeline === undefined) {
            clearHideTimer();
            hide();
            return;
        }
        if (data.pipeline) render(data.pipeline);
    }

    async function load() {
        try {
            const r = await fetch('/api/pipeline', { credentials: 'same-origin' });
            if (r.ok) {
                const d = await r.json();
                if (d.pipeline) render(d.pipeline);
                else hide();
            }
        } catch (_) { /* ignore */ }
    }

    function toggleCollapse() {
        collapsed = !collapsed;
        const bar = document.getElementById('pipelineBar');
        const body = document.getElementById('pipelineDockBody');
        const btn = document.getElementById('pipelineCollapseBtn');
        bar?.classList.toggle('pipeline-collapsed', collapsed);
        if (body) body.hidden = collapsed;
        if (btn) btn.textContent = collapsed ? '▲' : '▼';
        document.body.classList.toggle('has-pipeline-collapsed', collapsed);
    }

    global.PipelineUI = { render, onUpdate, load, toggleCollapse, hide };
})(window);
