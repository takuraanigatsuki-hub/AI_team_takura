/**
 * Проверка доступности логина и отображаемого имени (debounced).
 */
(function (global) {
    function debounce(fn, ms) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), ms);
        };
    }

    async function fetchCheck(path, param, value) {
        const trimmed = (value || '').trim();
        if (!trimmed) return { available: true, reason: '' };
        const qs = new URLSearchParams({ [param]: trimmed });
        try {
            const r = await fetch(`${path}?${qs}`, { credentials: 'same-origin' });
            if (!r.ok) return { available: false, reason: 'Не удалось проверить' };
            return r.json();
        } catch (_) {
            return { available: false, reason: 'Нет связи с сервером' };
        }
    }

    function applyHint(hintEl, data, okLabel) {
        if (!hintEl) return !!data.available;
        if (data.available) {
            hintEl.textContent = okLabel || 'Свободно';
            hintEl.className = 'auth-field-hint auth-field-hint--ok';
        } else {
            hintEl.textContent = data.reason || 'Занято';
            hintEl.className = 'auth-field-hint auth-field-hint--bad';
        }
        return !!data.available;
    }

    function bindCheck(inputEl, hintEl, path, param, okLabel) {
        if (!inputEl) return;
        inputEl.dataset.authAvailable = 'true';

        const run = debounce(async () => {
            const val = inputEl.value.trim();
            if (!val) {
                if (hintEl) {
                    hintEl.textContent = '';
                    hintEl.className = 'auth-field-hint';
                }
                inputEl.dataset.authAvailable = 'true';
                return;
            }
            if (hintEl) {
                hintEl.textContent = 'Проверка…';
                hintEl.className = 'auth-field-hint auth-field-hint--pending';
            }
            const data = await fetchCheck(path, param, val);
            const ok = applyHint(hintEl, data, okLabel);
            inputEl.dataset.authAvailable = ok ? 'true' : 'false';
        }, 450);

        inputEl.addEventListener('input', run);
    }

    function fieldsAvailable(...inputs) {
        return inputs.every((el) => !el || el.dataset.authAvailable !== 'false');
    }

    global.AuthFields = {
        bindUsernameCheck(inputEl, hintEl) {
            bindCheck(inputEl, hintEl, '/api/auth/check-username', 'u', 'Логин свободен');
        },
        bindNameCheck(inputEl, hintEl) {
            bindCheck(inputEl, hintEl, '/api/auth/check-name', 'name', 'Имя свободно');
        },
        fieldsAvailable,
        clearFieldState(inputEl, hintEl) {
            if (inputEl) {
                inputEl.value = '';
                inputEl.dataset.authAvailable = 'true';
            }
            if (hintEl) {
                hintEl.textContent = '';
                hintEl.className = 'auth-field-hint';
            }
        },
    };
})(window);
