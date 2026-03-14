"""
Тесты для Adaptive Spaced Repetition.

Запуск: cd pulse-final/ml && python test_spaced_repetition.py
"""

from datetime import datetime, timedelta
from spaced_repetition import AdaptiveSpacedRepetition


def test_asr_initialization():
    """Тест: инициализация планировщика."""
    asr = AdaptiveSpacedRepetition()
    assert asr.max_interval == 90, "Max interval должен быть 90 дней"
    assert asr.min_interval == 1, "Min interval должен быть 1 день"
    assert len(asr.mastery_intervals) > 0, "Должны быть базовые интервалы"
    print("✓ Тест 1: инициализация планировщика")


def test_predict_interval_by_mastery():
    """Тест: интервал зависит от mastery."""
    asr = AdaptiveSpacedRepetition()
    
    # Низкий mastery → короткий интервал
    interval_low = asr.predict_interval(mastery=0.2)
    
    # Средний mastery → средний интервал
    interval_mid = asr.predict_interval(mastery=0.5)
    
    # Высокий mastery → длинный интервал
    interval_high = asr.predict_interval(mastery=0.85)
    
    assert interval_low < interval_mid < interval_high, "Интервал должен расти с mastery"
    print(f"✓ Тест 2: интервал растёт с mastery")
    print(f"  mastery 0.2 → {interval_low} дней")
    print(f"  mastery 0.5 → {interval_mid} дней")
    print(f"  mastery 0.85 → {interval_high} дней")


def test_predict_interval_with_streak():
    """Тест: streak увеличивает интервал."""
    asr = AdaptiveSpacedRepetition()
    
    # Без streak
    interval_no_streak = asr.predict_interval(mastery=0.5, consecutive_correct=0)
    
    # С streak
    interval_with_streak = asr.predict_interval(mastery=0.5, consecutive_correct=3)
    
    assert interval_with_streak > interval_no_streak, "Streak должен увеличивать интервал"
    print(f"✓ Тест 3: streak увеличивает интервал")
    print(f"  без streak: {interval_no_streak} дней")
    print(f"  streak=3: {interval_with_streak} дней")


def test_predict_interval_with_speed():
    """Тест: скорость ответов влияет на интервал."""
    asr = AdaptiveSpacedRepetition()
    
    # Быстрые ответы (уверенность) → длиннее интервал
    interval_fast = asr.predict_interval(mastery=0.5, avg_time_ms=4000)
    
    # Медленные ответы (неуверенность) → короче интервал
    interval_slow = asr.predict_interval(mastery=0.5, avg_time_ms=20000)
    
    assert interval_fast > interval_slow, "Быстрые ответы → длиннее интервал"
    print(f"✓ Тест 4: скорость влияет на интервал")
    print(f"  быстро (4s): {interval_fast} дней")
    print(f"  медленно (20s): {interval_slow} дней")


def test_is_due_for_review():
    """Тест: проверка необходимости повтора."""
    asr = AdaptiveSpacedRepetition()
    
    # Никогда не повторяли → пора
    assert asr.is_due_for_review(None, 5) == True, "None → должен быть due"
    
    # Повторяли вчера, интервал 5 дней → не пора
    yesterday = datetime.utcnow() - timedelta(days=1)
    assert asr.is_due_for_review(yesterday, 5) == False, "1 день назад, интервал 5 → не пора"
    
    # Повторяли 6 дней назад, интервал 5 дней → пора
    week_ago = datetime.utcnow() - timedelta(days=6)
    assert asr.is_due_for_review(week_ago, 5) == True, "6 дней назад, интервал 5 → пора"
    
    print("✓ Тест 5: проверка due for review работает")


def test_compute_urgency():
    """Тест: вычисление urgency score."""
    asr = AdaptiveSpacedRepetition()
    
    # Просрочено + низкий mastery → высокая urgency
    overdue_date = datetime.utcnow() - timedelta(days=10)
    urgency_high = asr.compute_urgency(overdue_date, interval_days=5, mastery=0.2)
    
    # Не просрочено + высокий mastery → низкая urgency
    recent_date = datetime.utcnow() - timedelta(days=2)
    urgency_low = asr.compute_urgency(recent_date, interval_days=5, mastery=0.8)
    
    assert urgency_high > urgency_low, "Просроченная слабая тема → высокая urgency"
    print(f"✓ Тест 6: urgency вычисляется корректно")
    print(f"  просрочено + слабо: {urgency_high:.2f}")
    print(f"  свежо + сильно: {urgency_low:.2f}")


def test_get_review_schedule():
    """Тест: получение расписания повторений."""
    asr = AdaptiveSpacedRepetition()
    
    user_mastery = {
        "stocks": {"mastery": 0.5, "answers": 10, "correct": 7, "name": "Акции"},
        "etf": {"mastery": 0.2, "answers": 5, "correct": 1, "name": "ETF"},
        "risk": {"mastery": 0.8, "answers": 15, "correct": 13, "name": "Риск"},
    }
    
    last_review_dates = {
        "stocks": datetime.utcnow() - timedelta(days=3),
        "etf": datetime.utcnow() - timedelta(days=10),
        "risk": datetime.utcnow() - timedelta(days=5),
    }
    
    schedule = asr.get_review_schedule(user_mastery, last_review_dates)
    
    assert len(schedule) == 3, "Должно быть 3 темы в расписании"
    assert all("urgency" in s for s in schedule), "Все должны иметь urgency"
    assert all("is_due" in s for s in schedule), "Все должны иметь is_due"
    
    # Самая срочная тема должна быть первой
    assert schedule[0]["urgency"] >= schedule[1]["urgency"], "Urgency должен убывать"
    
    print("✓ Тест 7: расписание повторений генерируется")
    for s in schedule:
        print(f"  {s['topic_name']}: urgency={s['urgency']:.2f}, due={s['is_due']}, interval={s['interval_days']}d")


def test_adjust_interval_after_review():
    """Тест: корректировка интервала после повтора."""
    asr = AdaptiveSpacedRepetition()
    
    # Успешный повтор → увеличить интервал
    new_interval = asr.adjust_interval_after_review(
        current_interval=5,
        was_correct=True,
        mastery_before=0.6,
        mastery_after=0.7
    )
    assert new_interval > 5, "Успешный повтор → интервал растёт"
    print(f"✓ Тест 8: успешный повтор увеличивает интервал (5 → {new_interval})")
    
    # Неуспешный повтор → уменьшить интервал
    new_interval = asr.adjust_interval_after_review(
        current_interval=5,
        was_correct=False,
        mastery_before=0.6,
        mastery_after=0.5
    )
    assert new_interval < 5, "Неуспешный повтор → интервал уменьшается"
    print(f"✓ Тест 9: неуспешный повтор уменьшает интервал (5 → {new_interval})")


def test_interval_bounds():
    """Тест: интервал всегда в пределах [min, max]."""
    asr = AdaptiveSpacedRepetition()
    
    # Очень высокий mastery + большой streak
    interval = asr.predict_interval(
        mastery=0.99,
        consecutive_correct=10,
        avg_time_ms=2000,
        last_interval_days=60
    )
    assert interval <= asr.max_interval, f"Интервал не должен превышать {asr.max_interval}"
    print(f"✓ Тест 10: интервал ограничен max ({interval} <= {asr.max_interval})")
    
    # Очень низкий mastery
    interval = asr.predict_interval(mastery=0.01)
    assert interval >= asr.min_interval, f"Интервал не должен быть меньше {asr.min_interval}"
    print(f"✓ Тест 11: интервал ограничен min ({interval} >= {asr.min_interval})")


if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование Adaptive Spaced Repetition")
    print("=" * 60)
    
    test_asr_initialization()
    test_predict_interval_by_mastery()
    test_predict_interval_with_streak()
    test_predict_interval_with_speed()
    test_is_due_for_review()
    test_compute_urgency()
    test_get_review_schedule()
    test_adjust_interval_after_review()
    test_interval_bounds()
    
    print("\n" + "=" * 60)
    print("✅ Все тесты Spaced Repetition прошли успешно!")
    print("=" * 60)
