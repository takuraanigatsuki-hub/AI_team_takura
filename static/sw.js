/**
 * Service Worker для AI Team Room PWA
 * Обеспечивает установку на телефон и кэширование статики
 */

const CACHE_NAME = 'ai-team-room-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/main.css',
  '/static/js/app.js',
  '/static/js/studio.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// ── Установка: кэшируем статику ──────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Кэшируем по одному, чтобы не падать на отсутствующих файлах
      return Promise.allSettled(
        STATIC_ASSETS.map((url) =>
          cache.add(url).catch(() => {/* тихо пропускаем */})
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ── Активация: удаляем старые кэши ──────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Перехват запросов ────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // WebSocket и API — только сеть (никогда не кэшируем)
  if (
    url.pathname.startsWith('/ws') ||
    url.pathname.startsWith('/api/')
  ) {
    return; // браузер идёт в сеть напрямую
  }

  // CDN (Three.js и т.д.) — сначала кэш, потом сеть
  if (url.origin !== self.location.origin) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((c) => c.put(request, clone));
          }
          return response;
        }).catch(() => cached || new Response('Нет соединения', { status: 503 }));
      })
    );
    return;
  }

  // Статика: сначала кэш, при промахе — сеть + обновление кэша
  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request).then((response) => {
        if (response.ok && request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((c) => c.put(request, clone));
        }
        return response;
      }).catch(() => null);

      return cached || networkFetch || new Response('Нет соединения', { status: 503 });
    })
  );
});

// ── Push-уведомления (опционально) ──────────────────────────
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'AI Team Room', {
      body: data.body || 'Новое сообщение от команды',
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/icon-192.png',
    })
  );
});
