"""
Content Recommender для адаптивного обучения.

Рекомендует оптимальный контент на основе:
- Текущего mastery пользователя по темам
- Сложности доступного контента
- "Зоны ближайшего развития" (Zone of Proximal Development)

Оптимальная сложность: P(correct) = 0.5-0.8
- Слишком легко (P > 0.9) → скучно, нет обучения
- Слишком сложно (P < 0.3) → фрустрация
"""

import math
from typing import List, Dict


class ContentRecommender:
    """
    ML-based рекомендатор контента для адаптивного обучения.
    
    Использует Item Response Theory (IRT) для предсказания P(correct)
    и максимизирует learning utility в зоне ближайшего развития.
    """

    def __init__(self, bkt_models: Dict = None):
        """
        Args:
            bkt_models: словарь {topic_id: BayesianKnowledgeTracing} (опционально)
        """
        self.bkt = bkt_models or {}
        self.optimal_p = 0.65  # оптимальная вероятность правильного ответа
        self.utility_variance = 0.08  # ширина bell curve для utility

    def recommend(
        self,
        user_mastery: Dict[str, Dict],
        available_content: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Ранжировать контент по полезности для пользователя.
        
        Args:
            user_mastery: {topic_id: {"mastery": float, "answers": int, "recent_trend": str}}
            available_content: [{"id": str, "topic": str, "difficulty": int, ...}]
            top_k: количество рекомендаций (default: 5)
            
        Returns:
            sorted list of content with scores [{...content, "p_correct": float, "utility": float}]
        """
        scored = []
        
        for content in available_content:
            topic = content.get("topic", "")
            difficulty = content.get("difficulty", 1)
            
            # Получить mastery для темы
            mastery_data = user_mastery.get(topic, {"mastery": 0.0, "answers": 0})
            mastery = mastery_data.get("mastery", 0.0)
            answers_count = mastery_data.get("answers", 0)
            trend = mastery_data.get("recent_trend", "unknown")
            
            # Предсказать вероятность правильного ответа
            p_correct = self._predict_p_correct(mastery, difficulty)
            
            # Вычислить learning utility (максимум в зоне ближайшего развития)
            utility = self._learning_utility(p_correct)
            
            # Бонусы и штрафы
            utility = self._apply_modifiers(
                utility, mastery, answers_count, trend, difficulty
            )
            
            scored.append({
                **content,
                "p_correct": round(p_correct, 3),
                "utility": round(utility, 3),
            })
        
        # Сортировка по utility (descending)
        scored.sort(key=lambda x: x["utility"], reverse=True)
        
        return scored[:top_k] if top_k else scored

    def _predict_p_correct(self, mastery: float, difficulty: int) -> float:
        """
        Предсказать вероятность правильного ответа.
        
        Использует IRT-подобную формулу (Item Response Theory):
        P(correct) = 1 / (1 + exp(-(ability - difficulty)))
        
        Args:
            mastery: уровень владения темой (0.0 - 1.0)
            difficulty: сложность вопроса (1, 2, 3)
            
        Returns:
            вероятность правильного ответа (0.0 - 1.0)
        """
        # Масштабируем mastery к ability scale [-1.5, 1.5]
        ability = mastery * 3 - 1.5
        
        # Масштабируем difficulty к параметру сложности [0, 1, 2]
        diff_param = (difficulty - 1) * 1.0
        
        # IRT logistic function
        try:
            p = 1 / (1 + math.exp(-(ability - diff_param)))
        except OverflowError:
            p = 0.0 if ability < diff_param else 1.0
        
        return max(0.01, min(0.99, p))

    def _learning_utility(self, p_correct: float) -> float:
        """
        Вычислить learning utility для данной вероятности правильного ответа.
        
        Utility максимальна в "зоне ближайшего развития" (p ≈ 0.65).
        Использует Gaussian bell curve.
        
        Args:
            p_correct: вероятность правильного ответа
            
        Returns:
            utility score (0.0 - 1.0)
        """
        # Gaussian bell curve centered at optimal_p
        exponent = -((p_correct - self.optimal_p) ** 2) / self.utility_variance
        try:
            utility = math.exp(exponent)
        except OverflowError:
            utility = 0.0
        
        return utility

    def _apply_modifiers(
        self,
        base_utility: float,
        mastery: float,
        answers_count: int,
        trend: str,
        difficulty: int
    ) -> float:
        """
        Применить модификаторы к базовой utility.
        
        Модификаторы:
        - Слабые темы (mastery < 0.5) → бонус +30%
        - Struggling trend → бонус +20%
        - Мало данных (answers < 3) → бонус +15% (exploration)
        - Improving trend + высокая сложность → бонус +10%
        
        Args:
            base_utility: базовая utility
            mastery: уровень владения темой
            answers_count: количество ответов по теме
            trend: тренд ("improving", "struggling", "stable", "unknown")
            difficulty: сложность контента
            
        Returns:
            модифицированная utility
        """
        utility = base_utility
        
        # Бонус за слабые темы — приоритет на подтягивание
        if mastery < 0.5:
            utility *= 1.3
        
        # Бонус за struggling — нужна помощь
        if trend == "struggling":
            utility *= 1.2
        
        # Exploration bonus — мало данных по теме
        if answers_count < 3:
            utility *= 1.15
        
        # Бонус за прогресс + сложность — пользователь готов к челленджу
        if trend == "improving" and difficulty >= 2:
            utility *= 1.1
        
        # Штраф за слишком лёгкий контент для сильных тем
        if mastery > 0.8 and difficulty == 1:
            utility *= 0.7
        
        return utility

    def recommend_difficulty(self, mastery: float) -> int:
        """
        Рекомендовать оптимальную сложность для данного mastery.
        
        Args:
            mastery: уровень владения темой (0.0 - 1.0)
            
        Returns:
            рекомендуемая сложность (1, 2, или 3)
        """
        if mastery < 0.3:
            return 1  # easy
        elif mastery < 0.6:
            return 2  # medium
        else:
            return 3  # hard

    def get_topic_priority(self, user_mastery: Dict[str, Dict]) -> List[Dict]:
        """
        Определить приоритет тем для изучения.
        
        Приоритет:
        1. Struggling topics (recent_trend = "struggling")
        2. Weak topics (mastery < 0.5)
        3. Under-practiced topics (answers < 5)
        4. Topics ready for advancement (mastery 0.6-0.8)
        
        Args:
            user_mastery: {topic_id: {"mastery": float, "answers": int, "recent_trend": str}}
            
        Returns:
            sorted list of topics with priority scores
        """
        priorities = []
        
        for topic_id, data in user_mastery.items():
            mastery = data.get("mastery", 0.0)
            answers = data.get("answers", 0)
            trend = data.get("recent_trend", "unknown")
            
            # Вычислить priority score
            priority = 0.0
            
            if trend == "struggling":
                priority += 10.0  # highest priority
            
            if mastery < 0.5:
                priority += 5.0 * (1 - mastery)  # слабее = выше приоритет
            
            if answers < 5:
                priority += 3.0 * (1 - answers / 5)  # exploration bonus
            
            if 0.6 <= mastery <= 0.8:
                priority += 2.0  # ready for advancement
            
            priorities.append({
                "topic_id": topic_id,
                "priority": round(priority, 2),
                "mastery": mastery,
                "answers": answers,
                "trend": trend,
                **data,
            })
        
        priorities.sort(key=lambda x: x["priority"], reverse=True)
        return priorities
