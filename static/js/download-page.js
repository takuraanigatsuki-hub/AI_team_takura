(function () {
    const cards = document.getElementById('dlCards');
    const params = new URLSearchParams(location.search);
    const reason = params.get('reason');
    if (reason === 'desktop-only' && cards) {
        const note = document.createElement('p');
        note.className = 'lp-lead';
        note.style.marginBottom = '16px';
        note.textContent = 'Рабочая область (чат, Kanban, студия) доступна только в desktop-приложении. На сайте — кабинет, admin и поддержка.';
        cards.parentElement?.insertBefore(note, cards);
    }
    if (!cards) return;

    fetch('/api/downloads/desktop/info')
        .then((r) => r.json())
        .then((info) => {
            if (!info.platforms?.length) {
                cards.innerHTML = '<div class="dl-card"><p>Файлы пока не собраны.</p></div>';
                return;
            }
            cards.innerHTML = info.platforms.map((p) => {
                if (!p.url) {
                    return `<div class="dl-card"><h3>${p.label}</h3><p>${p.hint || 'Сборка недоступна на сервере.'}</p></div>`;
                }
                const size = p.size_mb ? ` · ~${p.size_mb} MB` : '';
                return `<div class="dl-card">
                    <h3>${p.label}</h3>
                    <p>${p.filename}${size}</p>
                    <a class="ds-btn ds-btn-primary" href="${p.url}" download="${p.filename || ''}">Скачать</a>
                </div>`;
            }).join('');
        })
        .catch(() => {
            cards.innerHTML = '<div class="dl-card"><p>Не удалось загрузить информацию о сборке.</p></div>';
        });
})();
