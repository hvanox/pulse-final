"""
Тесты для Content Recommender.

Запуск: cd pulse-final/ml && python test_recommender.py
"""

from recommender import ContentRecommender


def test_recommender_initialization():
    """Тест: инициализация рекомендатора."""
    rec = ContentRecommender()
    assert rec.optimal_p == 0.65, "Optimal P должен быть 0.65"
    assert rec.utility_variance == 0.08, "Utility variance должен быть 0.08"
    print("✓ Тест 1: инициализация рекомендатора")


def test_predict_p_correct():
    """Тест: предсказание P(correct) на основе mastery и difficulty."""
    rec = ContentRecommender()
    
    # Высокий mastery + лёгкий вопрос → высокая P
    p = rec._predict_p_correct(mastery=0.8, difficulty=1)
    assert p > 0.7, f"Высокий mastery + лёгкий → P > 0.7, получили {p:.2f}"
    print(f"✓ Тест 2: высокий mastery (0.8) + difficulty 1 → P = {p:.2f}")
    
    # Низкий mastery + сложный вопрос → низкая P
    p = rec._predict_p_correct(mastery=0.2, difficulty=3)
    assert p < 0.3, f"Низкий mastery + сложный → P < 0.3, получили {p:.2f}"
    print(f"✓ Тест 3: низкий mastery (0.2) + difficulty 3 → P = {p:.2f}")


def test_learning_utility():
    """Тест: learning utility максимальна в зоне ближайшего развития."""
    rec = ContentRecommender()
    
    # P = 0.65 (optimal) → максимальная utility
    u_optimal = rec._learning_utility(0.65)
    
    # P = 0.3 (слишком сложно) → низкая utility
    u_hard = rec._learning_utility(0.3)
    
    # P = 0.95 (слишком легко) → низкая utility
    u_easy = rec._learning_utility(0.95)
    
    assert u_optimal > u_hard, "Optimal utility > hard utility"
    assert u_optimal > u_easy, "Optimal utility > easy utility"
    print(f"✓ Тест 4: utility максимальна при P=0.65")
    print(f"  P=0.65: {u_optimal:.3f}, P=0.3: {u_hard:.3f}, P=0.95: {u_easy:.3f}")


def test_recommend():
    """Тест: рекомендация контента."""
    rec = ContentRecommender()
    
    user_mastery = {
        "stocks": {"mastery": 0.3, "answers": 5, "recent_trend": "stable"},
        "etf": {"mastery": 0.7, "answers": 10, "recent_trend": "improving"},
        "risk": {"mastery": 0.1, "answers": 2, "recent_trend": "struggling"},
    }
    
    available_content = [
        {"id": "c1", "topic": "stocks", "difficulty": 1, "title": "Что такое акция"},
        {"id": "c2", "topic": "stocks", "difficulty": 2, "title": "Как выбрать акцию"},
        {"id": "c3", "topic": "etf", "difficulty": 2, "title": "ETF для начинающих"},
        {"id": "c4", "topic": "etf", "difficulty": 3, "title": "Продвинутые ETF"},
        {"id": "c5", "topic": "risk", "difficulty": 1, "title": "Основы риска"},
    ]
    
    recommendations = rec.recommend(user_mastery, available_content, top_k=3)
    
    assert len(recommendations) == 3, "Должно быть 3 рекомендации"
    assert all("utility" in r for r in recommendations), "Все должны иметь utility"
    assert all("p_correct" in r for r in recommendations), "Все должны иметь p_correct"
    
    # Struggling topic (risk) должен быть в топе
    top_topics = [r["topic"] for r in recommendations]
    assert "risk" in top_topics, "Struggling topic должен быть в рекомендациях"
    
    print("✓ Тест 5: рекомендация контента работает")
    print(f"  Топ-3: {[r['id'] for r in recommendations]}")
    for r in recommendations:
        print(f"    {r['id']} ({r['topic']}): utility={r['utility']:.3f}, P={r['p_correct']:.3f}")


def test_recommend_difficulty():
    """Тест: рекомендация сложности на основе mastery."""
    rec = ContentRecommender()
    
    assert rec.recommend_difficulty(0.2) == 1, "Mastery 0.2 → difficulty 1"
    assert rec.recommend_difficulty(0.5) == 2, "Mastery 0.5 → difficulty 2"
    assert rec.recommend_difficulty(0.8) == 3, "Mastery 0.8 → difficulty 3"
    print("✓ Тест 6: рекомендация сложности корректна")


def test_get_topic_priority():
    """Тест: определение приоритета тем."""
    rec = ContentRecommender()
    
    user_mastery = {
        "stocks": {"mastery": 0.7, "answers": 10, "recent_trend": "improving", "name": "Акции"},
        "etf": {"mastery": 0.3, "answers": 3, "recent_trend": "stable", "name": "ETF"},
        "risk": {"mastery": 0.15, "answers": 5, "recent_trend": "struggling", "name": "Риск"},
    }
    
    priorities = rec.get_topic_priority(user_mastery)
    
    assert len(priorities) == 3, "Должно быть 3 темы"
    assert priorities[0]["topic_id"] == "risk", "Struggling topic должен быть первым"
    assert priorities[0]["priority"] > priorities[1]["priority"], "Приоритеты должны убывать"
    
    print("✓ Тест 7: приоритет тем корректен")
    for p in priorities:
        print(f"  {p['topic_id']}: priority={p['priority']:.2f}, mastery={p['mastery']:.2f}, trend={p['trend']}")


def test_weak_topic_bonus():
    """Тест: слабые темы получают бонус к utility."""
    rec = ContentRecommender()
    
    # Слабая тема
    base_utility = 0.5
    modified = rec._apply_modifiers(
        base_utility=base_utility,
        mastery=0.3,  # слабая
        answers_count=5,
        trend="stable",
        difficulty=2
    )
    assert modified > base_utility, "Слабая тема должна получить бонус"
    print(f"✓ Тест 8: слабая тема получает бонус ({base_utility:.2f} → {modified:.2f})")


def test_struggling_bonus():
    """Тест: struggling темы получают дополнительный бонус."""
    rec = ContentRecommender()
    
    base_utility = 0.5
    modified = rec._apply_modifiers(
        base_utility=base_utility,
        mastery=0.5,
        answers_count=5,
        trend="struggling",  # struggling
        difficulty=2
    )
    assert modified > base_utility, "Struggling тема должна получить бонус"
    print(f"✓ Тест 9: struggling тема получает бонус ({base_utility:.2f} → {modified:.2f})")


if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование Content Recommender")
    print("=" * 60)
    
    test_recommender_initialization()
    test_predict_p_correct()
    test_learning_utility()
    test_recommend()
    test_recommend_difficulty()
    test_get_topic_priority()
    test_weak_topic_bonus()
    test_struggling_bonus()
    
    print("\n" + "=" * 60)
    print("✅ Все тесты Recommender прошли успешно!")
    print("=" * 60)
