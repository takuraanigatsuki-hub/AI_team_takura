# AI Team Room — Android Companion

Нативная оболочка для `/mobile` (Capacitor WebView). Заменяет Telegram-bot для управления с телефона; iOS — позже.

## Возможности

- Вход по email / username
- Inbox задач и статус агентов (WebSocket)
- Вкладка «Обучение» — проекты агентов на проверку
- Быстрая отправка задачи PM из телефона
- PWA: можно установить с `/mobile` без сборки APK

## Быстрый старт (PWA)

1. Откройте `https://YOUR_SERVER/mobile` на Android Chrome
2. Меню → «Установить приложение»

## Сборка APK (Capacitor)

```bash
cd android-companion
npm install
npx cap add android   # один раз
npm run sync
npx cap open android
```

В Android Studio: **Build → Generate Signed Bundle / APK**.

`capacitor.config.ts` указывает `server.url` на ваш VPS или использует bundled `webDir` (`../static` + mobile shell).

## Структура

| Файл | Назначение |
|------|------------|
| `capacitor.config.ts` | URL сервера, app id |
| `package.json` | Capacitor scripts |
| `../static/mobile.html` | UI companion |
| `../static/js/mobile.js` | API + WebSocket |

## Telegram

Bot остаётся опциональным (`TELEGRAM_*` в `.env`). Основной мобильный канал — companion.
