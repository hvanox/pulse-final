# Задачи для Ярика (Backend)

## Контекст
Админ проверил проект и дал 4 замечания. Ниже — задачи, которые касаются бекенда.

---

## Задача 1: Автоматический деплой (CI/CD)

**Что нужно сделать:**
- Настроить GitHub Actions для автоматического деплоя бекенда
- Создать файл `.github/workflows/deploy-backend.yml`
- При пуше в ветку `backend` или `main` — автоматически деплоить на сервер

**Шаги:**
1. Выбрать хостинг для бекенда (например: Railway, Render, VPS)
2. Создать `Dockerfile` для бекенда:
   ```dockerfile
   FROM python:3.14-slim
   WORKDIR /app
   COPY backend/ .
   RUN pip install fastapi uvicorn pydantic
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```
3. Создать GitHub Actions workflow:
   ```yaml
   name: Deploy Backend
   on:
     push:
       branches: [backend, main]
       paths: ['backend/**']
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         # ... шаги деплоя зависят от хостинга
   ```
4. Настроить переменные окружения в GitHub Secrets (API ключи, URL БД и т.д.)
5. Убедиться, что после пуша бекенд автоматически обновляется на сервере

**Файлы:** `.github/workflows/deploy-backend.yml`, `Dockerfile`, `requirements.txt`

---

## Задача 2: Первый тест (onboarding) должен загружаться с бекенда

**Что сейчас:**
- Эндпоинт `GET /onboarding/questions` уже существует в `backend/main.py:985`
- Вопросы хранятся в `backend/onboarding.py` как Python-список `ONBOARDING_QUESTIONS`
- НО: эндпоинт отдаёт вопросы БЕЗ правильных ответов (строка 998: `"is_correct"` не передаётся)
- Проверка ответов происходит в `POST /onboarding/submit` на бекенде — это правильно

**Что нужно сделать:**
- Убедиться, что вся логика проверки ответов происходит ТОЛЬКО на бекенде
- Сейчас `POST /onboarding/submit` принимает `answers` и вызывает `score_onboarding()` на бекенде — это уже работает
- Проверить, что фронтенд НЕ хранит правильные ответы локально
- Добавить валидацию входных данных в `submit_onboarding` (проверка что `selected_index` валидный)
- Перенести вопросы из Python-файла в БД (SQLite таблица `onboarding_questions`), чтобы можно было менять без деплоя

**Файлы для изменения:**
- `backend/onboarding.py` — перенести вопросы в БД
- `backend/database.py` — добавить таблицу `onboarding_questions` и seed данных
- `backend/main.py` — обновить эндпоинты `/onboarding/questions` и `/onboarding/submit`

---

## Задача 3: Связать всё с бекендом

**Что нужно проверить и доработать:**

### 3.1 Убедиться, что ВСЕ данные приходят с бекенда
- Уроки и модули уже загружаются через API (`/v2/modules`, `/v2/lessons`, `/v2/lesson/{id}`)
- Портфель работает через API (`/portfolio`, `/trade`)
- Ачивки через `/achievements`
- Dashboard через `/dashboard`

### 3.2 Добавить обработку ошибок
- Если бекенд недоступен — показать сообщение, а не белый экран
- Добавить retry логику для критичных запросов
- Добавить health-check эндпоинт `GET /health`

### 3.3 Убрать хардкод
- В `backend/main.py:34` есть fallback `select_next_card` с `random.choice` — заменить на нормальную логику
- Начальный баланс `1000000` захардкожен в нескольких местах — вынести в конфигурацию
- `allow_origins` в CORS (`main.py:41-42`) — добавить production URL

### 3.4 Безопасность
- Пароли хранятся в открытом виде (`database.py` таблица `users`) — нужно хешировать (bcrypt)
- Нет аутентификации по токенам — `userId` передаётся в query-параметрах. Добавить JWT

**Файлы:** `backend/main.py`, `backend/database.py`

---

## Задача 4: ML — подготовить бекенд для интеграции

**Что нужно сделать:**
- Сейчас ML-модуль (`ml/selector.py`) работает только для legacy карточек
- Нужно подготовить API-эндпоинты для ML-определения уровня:

### Эндпоинт: `POST /ml/predict-level`
```python
@app.post("/ml/predict-level")
def predict_level(userId: str):
    """
    Вызвать ML модель для определения/уточнения уровня пользователя
    на основе его ответов, времени ответов, и паттернов поведения.
    """
    db = get_db()
    # Собрать фичи: ответы из adaptive_answers, onboarding_results
    # Вызвать ML модель
    # Вернуть предсказание уровня
```

### Эндпоинт: `GET /ml/features/{userId}`
- Собирает все фичи пользователя для ML модели:
  - Результаты onboarding (topic_scores)
  - История ответов (adaptive_answers)
  - Среднее время ответа
  - Процент правильных ответов по темам
  - Streak, XP, level

### Что передать ML-команде (Лёша/Назар):
- Структура таблиц: `onboarding_results`, `adaptive_answers`, `topic_mastery`
- Формат данных, которые отдаёт `/ml/features/{userId}`
- API контракт: что ML-модель принимает и возвращает

**Файлы:** `backend/main.py` (новые эндпоинты), `ml/` (интеграция)

---

## Приоритеты
1. **Высокий:** Задача 2 (onboarding с бекенда) + Задача 3 (всё связать с беком)
2. **Средний:** Задача 4 (подготовить API для ML)
3. **Средний:** Задача 1 (CI/CD) — координировать с Юрой для фронта

## Ветка для работы
Работай в ветке `backend`. После завершения — PR в `main`.
