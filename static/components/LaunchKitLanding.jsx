/**
 * LaunchKitLanding — React UI из Figma Sites (uYRfrETGR8pcwChwLtJ6Ua).
 * Соответствует макету /startup и design tokens startup.css.
 * Переменная task задаётся в react_preview.py (placeholder __TASK__).
 */
function App() {
  const [email, setEmail] = useState('');
  const [toast, setToast] = useState('');

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3200);
  };

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleCta = (e) => {
    e.preventDefault();
    const value = email.trim();
    if (!value || !value.includes('@')) {
      showToast('Введите корректный email');
      return;
    }
    showToast('Спасибо! Мы свяжемся с вами в течение дня.');
    setEmail('');
  };

  const features = [
    { icon: '⚡', title: 'Мгновенный старт', desc: 'Готовые шаблоны и интеграции — от идеи до работающего продукта за дни, не месяцы.' },
    { icon: '📊', title: 'Аналитика в реальном времени', desc: 'Дашборды, воронки и когортный анализ. Принимайте решения на основе данных, а не догадок.' },
    { icon: '🤖', title: 'AI-автоматизация', desc: 'Умные workflow для онбординга, уведомлений и поддержки — экономьте часы каждую неделю.' },
    { icon: '🔒', title: 'Enterprise-безопасность', desc: 'SOC 2, шифрование end-to-end и гранулярные права доступа с первого дня.' },
    { icon: '🔗', title: '200+ интеграций', desc: 'Stripe, Slack, Notion, GitHub и другие — подключайте стек за пару кликов.' },
    { icon: '📈', title: 'Growth-инструменты', desc: 'A/B-тесты, реферальные программы и email-кампании для ускорения роста.' },
  ];

  const chartHeights = [45, 65, 50, 80, 70, 95, 85];

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.logo}>
          <span style={styles.logoMark}>🚀</span>
          <span>LaunchKit</span>
        </div>
        <nav style={styles.nav}>
          <a href="#features" style={styles.navLink} onClick={(e) => { e.preventDefault(); scrollTo('features'); }}>Возможности</a>
          <a href="#cta" style={styles.navLink} onClick={(e) => { e.preventDefault(); scrollTo('cta'); }}>Старт</a>
        </nav>
        <div style={styles.headerActions}>
          <button type="button" style={styles.btnGhost} onClick={() => scrollTo('features')}>Демо</button>
          <button type="button" style={styles.btnPrimary} onClick={() => scrollTo('cta')}>Начать бесплатно</button>
        </div>
      </header>

      <section style={styles.hero}>
        <div style={styles.heroGlow} />
        <div>
          <span style={styles.badge}>🚀 Для амбициозных стартапов</span>
          <h1 style={styles.heroTitle}>
            Запустите продукт<br />
            <span style={styles.gradientText}>в 10 раз быстрее</span>
          </h1>
          <p style={styles.lead}>
            LaunchKit объединяет аналитику, автоматизацию и рост в одной платформе. Сфокусируйтесь на продукте — мы возьмём на себя операционку.
          </p>
          <div style={styles.heroCta}>
            <button type="button" style={styles.btnXl} onClick={() => scrollTo('cta')}>Получить ранний доступ</button>
            <button type="button" style={styles.btnXlOutline} onClick={() => scrollTo('features')}>Смотреть демо</button>
          </div>
          <div style={styles.stats}>
            <div><strong style={styles.statValue}>2 400+</strong><span style={styles.statLabel}>стартапов</span></div>
            <div><strong style={styles.statValue}>98%</strong><span style={styles.statLabel}>uptime</span></div>
            <div><strong style={styles.statValue}>3×</strong><span style={styles.statLabel}>быстрее запуск</span></div>
          </div>
        </div>

        <div style={styles.heroVisual}>
          <div style={styles.dashboard}>
            <div style={styles.dashboardBar}>
              <span style={{ ...styles.dot, background: '#ff5f57' }} />
              <span style={{ ...styles.dot, background: '#febc2e' }} />
              <span style={{ ...styles.dot, background: '#28c840' }} />
            </div>
            <div style={styles.dashboardBody}>
              <div style={styles.dashboardHeader}>
                <h3 style={styles.dashboardTitle}>Dashboard · LaunchKit</h3>
                <span style={styles.dashboardPill}>● Live</span>
              </div>
              <div style={styles.chart}>
                {chartHeights.map((h, i) => (
                  <div key={i} style={{ ...styles.chartBar, height: `${h}%` }} />
                ))}
              </div>
              <div style={styles.metrics}>
                <div style={styles.metric}>
                  <div style={styles.metricLabel}>MRR</div>
                  <div style={styles.metricValue}>$12.4k</div>
                </div>
                <div style={styles.metric}>
                  <div style={styles.metricLabel}>Активные юзеры</div>
                  <div style={styles.metricValue}>1 847</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" style={styles.features}>
        <p style={styles.sectionLabel}>Возможности</p>
        <h2 style={styles.sectionTitle}>Всё, что нужно для роста</h2>
        <p style={styles.sectionDesc}>Инструменты, которые масштабируются вместе с вашим стартапом — от MVP до Series A.</p>
        <div style={styles.grid}>
          {features.map((f, i) => (
            <article key={i} style={styles.card}>
              <div style={styles.cardIcon}>{f.icon}</div>
              <h3 style={styles.cardTitle}>{f.title}</h3>
              <p style={styles.cardDesc}>{f.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="cta" style={styles.cta}>
        <div style={styles.ctaGlow} />
        <div style={styles.ctaContent}>
          <h2 style={styles.sectionTitle}>Готовы запустить свой стартап?</h2>
          <p style={styles.ctaText}>Присоединяйтесь к 2 400+ командам. Бесплатный план — без кредитной карты.</p>
          <form style={styles.ctaForm} onSubmit={handleCta}>
            <input
              type="email"
              style={styles.input}
              placeholder="you@startup.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <button type="submit" style={styles.btnXl}>Получить доступ</button>
          </form>
          <p style={styles.ctaNote}>14 дней Pro бесплатно · Отмена в любой момент</p>
        </div>
      </section>

      <footer style={styles.footer}>
        <span>© 2026 LaunchKit · Сделано в AI Team Room</span>
        <div style={styles.footerLinks}>
          <a href="/" style={styles.footerLink}>AI Team Room</a>
          <a href="/app" style={styles.footerLink}>Dashboard</a>
        </div>
      </footer>

      {toast && (
        <div style={styles.toast}>{toast}</div>
      )}

      {task && (
        <p style={styles.figmaNote}>Figma → React · {task}</p>
      )}
    </div>
  );
}
