/**
 * Live Pipeline — визуальный прогресс задачи по команде
 */
(function (global) {
    let current = null;
    let activeAgentId = null;

    function ensureBar() {
        if (document.getElementById('pipelineBar')) return;
        const bar = document.createElement('div');
        bar.id = 'pipelineBar';
        bar.className = 'pipeline-bar hidden';
        bar.innerHTML = `
            <div class="pipeline-inner">
                <div class="pipeline-title">
                    <span class="pipeline-label">Pipeline</span>
                    <span id="pipelineTask" class="pipeline-task"></span>
                    <span id="pipelinePct" class="pipeline-pct">0%</span>
                </div>
                <div class="pipeline-track"><div id="pipelineFill" class="pipeline-fill"></div></div>
                <div id="pipelineSteps" class="pipeline-steps"></div>
            </div>`;
        document.body.appendChild(bar);
    }

    function statusClass(s) {
        return ({ pending: '', active: 'step-active', done: 'step-done', failed: 'step-failed' }[s] || '');
    }

    function render(pipeline) {
        ensureBar();
        const bar = document.getElementById('pipelineBar');
        if (!pipeline || !pipeline.steps?.length) {
            bar?.classList.add('hidden');
            document.body.classList.remove('has-pipeline');
            current = null;
            activeAgentId = null;
            if (window.StudioApp) StudioApp.setPipelineHighlight(null);
            return;
        }

        current = pipeline;
        bar.classList.remove('hidden');
        document.body.classList.add('has-pipeline');
        if (pipeline.finished_at) {
            bar.classList.add('pipeline-complete');
        } else {
            bar.classList.remove('pipeline-complete');
        }

        const taskEl = document.getElementById('pipelineTask');
        const pctEl = document.getElementById('pipelinePct');
        const fillEl = document.getElementById('pipelineFill');
        const stepsEl = document.getElementById('pipelineSteps');

        if (taskEl) taskEl.textContent = (pipeline.task || '').slice(0, 60);
        const pct = pipeline.progress || 0;
        if (pctEl) pctEl.textContent = `${pct}%`;
        if (fillEl) fillEl.style.width = `${pct}%`;

        activeAgentId = null;
        if (stepsEl) {
            stepsEl.innerHTML = pipeline.steps.map((step) => {
                if (step.status === 'active') activeAgentId = step.agent_id;
                return `<div class="pipeline-step ${statusClass(step.status)}" title="${step.label || ''}">
                    <span class="step-emoji">${step.emoji || '🤖'}</span>
                    <span class="step-name">${step.name || step.agent_id}</span>
                </div>`;
            }).join('');
        }

        if (window.StudioApp) StudioApp.setPipelineHighlight(activeAgentId);
    }

    function onUpdate(data) {
        if (data.pipeline) render(data.pipeline);
    }

    async function load() {
        try {
            const r = await fetch('/api/pipeline');
            if (r.ok) {
                const d = await r.json();
                if (d.pipeline) render(d.pipeline);
            }
        } catch (_) {}
    }

    global.PipelineUI = { render, onUpdate, load };
})(window);
