# Задачи для Лёши (ML)

## Контекст
Админ проверил проект и дал замечание: **"Что с ML? Подключить. Как определяется уровень?"**
Лёша и Назар работают над ML-частью вместе. Ниже — задачи для Лёши.

---

## Текущее состояние ML в проекте

### Что уже есть:
1. **`ml/selector.py`** — простой селектор карточек по сложности (legacy, без ML):
   - Если ответил правильно → сложность +1
   - Если неправильно → сложность -1
   - Это НЕ машинное обучение, просто правила

2. **`backend/onboarding.py`** — определение уровня по onboarding-тесту:
   - 10 вопросов с весами и сложностью
   - Скоринг: взвешенная сумма + time_bonus + exponential decay
   - 3 уровня: novice (0-39%), basic (40-69%), advanced (70-100%)
   - Это **rule-based**, не ML

3. **Adaptive Learning Engine** (`backend/onboarding.py:444`):
   - Трекинг mastery по 7 темам: stocks, etf, dividends, risk, diversification, portfolio, market_logic
   - Spaced repetition с exponential decay (half-life ~14 дней)
   - Рекомендации на основе слабых тем
   - Тоже rule-based

### Данные в БД (доступны для обучения):
- `onboarding_results` — результаты onboarding-теста (level_id, score, topic_scores JSON)
- `adaptive_answers` — все ответы пользователя (topic, is_correct, time_ms, source)
- `topic_mastery` — кэш mastery по темам (mastery 0.0-1.0, answers count)
- `interactions` — legacy ответы на карточки (card_id, is_correct, difficulty)
- `lesson_completions` — какие уроки прошёл
- `progress` — streak, xp, level, balance

---

## Задача: Создать ML модель определения уровня

### Цель
Заменить rule-based скоринг на ML-модель, которая точнее определяет уровень пользователя и адаптирует обучение.

### Шаг 1: Сбор и подготовка данных (Feature Engineering)

**Фичи для модели:**

| Фича | Откуда | Тип |
|-------|--------|-----|
| score (общий % правильных) | onboarding_results.score | float 0-1 |
| topic_scores по каждой теме (7 штук) | onboarding_results.topic_scores | float 0-1 |
| среднее время ответа | adaptive_answers.time_ms | int ms |
| кол-во "не знаю" ответов | onboarding answers с is_skip | int |
| паттерн: правильные на лёгких, ошибки на сложных | adaptive_answers + question difficulty | binary |
| streak (серия правильных ответов) | вычислить из adaptive_answers | int |
| скорость улучшения (тренд) | adaptive_answers over time | float |
| кол-во пройденных уроков | lesson_completions count | int |

**Целевая переменная (target):**
- `level_id`: novice / basic / advanced (classification)
- Или `mastery_score`: 0.0-1.0 (regression)

### Шаг 2: Выбор модели

**Рекомендуемые подходы:**

1. **Gradient Boosting (XGBoost / LightGBM)** — для классификации уровня
   - Хорошо работает с табличными данными
   - Не нужно много данных для нормального результата
   - Интерпретируемый (feature importance)

2. **Bayesian Knowledge Tracing (BKT)** — для оценки mastery по темам
   - Стандартный подход в EdTech
   - Моделирует: P(знает), P(угадал), P(ошибся), P(выучил)
   - Библиотека: `pyBKT`

3. **Простой вариант (для начала):** Logistic Regression
   - Быстро обучить, легко интерпретировать
   - Хороший baseline перед более сложными моделями

### Шаг 3: Реализация

**Структура файлов:**
```
ml/
├── __init__.py          # уже есть
├── selector.py          # уже есть (legacy)
├── model.py             # НОВЫЙ: ML модель определения уровня
├── features.py          # НОВЫЙ: сбор и подготовка фичей
├── train.py             # НОВЫЙ: обучение модели
├── data/
│   └── training_data.csv  # данные для обучения (сгенерить или собрать)
└── models/
    └── level_predictor.pkl  # сохранённая модель
```

**Файл `ml/features.py`:**
```python
def extract_features(db, user_id: str) -> dict:
    """
    Извлечь фичи пользователя для ML модели.
    Вызывается из backend/main.py через эндпоинт /ml/features/{userId}
    """
    features = {}

    # 1. Onboarding score
    onb = db.execute(
        "SELECT score, topic_scores FROM onboarding_results WHERE user_id=?",
        (user_id,)
    ).fetchone()
    features["onboarding_score"] = onb["score"] if onb else 0

    # 2. Per-topic scores (7 фичей)
    if onb and onb["topic_scores"]:
        topics = json.loads(onb["topic_scores"])
        for topic_id in ["stocks", "etf", "dividends", "risk",
                         "diversification", "portfolio", "market_logic"]:
            features[f"topic_{topic_id}"] = topics.get(topic_id, {}).get("score", 0)

    # 3. Answer patterns
    answers = db.execute(
        "SELECT is_correct, time_ms FROM adaptive_answers WHERE user_id=?",
        (user_id,)
    ).fetchall()

    if answers:
        features["avg_time_ms"] = sum(a["time_ms"] for a in answers) / len(answers)
        features["correct_rate"] = sum(a["is_correct"] for a in answers) / len(answers)
        features["total_answers"] = len(answers)

    # 4. Lessons completed
    lessons = db.execute(
        "SELECT COUNT(*) as cnt FROM lesson_completions WHERE user_id=?",
        (user_id,)
    ).fetchone()
    features["lessons_completed"] = lessons["cnt"]

    return features
```

**Файл `ml/model.py`:**
```python
import pickle
import numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "models" / "level_predictor.pkl"

class LevelPredictor:
    def __init__(self):
        self.model = None
        self.load()

    def load(self):
        if MODEL_PATH.exists():
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)

    def predict(self, features: dict) -> dict:
        """
        Предсказать уровень пользователя.
        Returns: {"level": "novice"|"basic"|"advanced", "confidence": 0.0-1.0, "details": {...}}
        """
        if self.model is None:
            # Fallback на rule-based
            return self._rule_based(features)

        # Подготовить вектор фичей
        X = self._features_to_array(features)
        prediction = self.model.predict(X)
        probabilities = self.model.predict_proba(X)

        levels = ["novice", "basic", "advanced"]
        return {
            "level": levels[prediction[0]],
            "confidence": float(max(probabilities[0])),
            "probabilities": {
                levels[i]: float(probabilities[0][i])
                for i in range(len(levels))
            }
        }

    def _rule_based(self, features: dict) -> dict:
        """Fallback: текущая rule-based логика."""
        score = features.get("onboarding_score", 0)
        if score >= 0.7:
            return {"level": "advanced", "confidence": 0.5, "method": "rule-based"}
        elif score >= 0.4:
            return {"level": "basic", "confidence": 0.5, "method": "rule-based"}
        else:
            return {"level": "novice", "confidence": 0.5, "method": "rule-based"}
```

### Шаг 4: Генерация тренировочных данных

Пока реальных пользователей мало, нужно сгенерировать синтетические данные:
```python
# ml/train.py — генерация и обучение
def generate_synthetic_data(n_samples=1000):
    """
    Сгенерировать синтетические данные для обучения.
    3 типа пользователей: novice, basic, advanced
    с реалистичными паттернами ответов.
    """
    # Novice: score 0-0.4, slow answers, many skips
    # Basic: score 0.4-0.7, medium speed, few skips
    # Advanced: score 0.7-1.0, fast answers, no skips
```

---

## Координация с Назаром

Лёша и Назар работают вместе. Предлагаемое разделение:
- **Лёша:** Feature engineering + модель определения уровня (classification)
- **Назар:** Adaptive learning + модель рекомендации контента

Подробнее — см. файл `TASKS_ML_NAZAR.md`

---

## Координация с Яриком (Backend)

Ярик подготовит API-эндпоинты:
- `GET /ml/features/{userId}` — вернёт собранные фичи
- `POST /ml/predict-level` — вызовет ML модель

Тебе нужно:
1. Определить финальный формат фичей (какие поля, типы данных)
2. Определить формат ответа модели
3. Передать Ярику, чтобы он подключил модель в эндпоинт

---

## Приоритеты
1. **Высокий:** Feature engineering (`ml/features.py`) — это основа для всего
2. **Высокий:** Baseline модель (хотя бы Logistic Regression)
3. **Средний:** Генерация синтетических данных для обучения
4. **Средний:** Улучшение модели (XGBoost)

## Ветка для работы
Работай в ветке `ml`. После завершения — PR в `main`.
