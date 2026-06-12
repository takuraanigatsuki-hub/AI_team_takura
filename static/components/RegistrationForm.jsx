/**
 * RegistrationForm — React-компонент регистрации.
 * Используется в React Preview (Соня) и как эталон для UI-задач.
 * Переменная task задаётся в react_preview.py (placeholder __TASK__).
 */
function App() {
  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [user, setUser] = useState(null);

  const setField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: '' }));
    setServerError('');
  };

  const validate = () => {
    const next = {};
    const name = form.name.trim();
    const email = form.email.trim().toLowerCase();

    if (!name) next.name = 'Введите имя';
    if (!email || !email.includes('@')) next.email = 'Некорректный email';
    if (form.password.length < 6) next.password = 'Минимум 6 символов';
    if (form.password !== form.confirmPassword) next.confirmPassword = 'Пароли не совпадают';

    return next;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const next = validate();
    if (Object.keys(next).length) {
      setErrors(next);
      return;
    }

    setLoading(true);
    setServerError('');

    try {
      const r = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          email: form.email.trim().toLowerCase(),
          password: form.password,
          name: form.name.trim(),
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Ошибка регистрации');
      setUser(data.user);
      setDone(true);
    } catch (err) {
      setServerError(err.message || 'Не удалось зарегистрироваться');
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div style={styles.page}>
        <div style={styles.card}>
          <div style={styles.successIcon}>✓</div>
          <h1 style={styles.title}>Аккаунт создан!</h1>
          <p style={styles.sub}>
            Добро пожаловать, {user?.name || form.name.trim()}. Теперь можно перейти в приложение.
          </p>
          <a href="/app?setup=1" style={{ ...styles.btn, ...styles.btnLink }}>
            Перейти в AI Team Room
          </a>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <p style={styles.badge}>AI Team Room</p>
        <h1 style={styles.title}>Регистрация</h1>
        <p style={styles.sub}>{task}</p>

        <form onSubmit={handleSubmit} noValidate>
          <label style={styles.label} htmlFor="reg-name">Имя</label>
          <input
            id="reg-name"
            style={{ ...styles.input, ...(errors.name ? styles.inputError : {}) }}
            type="text"
            placeholder="Алексей"
            value={form.name}
            onChange={(e) => setField('name', e.target.value)}
            autoComplete="name"
          />
          {errors.name && <p style={styles.fieldError}>{errors.name}</p>}

          <label style={styles.label} htmlFor="reg-email">Email</label>
          <input
            id="reg-email"
            style={{ ...styles.input, ...(errors.email ? styles.inputError : {}) }}
            type="email"
            placeholder="you@company.com"
            value={form.email}
            onChange={(e) => setField('email', e.target.value)}
            autoComplete="email"
          />
          {errors.email && <p style={styles.fieldError}>{errors.email}</p>}

          <label style={styles.label} htmlFor="reg-password">Пароль</label>
          <input
            id="reg-password"
            style={{ ...styles.input, ...(errors.password ? styles.inputError : {}) }}
            type="password"
            placeholder="минимум 6 символов"
            value={form.password}
            onChange={(e) => setField('password', e.target.value)}
            autoComplete="new-password"
            minLength={6}
          />
          {errors.password && <p style={styles.fieldError}>{errors.password}</p>}

          <label style={styles.label} htmlFor="reg-confirm">Подтверждение пароля</label>
          <input
            id="reg-confirm"
            style={{ ...styles.input, ...(errors.confirmPassword ? styles.inputError : {}) }}
            type="password"
            placeholder="повторите пароль"
            value={form.confirmPassword}
            onChange={(e) => setField('confirmPassword', e.target.value)}
            autoComplete="new-password"
          />
          {errors.confirmPassword && <p style={styles.fieldError}>{errors.confirmPassword}</p>}

          {serverError && <p style={styles.serverError}>{serverError}</p>}

          <button
            type="submit"
            style={{ ...styles.btn, ...(loading ? styles.btnDisabled : {}) }}
            disabled={loading}
          >
            {loading ? 'Создаём аккаунт…' : 'Создать аккаунт'}
          </button>
        </form>

        <p style={styles.footer}>
          Уже есть аккаунт?{' '}
          <a href="/?auth=login" style={styles.link}>
            Войти
          </a>
        </p>
      </div>
    </div>
  );
}
