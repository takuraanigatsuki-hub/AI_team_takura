(function () {
    const cards = document.getElementById('dlCards');
    const params = new URLSearchParams(location.search);
    const reason = params.get('reason');
    const isBlocked = reason === 'desktop-only';

    if (isBlocked) {
        document.body.classList.add('dl-mode-blocked');
        document.getElementById('dlNotice')?.classList.remove('hidden');
        document.getElementById('dlFeatures')?.classList.add('hidden');
        const sub = document.getElementById('dlSub');
        if (sub) sub.textContent = 'Скачайте клиент, чтобы продолжить работу';
        document.title = 'Скачать приложение — AI Team Room';
    }

    function blockedFallbackHtml() {
        return `
            <p class="dl-error">Установщик пока недоступен на сервере.</p>
            <a class="ds-btn ds-btn-primary dl-cta" href="/">На главную</a>`;
    }

    function renderPlatforms(platforms) {
        if (!cards) return;
        const setup = platforms.find((p) => p.id === 'win-setup' && p.url);
        const portable = platforms.find((p) => p.id === 'win-portable' && p.url);

        if (isBlocked) {
            if (!setup) {
                cards.innerHTML = blockedFallbackHtml();
                return;
            }
            const size = setup.size_mb ? ` · ${setup.size_mb} MB` : '';
            cards.innerHTML = `
                <a class="ds-btn ds-btn-primary dl-cta" href="${setup.url}" download="${setup.filename || ''}">
                    ⬇ Скачать установщик${size}
                </a>
                ${portable ? `<a class="dl-cta-secondary" href="${portable.url}" download="${portable.filename || ''}">Portable .exe${portable.size_mb ? ` (${portable.size_mb} MB)` : ''}</a>` : ''}`;
            return;
        }

        cards.innerHTML = platforms.map((p) => {
            if (!p.url) {
                return `<div class="dl-card"><h3>${p.label}</h3><p>${p.hint || 'Сборка недоступна.'}</p></div>`;
            }
            const size = p.size_mb ? ` · ~${p.size_mb} MB` : '';
            const primary = p.id === 'win-setup';
            return primary
                ? `<a class="ds-btn ds-btn-primary dl-cta" href="${p.url}" download="${p.filename || ''}">⬇ ${p.label}${size}</a>`
                : `<a class="dl-cta-secondary" href="${p.url}" download="${p.filename || ''}">${p.label}${size}</a>`;
        }).join('');
    }

    if (!cards) return;

    fetch('/api/downloads/desktop/info')
        .then((r) => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then((info) => {
            if (!info.platforms?.length) {
                cards.innerHTML = isBlocked
                    ? blockedFallbackHtml()
                    : '<p class="dl-error">Файлы пока не собраны на сервере.</p>';
                return;
            }
            renderPlatforms(info.platforms);
        })
        .catch(() => {
            cards.innerHTML = isBlocked
                ? blockedFallbackHtml()
                : '<p class="dl-error">Не удалось загрузить информацию о сборке.</p>';
        });
})();
