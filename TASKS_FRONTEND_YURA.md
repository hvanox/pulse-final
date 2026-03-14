# Задачи для Юры (Frontend)

## Контекст
Админ проверил проект и дал 4 замечания. Ниже — задачи, которые касаются фронтенда.

---

## Задача 1: Автоматический деплой (CI/CD)

**Что нужно сделать:**
- Настроить GitHub Actions для автоматического деплоя фронтенда
- Создать файл `.github/workflows/deploy-frontend.yml`
- При пуше в ветку `frontend` или `main` — автоматически деплоить

**Шаги:**
1. Выбрать хостинг для фронтенда (например: Vercel, Netlify, GitHub Pages)
2. Для Vercel (рекомендуется):
   - Подключить репозиторий к Vercel
   - Настроить автодеплой из ветки `frontend`
   - Root directory: `frontend/`
   - Build command: `npm run build`
   - Output: `dist/`
3. Для GitHub Actions:
   ```yaml
   name: Deploy Frontend
   on:
     push:
       branches: [frontend, main]
       paths: ['frontend/**']
   jobs:
     build-deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: 20
         - run: cd frontend && npm ci && npm run build
         # ... шаги деплоя
   ```
4. Настроить environment variable `VITE_API_URL` для production (вместо `http://localhost:8000`)

**Файлы:** `.github/workflows/deploy-frontend.yml`, `frontend/.env.production`

---

## Задача 2: Первый тест (onboarding) — убедиться что загружается с бекенда

**Что сейчас:**
- `OnboardingScreen.jsx` уже загружает вопросы через API: `getOnboardingQuestions()` (строка 26)
- Ответы отправляются на бекенд через `submitOnboarding(answers)` (строка 73)
- Это уже работает правильно!

**Что нужно проверить/доработать:**
1. Убедиться что в коде фронтенда НИГДЕ нет захардкоженных вопросов или правильных ответов
2. Добавить состояние загрузки при получении вопросов:
   ```jsx
   // В OnboardingScreen.jsx, если questions ещё не загрузились — показать лоадер
   if (questions.length === 0) {
     return <div>Загрузка вопросов...</div>
   }
   ```
3. Добавить обработку ошибки, если бекенд недоступен:
   ```jsx
   getOnboardingQuestions()
     .then(data => setQuestions(data.questions || []))
     .catch(err => setError("Не удалось загрузить тест. Проверьте соединение."))
   ```
4. Координировать с Яриком — когда он перенесёт вопросы в БД, фронтенд не должен ломаться

**Файлы:** `frontend/src/screens/OnboardingScreen.jsx`

---

## Задача 3: Связать всё с бекендом

**Что нужно проверить и доработать:**

### 3.1 Заменить localhost на переменную окружения
В файле `frontend/src/api.js` строка 1:
```js
// БЫЛО:
const BASE = "http://localhost:8000"

// НУЖНО:
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"
```
Создать файлы:
- `frontend/.env` — `VITE_API_URL=http://localhost:8000`
- `frontend/.env.production` — `VITE_API_URL=https://pulse-api.your-domain.com`

### 3.2 Добавить обработку ошибок сети
Сейчас если бекенд не отвечает — приложение просто зависает. Нужно:
- Обернуть ВСЕ fetch-вызовы в try/catch или .catch()
- Показывать пользователю понятное сообщение об ошибке
- Добавить toast-уведомления для ошибок

### 3.3 Добавить loading-состояния
На каждом экране при загрузке данных показывать скелетон или спиннер:
- `HomeScreen.jsx` — при загрузке dashboard
- `PortfolioScreen.jsx` — при загрузке портфеля
- `LearnScreen.jsx` — при загрузке модулей
- `AchievementsScreen.jsx` — при загрузке ачивок

### 3.4 Проверить что нет "мёртвых" данных
- Убедиться что НЕТ захардкоженных данных на фронте (все данные только с API)
- Удалены экраны `FeedbackScreen`, `ProfileScreen`, `ProgressScreen`, `QuizScreen` — убедиться что нет ссылок на них

**Файлы:** `frontend/src/api.js`, все файлы в `frontend/src/screens/`

---

## Задача 4: ML — подготовить UI для отображения уровня

**Что нужно сделать:**
- Когда ML-команда подготовит модель определения уровня, нужно будет отображать результат на фронте

### 4.1 Отображение ML-уровня на HomeScreen
- На dashboard уже показывается `level_info` — нужно будет добавить блок "Уровень по ML"
- Показать график mastery по топикам (уже есть данные из `/adaptive/mastery`)

### 4.2 Рекомендации от ML
- Эндпоинт `/adaptive/recommendation` уже возвращает рекомендации
- Добавить карточку "Рекомендуем изучить" на HomeScreen на основе данных ML

### 4.3 UI для определения уровня
- После onboarding показать не только "Новичок/Базовый/Продвинутый", но и детальный разбор по ML
- Визуализация: radar-chart по темам (stocks, etf, dividends, risk, diversification, portfolio, market_logic)

**Файлы:** `frontend/src/screens/HomeScreen.jsx`, `frontend/src/screens/OnboardingScreen.jsx`

---

## Приоритеты
1. **Высокий:** Задача 3 (связать всё с беком, убрать localhost, обработка ошибок)
2. **Высокий:** Задача 2 (проверить onboarding)
3. **Средний:** Задача 1 (CI/CD для фронта)
4. **Низкий:** Задача 4 (UI для ML — ждать ML-команду)

## Ветка для работы
Работай в ветке `frontend`. После завершения — PR в `main`.
