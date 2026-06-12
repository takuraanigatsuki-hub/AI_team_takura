/** Startup landing — навигация, CTA-форма, плавный скролл */
(function () {
    const toast = document.getElementById('slToast');
    const form = document.getElementById('ctaForm');
    const emailInput = document.getElementById('ctaEmail');

    document.querySelectorAll('a[href^="#"]').forEach((link) => {
        link.addEventListener('click', (e) => {
            const id = link.getAttribute('href').slice(1);
            const target = document.getElementById(id);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    function showToast(msg) {
        if (!toast) return;
        toast.textContent = msg;
        toast.classList.add('visible');
        setTimeout(() => toast.classList.remove('visible'), 3200);
    }

    document.getElementById('btnHeroStart')?.addEventListener('click', () => {
        document.getElementById('cta')?.scrollIntoView({ behavior: 'smooth' });
        emailInput?.focus();
    });

    function scrollToFeatures() {
        document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
    }

    document.getElementById('btnHeroDemo')?.addEventListener('click', scrollToFeatures);
    document.getElementById('btnHeroDemo2')?.addEventListener('click', scrollToFeatures);

    document.getElementById('btnHeaderCta')?.addEventListener('click', () => {
        document.getElementById('cta')?.scrollIntoView({ behavior: 'smooth' });
        emailInput?.focus();
    });

    form?.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = emailInput?.value.trim();
        if (!email || !email.includes('@')) {
            showToast('Введите корректный email');
            return;
        }
        showToast('Спасибо! Мы свяжемся с вами в течение дня.');
        form.reset();
    });
})();
