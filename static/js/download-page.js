(function () {
    const cards = document.getElementById('dlCards');
    const params = new URLSearchParams(location.search);
    const reason = params.get('reason');
    const isBlocked = reason === 'desktop-only';
    const isAndroid = /Android/i.test(navigator.userAgent || '');
    const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent || '');
    const isMobile = isAndroid || isIOS;

    if (isAndroid) {
        document.body.classList.add('dl-platform-android');
        const title = document.getElementById('dlTitle');
        if (title && !isBlocked) title.textContent = 'AI Team · Android';
        const features = document.getElementById('dlFeatures');
        if (features && !isBlocked) {
            features.innerHTML = `
                <li>📋 Inbox & задачи</li>
                <li>👥 Статус агентов</li>
                <li>📚 Обучение & проекты</li>
                <li>💬 Быстрая задача PM</li>`;
        }
    }
    if (isIOS) {
        document.body.classList.add('dl-platform-ios');
        const title = document.getElementById('dlTitle');
        if (title && !isBlocked) title.textContent = 'AI Team · Companion';
    }

    if (isBlocked) {
        document.body.classList.add('dl-mode-blocked');
        document.getElementById('dlNotice')?.classList.remove('hidden');
        document.getElementById('dlFeatures')?.classList.add('hidden');
        const sub = document.getElementById('dlSub');
        if (sub) {
            sub.textContent = isAndroid
                ? 'Скачайте companion для Android'
                : 'Скачайте клиент, чтобы продолжить работу';
        }
        document.title = isAndroid ? 'Скачать Android — AI Team Room' : 'Скачать приложение — AI Team Room';
    }

    const dlSub = document.getElementById('dlSub');
    if (dlSub && !isBlocked && isAndroid) {
        dlSub.textContent = 'Android · companion · управление с телефона';
    }

    function blockedFallbackHtml() {
        if (isAndroid) {
            return `
                <a class="ds-btn ds-btn-primary dl-cta" href="/mobile">🌐 Открыть веб-приложение</a>
                <p class="dl-error">APK пока собирается на сервере.</p>`;
        }
        return `
            <p class="dl-error">Установщик пока недоступен на сервере.</p>
            <a class="ds-btn ds-btn-primary dl-cta" href="/">На главную</a>`;
    }

    function pickPrimary(platforms) {
        if (isAndroid) {
            return platforms.find((p) => p.id === 'android-apk' && p.url)
                || platforms.find((p) => p.id === 'android-pwa' && p.url);
        }
        return platforms.find((p) => p.id === 'win-setup' && p.url);
    }

    function renderPlatforms(platforms) {
        if (!cards) return;
        const primary = pickPrimary(platforms);
        const portable = platforms.find((p) => p.id === 'win-portable' && p.url);
        const pwa = platforms.find((p) => p.id === 'android-pwa' && p.url);

        if (isBlocked) {
            if (!primary) {
                cards.innerHTML = blockedFallbackHtml();
                return;
            }
            const size = primary.size_mb ? ` · ${primary.size_mb} MB` : '';
            const label = isAndroid ? '📱 Скачать APK' : '⬇ Скачать установщик';
            cards.innerHTML = `
                <a class="ds-btn ds-btn-primary dl-cta" href="${primary.url}" download="${primary.filename || ''}">
                    ${label}${size}
                </a>
                ${isAndroid && pwa ? `<a class="dl-cta-secondary" href="${pwa.url}">🌐 Веб-приложение</a>` : ''}
                ${!isAndroid && portable ? `<a class="dl-cta-secondary" href="${portable.url}" download="${portable.filename || ''}">Portable .exe${portable.size_mb ? ` (${portable.size_mb} MB)` : ''}</a>` : ''}`;
            return;
        }

        const ordered = isAndroid
            ? platforms.filter((p) => p.platform === 'android' || p.id === 'android-apk' || p.id === 'android-pwa')
            : platforms.filter((p) => p.platform === 'windows' || p.id?.startsWith('win'));

        cards.innerHTML = ordered.map((p) => {
            if (!p.url) {
                return `<div class="dl-card"><h3>${p.label}</h3><p>${p.hint || 'Сборка недоступна.'}</p></div>`;
            }
            const size = p.size_mb ? ` · ~${p.size_mb} MB` : '';
            const isPrimary = p.id === (isAndroid ? 'android-apk' : 'win-setup')
                || (!isAndroid && p.id === 'win-setup')
                || (isAndroid && p.id === 'android-apk');
            const icon = isAndroid && p.id === 'android-apk' ? '📱 ' : (isPrimary ? '⬇ ' : '');
            return isPrimary
                ? `<a class="ds-btn ds-btn-primary dl-cta" href="${p.url}" download="${p.filename || ''}">${icon}${p.label}${size}</a>`
                : `<a class="dl-cta-secondary" href="${p.url}" download="${p.filename || ''}">${p.label}${size}</a>`;
        }).join('');
    }

    if (!cards) return;

    fetch('/api/downloads/info')
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
