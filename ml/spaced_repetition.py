"""
Adaptive Spaced Repetition для оптимизации интервалов повторения.

Вдохновлён алгоритмом SM-2 (SuperMemo) + half-life regression.
Предсказывает оптимальный интервал до следующего повтора темы
на основе mastery, streak, и скорости ответов.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional


class AdaptiveSpacedRepetition:
    """
    ML-based spaced repetition scheduler.
    
    Адаптивно определяет интервалы повторения на основе:
    - Текущего mastery
    - Количества последовательных правильных ответов
    - Скорости ответов (confidence indicator)
    - Предыдущего интервала (для прогрессивного роста)
    """

    def __init__(self):
        """Инициализация адаптивного планировщика."""
        # Base intervals по уровням mastery (в днях)
        self.mastery_intervals = {
            0.0: 1,    # очень слабо → повтор завтра
            0.3: 2,    # слабо → через 2 дня
            0.5: 4,    # средне → через 4 дня
            0.7: 8,    # хорошо → через неделю
            0.85: 16,  # отлично → через 2 недели
            1.0: 30,   # мастер → через месяц
        }
        
        # Максимальный интервал (cap)
        self.max_interval = 90  # 3 месяца
        
        # Минимальный интервал
        self.min_interval = 1  # 1 день

    def predict_interval(
        self,
        mastery: float,
        consecutive_correct: int = 0,
        avg_time_ms: int = 15000,
        last_interval_days: int = 0
    ) -> int:
        """
        Предсказать оптимальный интервал до следующего повтора.
        
        Args:
            mastery: текущий mastery score (0.0 - 1.0)
            consecutive_correct: количество последовательных правильных ответов
            avg_time_ms: средняя скорость ответов (мс)
            last_interval_days: предыдущий интервал (для прогрессивного роста)
            
        Returns:
            рекомендуемый интервал в днях
        """
        # 1. Base interval из mastery
        base = self._get_base_interval(mastery)
        
        # 2. Streak multiplier: последовательные правильные ответы → длиннее интервал
        streak_mult = 1 + min(consecutive_correct, 5) * 0.3
        
        # 3. Speed factor: быстрые ответы = уверенность = длиннее интервал
        speed_factor = self._compute_speed_factor(avg_time_ms)
        
        # 4. Progressive growth: каждый успешный review удлиняет интервал
        if last_interval_days > 0:
            growth = min(last_interval_days * 1.5, self.max_interval)
            interval = max(base, growth)
        else:
            interval = base
        
        # Применить модификаторы
        interval = int(interval * streak_mult * speed_factor)
        
        # Clamp к [min_interval, max_interval]
        return max(self.min_interval, min(interval, self.max_interval))

    def _get_base_interval(self, mastery: float) -> int:
        """
        Получить базовый интервал из mastery score.
        
        Использует кусочно-линейную интерполяцию между ключевыми точками.
        """
        # Найти два ближайших ключа
        keys = sorted(self.mastery_intervals.keys())
        
        if mastery <= keys[0]:
            return self.mastery_intervals[keys[0]]
        if mastery >= keys[-1]:
            return self.mastery_intervals[keys[-1]]
        
        # Линейная интерполяция
        for i in range(len(keys) - 1):
            if keys[i] <= mastery <= keys[i + 1]:
                m1, m2 = keys[i], keys[i + 1]
                v1, v2 = self.mastery_intervals[m1], self.mastery_intervals[m2]
                # Interpolate
                ratio = (mastery - m1) / (m2 - m1)
                return int(v1 + (v2 - v1) * ratio)
        
        return self.mastery_intervals[0.5]  # fallback

    def _compute_speed_factor(self, avg_time_ms: int) -> float:
        """
        Вычислить speed factor из средней скорости ответов.
        
        Быстрые ответы (< 5s) → confidence → длиннее интервал
        Медленные ответы (> 15s) → uncertainty → короче интервал
        """
        if avg_time_ms < 5000:
            return 1.2  # быстро и уверенно
        elif avg_time_ms < 10000:
            return 1.0  # нормально
        elif avg_time_ms < 15000:
            return 0.9  # медленно
        else:
            return 0.8  # очень медленно, не уверен

    def is_due_for_review(
        self,
        last_review_date: Optional[datetime],
        interval_days: int
    ) -> bool:
        """
        Проверить, пора ли повторять тему.
        
        Args:
            last_review_date: дата последнего повтора (datetime или None)
            interval_days: интервал в днях
            
        Returns:
            True если пора повторять, False иначе
        """
        if last_review_date is None:
            return True  # никогда не повторяли → пора
        
        now = datetime.utcnow()
        due_date = last_review_date + timedelta(days=interval_days)
        
        return now >= due_date

    def compute_urgency(
        self,
        last_review_date: Optional[datetime],
        interval_days: int,
        mastery: float
    ) -> float:
        """
        Вычислить urgency score для темы (насколько срочно нужен повтор).
        
        Urgency растёт если:
        - Прошло больше времени чем interval
        - Mastery низкий (забывание быстрее)
        
        Args:
            last_review_date: дата последнего повтора
            interval_days: рекомендуемый интервал
            mastery: текущий mastery
            
        Returns:
            urgency score (0.0 - 10.0)
        """
        if last_review_date is None:
            return 5.0  # средняя urgency для новых тем
        
        now = datetime.utcnow()
        days_since = (now - last_review_date).days
        
        # Overdue factor: сколько дней просрочено
        overdue = max(0, days_since - interval_days)
        overdue_factor = min(overdue / interval_days, 2.0) if interval_days > 0 else 0
        
        # Forgetting factor: низкий mastery → быстрее забывается
        forgetting_factor = 1 - mastery
        
        # Urgency score
        urgency = (overdue_factor * 5) + (forgetting_factor * 3)
        
        return min(10.0, urgency)

    def get_review_schedule(
        self,
        user_mastery: Dict[str, Dict],
        last_review_dates: Dict[str, datetime]
    ) -> List[Dict]:
        """
        Получить расписание повторений для всех тем.
        
        Args:
            user_mastery: {topic_id: {"mastery": float, "answers": int, ...}}
            last_review_dates: {topic_id: datetime}
            
        Returns:
            список тем с расписанием [{topic_id, due_date, urgency, interval}]
        """
        schedule = []
        
        for topic_id, data in user_mastery.items():
            mastery = data.get("mastery", 0.0)
            answers = data.get("answers", 0)
            
            if answers == 0:
                continue  # пропускаем темы без истории
            
            last_review = last_review_dates.get(topic_id)
            
            # Предсказать интервал
            interval = self.predict_interval(
                mastery=mastery,
                consecutive_correct=data.get("correct", 0),
                avg_time_ms=data.get("avg_time_ms", 15000),
                last_interval_days=data.get("last_interval", 0)
            )
            
            # Вычислить due date
            if last_review:
                due_date = last_review + timedelta(days=interval)
            else:
                due_date = datetime.utcnow()
            
            # Вычислить urgency
            urgency = self.compute_urgency(last_review, interval, mastery)
            
            schedule.append({
                "topic_id": topic_id,
                "topic_name": data.get("name", topic_id),
                "mastery": mastery,
                "interval_days": interval,
                "due_date": due_date.isoformat(),
                "is_due": self.is_due_for_review(last_review, interval),
                "urgency": round(urgency, 2),
                "last_review": last_review.isoformat() if last_review else None,
            })
        
        # Сортировка по urgency (descending)
        schedule.sort(key=lambda x: x["urgency"], reverse=True)
        
        return schedule

    def adjust_interval_after_review(
        self,
        current_interval: int,
        was_correct: bool,
        mastery_before: float,
        mastery_after: float
    ) -> int:
        """
        Скорректировать интервал после повтора.
        
        Если повтор успешен → увеличить интервал
        Если повтор неуспешен → уменьшить интервал
        
        Args:
            current_interval: текущий интервал
            was_correct: был ли ответ правильным
            mastery_before: mastery до повтора
            mastery_after: mastery после повтора
            
        Returns:
            новый интервал
        """
        if was_correct:
            # Успешный повтор → увеличить интервал
            growth_rate = 1.5 if mastery_after > 0.7 else 1.3
            new_interval = int(current_interval * growth_rate)
        else:
            # Неуспешный повтор → уменьшить интервал
            new_interval = max(1, int(current_interval * 0.5))
        
        return max(self.min_interval, min(new_interval, self.max_interval))
