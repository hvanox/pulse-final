# Задачи для Назара (ML)

## Контекст
Админ проверил проект и дал замечание: **"Что с ML? Подключить. Как определяется уровень?"**
Назар и Лёша работают над ML-частью вместе. Ниже — задачи для Назара.

---

## Текущее состояние

### Что уже есть (rule-based, не ML):
- **Adaptive Learning Engine** в `backend/onboarding.py`:
  - 7 тем: stocks, etf, dividends, risk, diversification, portfolio, market_logic
  - Mastery трекинг с exponential decay (half-life ~14 дней)
  - Spaced repetition (интервалы: 1/2/5/14 дней в зависимости от mastery)
  - Рекомендации: слабые темы → повтор, сильные → продвижение
- **Legacy selector** в `ml/selector.py`:
  - Простое правило: правильно → сложность +1, неправильно → -1

### Данные в БД:
- `adaptive_answers` — topic, is_correct, time_ms, source (onboarding/lesson), created_at
- `topic_mastery` — mastery 0.0-1.0, answers count по каждой теме
- `lesson_completions` — какие уроки прошёл, xp_earned
- `onboarding_results` — level_id, score, topic_scores JSON

---

## Задача: ML-модель адаптивного обучения и рекомендации контента

### Цель
Заменить rule-based рекомендации на ML-модель, которая лучше определяет:
1. Какой контент показать пользователю следующим
2. Когда нужен повтор (spaced repetition на основе ML)
3. Оптимальную сложность для каждого пользователя

---

### Шаг 1: Knowledge Tracing (BKT — Bayesian Knowledge Tracing)

**Что это:**
Модель, которая предсказывает P(знает тему) на основе истории ответов.

**4 параметра BKT:**
- `P(L0)` — начальная вероятность знания (prior)
- `P(T)` — вероятность выучить после взаимодействия (transition)
- `P(G)` — вероятность угадать (guess)
- `P(S)` — вероятность ошибиться, зная ответ (slip)

**Реализация:**
```python
# ml/knowledge_tracing.py

class BayesianKnowledgeTracing:
    def __init__(self, p_l0=0.1, p_t=0.3, p_g=0.25, p_s=0.1):
        self.p_l0 = p_l0  # Prior: вероятность знания до обучения
        self.p_t = p_t     # Transition: вероятность выучить
        self.p_g = p_g     # Guess: вероятность угадать
        self.p_s = p_s     # Slip: вероятность ошибиться зная

    def update(self, p_know: float, is_correct: bool) -> float:
        """
        Обновить P(знает) после ответа.

        Bayes update:
        P(L|obs) = P(obs|L) * P(L) / P(obs)
        """
        if is_correct:
            # P(correct | knows) = 1 - P(slip)
            # P(correct | ~knows) = P(guess)
            p_correct_given_know = 1 - self.p_s
            p_correct_given_not_know = self.p_g
            p_correct = p_know * p_correct_given_know + (1 - p_know) * p_correct_given_not_know
            p_know_updated = p_know * p_correct_given_know / p_correct
        else:
            # P(incorrect | knows) = P(slip)
            # P(incorrect | ~knows) = 1 - P(guess)
            p_incorrect_given_know = self.p_s
            p_incorrect_given_not_know = 1 - self.p_g
            p_incorrect = p_know * p_incorrect_given_know + (1 - p_know) * p_incorrect_given_not_know
            p_know_updated = p_know * p_incorrect_given_know / p_incorrect

        # Learning transition: even if didn't know before, might learn
        p_know_after = p_know_updated + (1 - p_know_updated) * self.p_t

        return min(0.99, max(0.01, p_know_after))

    def predict_mastery(self, answer_history: list) -> float:
        """
        Предсказать текущий mastery по истории ответов.
        answer_history: [{"is_correct": bool, "time_ms": int}, ...]
        """
        p_know = self.p_l0
        for ans in answer_history:
            p_know = self.update(p_know, ans["is_correct"])
        return p_know
```

### Шаг 2: Content Recommendation Model

**Что нужно предсказывать:**
Для каждого доступного урока/вопроса → P(пользователь ответит правильно)

**Оптимальная сложность:**
- Слишком легко (P > 0.9) → скучно, нет обучения
- Слишком сложно (P < 0.3) → фрустрация
- "Зона ближайшего развития" (P = 0.5-0.8) → максимальное обучение

**Реализация:**
```python
# ml/recommender.py

class ContentRecommender:
    def __init__(self, bkt_models: dict):
        """bkt_models: {topic_id: BayesianKnowledgeTracing}"""
        self.bkt = bkt_models

    def recommend(self, user_mastery: dict, available_content: list) -> list:
        """
        Ранжировать контент по полезности для пользователя.

        user_mastery: {topic_id: {"mastery": float, "answers": int}}
        available_content: [{"id": str, "topic": str, "difficulty": int}]

        Returns: sorted list of content with scores
        """
        scored = []
        for content in available_content:
            topic = content.get("topic", "")
            mastery = user_mastery.get(topic, {}).get("mastery", 0)
            difficulty = content.get("difficulty", 1)

            # Предсказанная вероятность правильного ответа
            p_correct = self._predict_p_correct(mastery, difficulty)

            # Полезность максимальна в "зоне ближайшего развития"
            # Bell curve centered at p=0.65
            utility = self._learning_utility(p_correct)

            # Бонус за слабые темы
            if mastery < 0.5:
                utility *= 1.3

            scored.append({
                **content,
                "p_correct": round(p_correct, 2),
                "utility": round(utility, 2),
            })

        # Сортируем по полезности (descending)
        scored.sort(key=lambda x: x["utility"], reverse=True)
        return scored

    def _predict_p_correct(self, mastery: float, difficulty: int) -> float:
        """Предсказать вероятность правильного ответа."""
        # IRT-подобная формула
        # mastery высокий + difficulty низкий → высокая P
        ability = mastery * 3 - 1.5  # масштабируем к [-1.5, 1.5]
        diff_param = (difficulty - 1) * 1.0  # 0, 1, 2
        import math
        return 1 / (1 + math.exp(-(ability - diff_param)))

    def _learning_utility(self, p_correct: float) -> float:
        """
        Полезность для обучения.
        Максимум при p=0.65 (зона ближайшего развития).
        """
        import math
        optimal = 0.65
        return math.exp(-((p_correct - optimal) ** 2) / 0.08)
```

### Шаг 3: Spaced Repetition с ML

Заменить фиксированные интервалы (1/2/5/14 дней) на адаптивные:

```python
# ml/spaced_repetition.py

class AdaptiveSpacedRepetition:
    """
    ML-based spaced repetition (вдохновлён SM-2 + half-life regression).

    Предсказывает оптимальный интервал повтора для каждой темы.
    """

    def predict_interval(self, mastery: float, consecutive_correct: int,
                          avg_time_ms: int, last_interval_days: int) -> int:
        """
        Предсказать оптимальный интервал до следующего повтора.

        Если mastery высокий и ответы быстрые → длинный интервал
        Если mastery низкий или ответы медленные → короткий интервал
        """
        # Base interval from mastery
        if mastery < 0.3:
            base = 1
        elif mastery < 0.5:
            base = 2
        elif mastery < 0.7:
            base = 4
        elif mastery < 0.85:
            base = 8
        else:
            base = 16

        # Consecutive correct multiplier
        streak_mult = 1 + min(consecutive_correct, 5) * 0.3

        # Speed factor: fast answers = more confident
        speed_factor = 1.0
        if avg_time_ms < 5000:
            speed_factor = 1.2  # fast and confident
        elif avg_time_ms > 15000:
            speed_factor = 0.8  # slow, unsure

        # Growth: each successful review doubles interval
        growth = min(last_interval_days * 1.5, 90) if last_interval_days > 0 else base

        interval = max(1, int(base * streak_mult * speed_factor))
        return min(interval, 90)  # Cap at 90 days

    def is_due_for_review(self, last_review_date, interval_days) -> bool:
        """Проверить, пора ли повторять тему."""
        from datetime import datetime, timedelta
        if last_review_date is None:
            return True
        now = datetime.utcnow()
        due_date = last_review_date + timedelta(days=interval_days)
        return now >= due_date
```

---

### Шаг 4: Структура файлов

```
ml/
├── __init__.py              # уже есть
├── selector.py              # уже есть (legacy)
├── knowledge_tracing.py     # НОВЫЙ (Назар): BKT модель
├── recommender.py           # НОВЫЙ (Назар): рекомендация контента
├── spaced_repetition.py     # НОВЫЙ (Назар): адаптивные интервалы
├── features.py              # НОВЫЙ (Лёша): сбор фичей
├── model.py                 # НОВЫЙ (Лёша): модель уровня
├── train.py                 # НОВЫЙ (Лёша): обучение
└── models/
    └── level_predictor.pkl  # сохранённая модель (Лёша)
```

---

## Координация с Лёшей

| Лёша | Назар |
|------|-------|
| Feature engineering | Knowledge Tracing (BKT) |
| Модель определения уровня | Рекомендация контента |
| Classification (novice/basic/advanced) | Spaced repetition с ML |
| `ml/features.py`, `ml/model.py`, `ml/train.py` | `ml/knowledge_tracing.py`, `ml/recommender.py`, `ml/spaced_repetition.py` |

**Общий формат данных:**
- Фичи берутся из `ml/features.py` (Лёша делает, Назар использует)
- Mastery из BKT (Назар делает) используется для уровня (Лёша использует)

---

## Координация с Яриком (Backend)

Ярик подготовит эндпоинты:
- `GET /ml/features/{userId}` — вернёт фичи для модели
- `POST /ml/predict-level` — вызовет модель Лёши
- `GET /adaptive/recommendation` — вызовет рекомендатор Назара (эндпоинт уже есть, нужно подключить ML)

Назару нужно:
1. Определить формат входных данных для `recommender.recommend()`
2. Определить формат выходных данных
3. Передать Ярику для интеграции

---

## Приоритеты
1. **Высокий:** Knowledge Tracing (`ml/knowledge_tracing.py`) — основа адаптивности
2. **Высокий:** Content Recommender (`ml/recommender.py`)
3. **Средний:** Spaced Repetition (`ml/spaced_repetition.py`)
4. **Низкий:** Настройка параметров BKT под реальные данные

## Ветка для работы
Работай в ветке `ml-nazar`. После завершения — PR в `main`.
