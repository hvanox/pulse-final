"""
Bayesian Knowledge Tracing (BKT) для адаптивного обучения.

BKT — это Hidden Markov Model, которая предсказывает P(знает тему)
на основе истории ответов пользователя.

Модель имеет 4 параметра:
- P(L0): начальная вероятность знания (prior)
- P(T): вероятность выучить после взаимодействия (transition)
- P(G): вероятность угадать правильный ответ, не зная (guess)
- P(S): вероятность ошибиться, зная ответ (slip)
"""

from typing import List, Dict


class BayesianKnowledgeTracing:
    """
    Bayesian Knowledge Tracing model для предсказания mastery.
    
    Использует Bayesian inference для обновления вероятности знания
    после каждого ответа пользователя.
    """

    def __init__(
        self,
        p_l0: float = 0.1,
        p_t: float = 0.3,
        p_g: float = 0.25,
        p_s: float = 0.1
    ):
        """
        Инициализация BKT модели.
        
        Args:
            p_l0: Prior — начальная вероятность знания (default: 0.1)
            p_t: Transition — вероятность выучить после взаимодействия (default: 0.3)
            p_g: Guess — вероятность угадать, не зная (default: 0.25)
            p_s: Slip — вероятность ошибиться, зная ответ (default: 0.1)
        """
        self.p_l0 = p_l0
        self.p_t = p_t
        self.p_g = p_g
        self.p_s = p_s

    def update(self, p_know: float, is_correct: bool) -> float:
        """
        Обновить P(знает) после наблюдения ответа.
        
        Использует Bayes' theorem:
        P(L|obs) = P(obs|L) * P(L) / P(obs)
        
        Args:
            p_know: текущая вероятность знания (до ответа)
            is_correct: правильный ли был ответ
            
        Returns:
            обновлённая вероятность знания (после ответа + learning transition)
        """
        if is_correct:
            # P(correct | knows) = 1 - P(slip)
            # P(correct | ~knows) = P(guess)
            p_correct_given_know = 1 - self.p_s
            p_correct_given_not_know = self.p_g
            
            # Total probability of correct answer
            p_correct = (
                p_know * p_correct_given_know +
                (1 - p_know) * p_correct_given_not_know
            )
            
            # Bayes update
            if p_correct > 0:
                p_know_updated = (p_know * p_correct_given_know) / p_correct
            else:
                p_know_updated = p_know
        else:
            # P(incorrect | knows) = P(slip)
            # P(incorrect | ~knows) = 1 - P(guess)
            p_incorrect_given_know = self.p_s
            p_incorrect_given_not_know = 1 - self.p_g
            
            # Total probability of incorrect answer
            p_incorrect = (
                p_know * p_incorrect_given_know +
                (1 - p_know) * p_incorrect_given_not_know
            )
            
            # Bayes update
            if p_incorrect > 0:
                p_know_updated = (p_know * p_incorrect_given_know) / p_incorrect
            else:
                p_know_updated = p_know

        # Learning transition: применяется только после правильного ответа
        # (если ответил неправильно, вряд ли выучил)
        if is_correct:
            p_know_after = p_know_updated + (1 - p_know_updated) * self.p_t
        else:
            p_know_after = p_know_updated

        # Clamp to [0.01, 0.99] для численной стабильности
        return min(0.99, max(0.01, p_know_after))

    def predict_mastery(self, answer_history: List[Dict]) -> float:
        """
        Предсказать текущий mastery по истории ответов.
        
        Args:
            answer_history: список ответов [{"is_correct": bool, "time_ms": int}, ...]
            
        Returns:
            предсказанный mastery score (0.0 - 1.0)
        """
        p_know = self.p_l0
        
        for ans in answer_history:
            is_correct = ans.get("is_correct", False)
            p_know = self.update(p_know, is_correct)
            
            # Time factor: быстрые правильные ответы = выше confidence
            time_ms = ans.get("time_ms", 15000)
            if is_correct and time_ms < 5000:
                # Быстрый правильный ответ — небольшой бонус к mastery
                p_know = min(0.99, p_know * 1.05)
            elif not is_correct and time_ms > 20000:
                # Медленный неправильный ответ — пользователь не уверен
                p_know = max(0.01, p_know * 0.95)
        
        return p_know

    def predict_next_performance(self, p_know: float, difficulty: int) -> float:
        """
        Предсказать вероятность правильного ответа на следующий вопрос.
        
        Args:
            p_know: текущая вероятность знания темы
            difficulty: сложность вопроса (1-3)
            
        Returns:
            вероятность правильного ответа (0.0 - 1.0)
        """
        # Базовая вероятность с учётом guess/slip
        p_correct_if_know = 1 - self.p_s
        p_correct_if_not_know = self.p_g
        
        base_p = (
            p_know * p_correct_if_know +
            (1 - p_know) * p_correct_if_not_know
        )
        
        # Adjust for difficulty (harder questions = lower P)
        difficulty_penalty = (difficulty - 1) * 0.15
        adjusted_p = base_p * (1 - difficulty_penalty)
        
        return max(0.01, min(0.99, adjusted_p))


class MultiTopicBKT:
    """
    Wrapper для управления BKT моделями по всем темам.
    
    Каждая тема имеет свою BKT модель с отдельными параметрами.
    """

    def __init__(self, topics: List[str], default_params: Dict = None):
        """
        Args:
            topics: список topic_id
            default_params: дефолтные параметры BKT (опционально)
        """
        params = default_params or {}
        self.models = {
            topic: BayesianKnowledgeTracing(
                p_l0=params.get("p_l0", 0.1),
                p_t=params.get("p_t", 0.3),
                p_g=params.get("p_g", 0.25),
                p_s=params.get("p_s", 0.1),
            )
            for topic in topics
        }

    def predict_mastery_all(self, answer_histories: Dict[str, List[Dict]]) -> Dict[str, float]:
        """
        Предсказать mastery для всех тем.
        
        Args:
            answer_histories: {topic_id: [{"is_correct": bool, "time_ms": int}, ...]}
            
        Returns:
            {topic_id: mastery_score}
        """
        result = {}
        for topic, history in answer_histories.items():
            if topic in self.models:
                result[topic] = self.models[topic].predict_mastery(history)
            else:
                result[topic] = 0.1  # default for unknown topics
        return result

    def get_model(self, topic: str) -> BayesianKnowledgeTracing:
        """Получить BKT модель для конкретной темы."""
        return self.models.get(topic, BayesianKnowledgeTracing())
