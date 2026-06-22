(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const fmt = (n, d = 2) =>
    n === null || n === undefined || Number.isNaN(n)
      ? "—"
      : Number(n).toLocaleString("ru-RU", {
          minimumFractionDigits: d,
          maximumFractionDigits: d,
        });
  const fmtPct = (n) =>
    n === null || n === undefined || Number.isNaN(n)
      ? "—"
      : (n >= 0 ? "+" : "") + Number(n).toFixed(2) + "%";
  const tsFmt = (ms) => {
    if (!ms) return "—";
    const d = new Date(ms);
    return d.toLocaleString("ru-RU");
  };

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) {
      let detail;
      try { detail = (await res.json()).detail; } catch (e) { detail = res.statusText; }
      throw new Error(detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  let equityChart = null;
  function renderEquity(points) {
    const ctx = $("#equity-chart").getContext("2d");
    const labels = points.map((p) => new Date(p.ts).toLocaleTimeString("ru-RU"));
    const data = points.map((p) => p.equity);
    const config = {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Equity",
          data,
          borderColor: "#4ea1ff",
          backgroundColor: "rgba(78,161,255,0.15)",
          fill: true,
          tension: 0.25,
          pointRadius: 0,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#93a4bf", maxTicksLimit: 8 }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { ticks: { color: "#93a4bf" }, grid: { color: "rgba(255,255,255,0.05)" } },
        },
      },
    };
    if (equityChart) {
      equityChart.data = config.data;
      equityChart.update("none");
    } else {
      equityChart = new Chart(ctx, config);
    }
  }

  function setKpis(status) {
    $("#kpi-equity").textContent = fmt(status.equity);
    $("#kpi-cash").textContent = fmt(status.cash);
    $("#kpi-positions-value").textContent = fmt(status.positions_value);
    const pnlEl = $("#kpi-daily-pnl");
    pnlEl.textContent = fmt(status.daily_pnl) + " · " + fmtPct(status.daily_pnl_pct);
    pnlEl.classList.toggle("pnl-pos", status.daily_pnl >= 0);
    pnlEl.classList.toggle("pnl-neg", status.daily_pnl < 0);
    $("#kpi-status").textContent =
      (status.running ? "RUN" : "STOP") +
      (status.paused ? " · PAUSE" : "") +
      (status.kill_switch ? " · KILL" : "");
    $("#last-tick").textContent = "tick: " + tsFmt(status.last_tick_at);
    $("#symbols-list").textContent = (status.symbols || []).join(", ");
    const list = $("#strategies-list");
    list.innerHTML = "";
    (status.strategies || []).forEach((name) => {
      const li = document.createElement("li");
      li.textContent = name;
      list.appendChild(li);
    });
  }

  function renderPositions(rows) {
    const tbody = $("#positions-table tbody");
    if (!rows || !rows.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="muted">нет позиций</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((r) => `
      <tr>
        <td>${r.symbol}</td>
        <td>${fmt(r.quantity, 6)}</td>
        <td>${fmt(r.avg_entry_price, 4)}</td>
        <td>${fmt(r.current_price, 4)}</td>
        <td>${fmt(r.market_value, 2)}</td>
        <td class="${r.unrealized_pnl >= 0 ? "pnl-pos" : "pnl-neg"}">
          ${fmt(r.unrealized_pnl, 2)} · ${fmtPct(r.unrealized_pnl_pct)}
        </td>
        <td>${fmt(r.stop_loss, 4)}</td>
        <td>${fmt(r.take_profit, 4)}</td>
      </tr>
    `).join("");
  }

  function renderDecisions(rows) {
    const tbody = $("#decisions-table tbody");
    if (!rows || !rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="muted">пока пусто</td></tr>';
      return;
    }
    tbody.innerHTML = rows.slice(0, 30).map((r) => `
      <tr>
        <td>${tsFmt(r.ts)}</td>
        <td>${r.symbol}</td>
        <td class="act-${r.action}">${r.action.toUpperCase()}</td>
        <td>${fmt(r.confidence * 100, 0)}%</td>
        <td>${fmt(r.price, 4)}</td>
        <td>${escapeHtml(r.reason || "")}</td>
      </tr>
    `).join("");
  }

  function renderOrders(rows) {
    const tbody = $("#orders-table tbody");
    if (!rows || !rows.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="muted">пока пусто</td></tr>';
      return;
    }
    tbody.innerHTML = rows.slice(0, 30).map((r) => `
      <tr>
        <td>${tsFmt(r.created_at)}</td>
        <td>${r.symbol}</td>
        <td class="act-${r.side}">${r.side.toUpperCase()}</td>
        <td>${fmt(r.quantity, 6)}</td>
        <td>${fmt(r.price, 4)}</td>
        <td>${fmt(r.quote_amount, 2)}</td>
        <td>${fmt(r.fee, 4)}</td>
        <td>${escapeHtml(r.reason || "")}</td>
      </tr>
    `).join("");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function refresh() {
    try {
      const [status, positions, decisions, orders, equity, agentStatus, journal, news, metrics,
             risk, stress, optMs, optRp, sentiment] = await Promise.all([
        api("/api/bot/status"),
        api("/api/bot/positions"),
        api("/api/bot/decisions?limit=30"),
        api("/api/bot/orders?limit=30"),
        api("/api/bot/equity?limit=200"),
        api("/api/agent/status"),
        api("/api/agent/journal?limit=20"),
        api("/api/agent/news?limit=15").catch(() => []),
        api("/api/metrics/portfolio").catch(() => null),
        api("/api/analytics/risk").catch(() => ({ error: "—" })),
        api("/api/analytics/stress").catch(() => []),
        api("/api/optimizer/max_sharpe").catch(() => null),
        api("/api/optimizer/risk_parity").catch(() => null),
        api("/api/sentiment").catch(() => []),
      ]);
      setKpis(status);
      renderPositions(positions);
      renderDecisions(decisions);
      renderOrders(orders);
      renderEquity(equity);
      renderAgentStatus(agentStatus);
      renderJournal(journal);
      renderNews(news);
      renderMetrics(metrics);
      renderRisk(risk);
      renderStress(stress);
      renderOptimizer($("#opt-sharpe"), optMs);
      renderOptimizer($("#opt-parity"), optRp);
      renderSentiment(sentiment);
    } catch (err) {
      console.error("refresh failed:", err);
    }
  }

  async function withButtons(disabled, fn) {
    document.querySelectorAll(".btn").forEach((b) => (b.disabled = disabled));
    try { await fn(); } finally {
      document.querySelectorAll(".btn").forEach((b) => (b.disabled = false));
    }
  }

  function renderMetrics(m) {
    if (!m) return;
    const grid = $("#metrics-grid");
    if (!m.points) {
      grid.innerHTML = '<div class="muted">пока нет данных (бот не делал тиков)</div>';
      $("#metrics-since").textContent = "—";
      return;
    }
    $("#metrics-since").textContent = m.first_at
      ? `с ${tsFmt(m.first_at)} · ${m.points} точек`
      : "—";
    const pnlClass = (v) => v >= 0 ? "pnl-pos" : "pnl-neg";
    const items = [
      ["Старт", fmt(m.starting_equity), ""],
      ["Сейчас", fmt(m.current_equity), ""],
      ["Всего", `${fmt(m.total_return)} (${fmtPct(m.total_return_pct)})`, pnlClass(m.total_return)],
      ["Max DD", `${fmt(m.max_drawdown)} (${fmtPct(-m.max_drawdown_pct)})`, "pnl-neg"],
      ["Sharpe", m.sharpe_ratio === null ? "—" : fmt(m.sharpe_ratio, 2), ""],
      ["Sortino", m.sortino_ratio === null ? "—" : fmt(m.sortino_ratio, 2), ""],
      ["Win-rate", m.win_rate === null ? "—" : fmtPct(m.win_rate * 100), ""],
      ["Ордеров", String(m.num_orders), ""],
    ];
    grid.innerHTML = items.map(([label, value, cls]) =>
      `<div class="m"><div class="m-label">${label}</div>` +
      `<div class="m-value ${cls}">${value}</div></div>`
    ).join("");
  }

  function renderAgentStatus(s) {
    if (!s) return;
    $("#agent-status").textContent =
      (s.has_api_key ? "" : "ключ LLM не задан · ") +
      (s.running ? "работает" : "остановлен") +
      ` · циклов: ${s.cycles}`;
    $("#agent-meta").textContent =
      `провайдер: ${s.provider} · модель: ${s.model} · интервал: ${s.interval_seconds}с` +
      (s.last_run_at ? ` · последний тик: ${tsFmt(s.last_run_at)}` : "") +
      (s.last_error ? ` · ошибка: ${s.last_error}` : "");
  }

  function renderJournal(rows) {
    const box = $("#agent-journal");
    if (!rows || !rows.length) {
      box.innerHTML = '<div class="muted">журнал пока пуст</div>';
      return;
    }
    box.innerHTML = rows.slice(0, 20).map((r) => {
      let executed = [];
      try { executed = JSON.parse(r.executed || "[]"); } catch (e) { executed = []; }
      const actions = executed.map((a) =>
        `<div class="action-line ${a.accepted ? "ok" : "no"}">` +
        `${a.accepted ? "✓" : "✗"} <b>${a.tool}</b> ` +
        `${escapeHtml(JSON.stringify(a.args || {}))} — ${escapeHtml(a.detail || "")}</div>`
      ).join("");
      const err = r.error ? `<div class="err">${escapeHtml(r.error)}</div>` : "";
      return `
        <div class="journal-entry">
          <div class="meta">
            <time>${tsFmt(r.ts)}</time>
            <span class="muted">${r.mode}</span>
          </div>
          <div class="thesis">${escapeHtml(r.thesis || "(нет тезиса)")}</div>
          ${actions ? `<div class="actions">${actions}</div>` : ""}
          ${err}
        </div>
      `;
    }).join("");
  }

  function renderNews(items) {
    const ul = $("#news-list");
    if (!items || !items.length) {
      ul.innerHTML = '<li class="muted">новостей нет (или ленты недоступны)</li>';
      return;
    }
    ul.innerHTML = items.slice(0, 20).map((n) => `
      <li>
        <a href="${escapeAttr(n.link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(n.title)}</a>
        <div class="news-meta">${escapeHtml(n.source)}${n.published_at ? " · " + tsFmt(n.published_at) : ""}</div>
      </li>
    `).join("");
  }

  function escapeAttr(s) { return escapeHtml(s); }

  function renderRisk(risk) {
    if (!risk || risk.error) {
      $("#risk-meta").textContent = risk?.error || "нет данных";
      return;
    }
    $("#risk-meta").textContent =
      `годовая σ=${fmtPct((risk.volatility||0)*100)} · μ=${fmtPct((risk.expected_return||0)*100)} ` +
      `· Sharpe=${risk.sharpe ?? "—"}`;
    $("#risk-var").innerHTML = [
      ["VaR 95% (период)", fmtPct((risk.var_95||0)*100), "pnl-neg"],
      ["CVaR 95% (период)", fmtPct((risk.cvar_95||0)*100), "pnl-neg"],
      ["Макс. убыток (hist)", fmtPct((risk.max_loss_observed||0)*100), "pnl-neg"],
    ].map(([l, v, cls]) =>
      `<div class="m"><div class="m-label">${l}</div><div class="m-value ${cls}">${v}</div></div>`
    ).join("");

    const betas = risk.betas || {};
    $("#risk-betas").innerHTML = Object.keys(betas).length
      ? Object.entries(betas).map(([s, b]) =>
          `<li><span class="k">${s}</span><span>β=${fmt(b, 3)}</span></li>`
        ).join("")
      : '<li class="muted">—</li>';

    const contrib = risk.contributions || [];
    $("#risk-contrib").innerHTML = contrib.length
      ? contrib.map((c) =>
          `<li><span class="k">${c.symbol} (w=${fmtPct(c.weight*100)})</span>` +
          `<span>${fmtPct(c.pct_of_total_risk)} риска</span></li>`
        ).join("")
      : '<li class="muted">—</li>';
  }

  function renderStress(stress) {
    const tbody = $("#stress-table tbody");
    if (!stress || !stress.length) {
      tbody.innerHTML = '<tr><td colspan="2" class="muted">портфель пуст</td></tr>';
      return;
    }
    tbody.innerHTML = stress.map((s) => {
      const cls = s.portfolio_change_pct < 0 ? "pnl-neg" : "pnl-pos";
      return `<tr><td>${escapeHtml(s.scenario)}</td>` +
             `<td class="${cls}">${fmtPct(s.portfolio_change_pct)}</td></tr>`;
    }).join("");
  }

  function renderOptimizer(elem, res) {
    if (!res || !res.weights || !res.converged) {
      elem.innerHTML = '<li class="muted">оптимизатор не сошёлся</li>';
      return;
    }
    const entries = Object.entries(res.weights)
      .filter(([_, w]) => w > 0.005)
      .sort((a, b) => b[1] - a[1]);
    elem.innerHTML = entries.map(([sym, w]) =>
      `<li><span class="k">${sym}</span><span>${fmtPct(w*100)}</span></li>`
    ).join("") +
      `<li><span class="k">σ годовая</span><span>${fmtPct((res.volatility||0)*100)}</span></li>` +
      `<li><span class="k">Sharpe</span><span>${res.sharpe ?? "—"}</span></li>`;
  }

  function renderSentiment(items) {
    const list = $("#sentiment-list");
    if (!items || !items.length) {
      list.innerHTML = '<li class="muted">в окне 48ч нет упоминаний</li>';
      return;
    }
    list.innerHTML = items.map((s) => {
      const cls = "label-" + s.label;
      return `<li><span class="k">${s.symbol}</span>` +
             `<span class="${cls}">${s.label.toUpperCase()} (${s.score >= 0 ? "+" : ""}${s.score})</span></li>`;
    }).join("");
  }

  function bindControls() {
    const post = (path) => () => withButtons(true, async () => {
      try { await api(path, { method: "POST" }); }
      catch (e) { alert("Ошибка: " + e.message); }
      await refresh();
    });

    $("#btn-start").addEventListener("click", post("/api/bot/start"));
    $("#btn-pause").addEventListener("click", post("/api/bot/pause"));
    $("#btn-stop").addEventListener("click", post("/api/bot/stop"));
    $("#btn-tick").addEventListener("click", post("/api/bot/tick"));
    $("#btn-kill").addEventListener("click", () => {
      if (!confirm("KILL SWITCH остановит открытие новых сделок. Продолжить?")) return;
      post("/api/bot/kill")();
    });

    $("#btn-agent-start").addEventListener("click", post("/api/agent/start"));
    $("#btn-agent-stop").addEventListener("click", post("/api/agent/stop"));
    $("#btn-agent-tick").addEventListener("click", post("/api/agent/tick"));
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindControls();
    refresh();
    setInterval(refresh, 6000);
  });
})();
