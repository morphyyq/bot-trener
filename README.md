# Fitness AI Telegram Bot

Telegram-бот персонального AI-фитнес и wellness-помощника на Python, aiogram, FastAPI и PostgreSQL/SQLite.

## Возможности первой версии

- анкета пользователя и сохранение профиля;
- AI-план через DeepSeek, с безопасным базовым планом без API-ключа;
- главное меню с inline-кнопками;
- тренировка дня и отметка упражнений;
- питание текстом и фотографией, примерные калории и БЖУ;
- вода и сон;
- напоминания;
- AI-тренер;
- базовый прогресс;
- база данных.

## Локальный запуск

1. Установите Python 3.11+.
2. Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

3. Скопируйте `.env.example` в `.env`.
4. Создайте бота через @BotFather и вставьте токен в `BOT_TOKEN`.
5. Для AI создайте ключ DeepSeek и вставьте его в `DEEPSEEK_API_KEY`.
6. Запустите:

```bash
uvicorn app.main:app --reload --port 8000
```

Локальный запуск через webhook без HTTPS не принимает сообщения от Telegram. Для первого теста можно временно добавить polling-режим, либо сразу развернуть на Render.

## Render

1. Загрузите проект в GitHub.
2. В Render выберите New → Web Service → подключите репозиторий.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Добавьте переменные:
   - `BOT_TOKEN`
   - `DEEPSEEK_API_KEY`
   - `DATABASE_URL`
   - `WEBHOOK_URL`, равный URL сервиса Render без завершающего `/`
   - `WEBHOOK_SECRET`
   - `SCHEDULER_SECRET`
6. После первого запуска откройте `/health`. Если всё в порядке, в ответе будет `status: ok`.

## Важные ограничения

- Оценка питания по фотографии приблизительная.
- Бот не ставит диагнозы и не назначает лекарства.
- Для несовершеннолетних калории не должны трактоваться как строгая диета.
- Бесплатный Render может засыпать, поэтому точность напоминаний на бесплатном сервисе не гарантируется. Для более надёжных уведомлений нужен внешний бесплатный cron, который периодически вызывает `/scheduler/tick` с заголовком `X-Scheduler-Secret`.
- Не публикуйте `.env` и API-ключи в GitHub.
