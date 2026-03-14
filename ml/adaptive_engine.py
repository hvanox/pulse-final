"""
Adaptive Learning Engine — интеграция всех ML компонентов.

Объединяет:
- Bayesian Knowledge Tracing (BKT)
- Content Recommender
- Adaptive Spaced Repetition

Предоставляет простой API для бэкенда.
"""

from typing import List, Dict, Optional
from datetime import datetime

# Support both package import (from ml.adaptive_engine) and direct import (cd ml && python)
try:
    from ml.knowledge_tracing import BayesianKnowledgeTracing, MultiTopicBKT
    from ml.recommender import ContentRecommender
    from ml.spaced_repetition import AdaptiveSpacedRepetition
except ImportError:
    from knowledge_tracing import BayesianKnowledgeTracing, MultiTopicBKT
    from recommender import ContentRecommender
    from spaced_repetition import AdaptiveSpacedRepetition


class AdaptiveLearningEngine:
    """
    Главный класс для ML-based адаптивного обучения.

    Использует BKT для трекинга знаний, рекомендатор для выбора контента,
    и spaced repetition для оптимизации повторений.
    """

    def __init__(self, topics: List[str]):
        """
        Args:
            topics: список topic_id для трекинга
        """
        self.topics = topics
        self.multi_bkt = MultiTopicBKT(topics)
        self.recommender = ContentRecommender(bkt_models=self.multi_bkt.models)
        self.spaced_rep = AdaptiveSpacedRepetition()

    def compute_mastery_from_db(self, db, user_id: str) -> Dict[str, Dict]:
        """
        Вычислить mastery для всех тем из БД.

        Использует BKT для предсказания mastery на основе истории ответов.

        Args:
            db: database connection
            user_id: ID пользователя

        Returns:
            {topic_id: {"mastery": float, "answers": int, "recent_trend": str, ...}}
        """
        # Получить историю ответов из БД
        rows = db.execute(
            """SELECT topic, is_correct, time_ms, created_at
               FROM adaptive_answers
               WHERE user_id=?
               ORDER BY created_at ASC""",
            (user_id,)
        ).fetchall()

        # Группировка по темам
        histories = {topic: [] for topic in self.topics}
        for r in rows:
            topic = r["topic"]
            if topic in histories:
                histories[topic].append({
                    "is_correct": bool(r["is_correct"]),
                    "time_ms": r["time_ms"] or 15000,
                    "created_at": r["created_at"],
                })

        # Предсказать mastery через BKT
        mastery_scores = self.multi_bkt.predict_mastery_all(histories)

        # Добавить метаданные
        result = {}
        for topic in self.topics:
            history = histories[topic]
            mastery = mastery_scores.get(topic, 0.1)

            # Вычислить recent trend
            recent = history[-5:] if len(history) >= 5 else history
            if len(recent) >= 3:
                recent_rate = sum(1 for h in recent if h["is_correct"]) / len(recent)
                if recent_rate >= 0.8:
                    trend = "improving"
                elif recent_rate <= 0.3:
                    trend = "struggling"
                else:
                    trend = "stable"
            else:
                trend = "unknown"

            # Средняя скорость ответов
            if history:
                avg_time = sum(h["time_ms"] for h in history) / len(history)
            else:
                avg_time = 15000

            result[topic] = {
                "mastery": round(mastery, 3),
                "answers": len(history),
                "correct": sum(1 for h in history if h["is_correct"]),
                "recent_trend": trend,
                "avg_time_ms": int(avg_time),
            }

        return result

    def recommend_content(
        self,
        user_mastery: Dict[str, Dict],
        available_content: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Рекомендовать контент для пользователя.

        Args:
            user_mastery: результат compute_mastery_from_db()
            available_content: список доступного контента
            top_k: количество рекомендаций

        Returns:
            топ-k рекомендаций с utility scores
        """
        return self.recommender.recommend(user_mastery, available_content, top_k)

    def get_review_schedule(
        self,
        db,
        user_id: str,
        user_mastery: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Получить расписание повторений для пользователя.

        Args:
            db: database connection
            user_id: ID пользователя
            user_mastery: результат compute_mastery_from_db()

        Returns:
            список тем для повтора с urgency scores
        """
        # Получить даты последних повторов из БД
        last_review_dates = {}
        for topic in self.topics:
            row = db.execute(
                """SELECT created_at FROM adaptive_answers
                   WHERE user_id=? AND topic=?
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id, topic)
            ).fetchone()

            if row:
                try:
                    last_review_dates[topic] = datetime.fromisoformat(row["created_at"])
                except (ValueError, TypeError):
                    last_review_dates[topic] = None

        return self.spaced_rep.get_review_schedule(user_mastery, last_review_dates)

    def get_next_optimal_difficulty(self, topic: str, mastery: float) -> int:
        """
        Получить оптимальную сложность для следующего вопроса.

        Args:
            topic: topic_id
            mastery: текущий mastery пользователя по теме

        Returns:
            рекомендуемая сложность (1, 2, или 3)
        """
        return self.recommender.recommend_difficulty(mastery)

    def predict_performance(
        self,
        topic: str,
        mastery: float,
        difficulty: int
    ) -> float:
        """
        Предсказать вероятность правильного ответа.

        Args:
            topic: topic_id
            mastery: текущий mastery
            difficulty: сложность вопроса

        Returns:
            P(correct) (0.0 - 1.0)
        """
        bkt_model = self.multi_bkt.get_model(topic)
        return bkt_model.predict_next_performance(mastery, difficulty)

    def update_mastery_after_answer(
        self,
        topic: str,
        current_mastery: float,
        is_correct: bool
    ) -> float:
        """
        Обновить mastery после ответа (real-time update).

        Args:
            topic: topic_id
            current_mastery: текущий mastery (P(know))
            is_correct: правильный ли был ответ

        Returns:
            обновлённый mastery
        """
        bkt_model = self.multi_bkt.get_model(topic)
        return bkt_model.update(current_mastery, is_correct)

    def get_topic_priorities(self, user_mastery: Dict[str, Dict]) -> List[Dict]:
        """
        Получить приоритет тем для изучения.

        Args:
            user_mastery: результат compute_mastery_from_db()

        Returns:
            список тем отсортированных по приоритету
        """
        return self.recommender.get_topic_priority(user_mastery)


# ═══════════════════════════════════════════
# HELPER FUNCTIONS ДЛЯ БЭКЕНДА
# ═══════════════════════════════════════════

def create_engine_for_topics(topics: List[str]) -> AdaptiveLearningEngine:
    """
    Factory function для создания engine с заданными темами.

    Args:
        topics: список topic_id

    Returns:
        настроенный AdaptiveLearningEngine
    """
    return AdaptiveLearningEngine(topics)


def get_default_engine() -> AdaptiveLearningEngine:
    """
    Получить engine с дефолтными темами из onboarding.

    Returns:
        AdaptiveLearningEngine с 7 темами
    """
    default_topics = [
        "stocks",
        "etf",
        "dividends",
        "risk",
        "diversification",
        "portfolio",
        "market_logic",
    ]
    return AdaptiveLearningEngine(default_topics)
