"""
Тесты для Bayesian Knowledge Tracing модели.

Запуск: cd pulse-final/ml && python test_knowledge_tracing.py
"""

from knowledge_tracing import BayesianKnowledgeTracing, MultiTopicBKT


def test_bkt_initialization():
    """Тест: инициализация с дефолтными параметрами."""
    bkt = BayesianKnowledgeTracing()
    assert bkt.p_l0 == 0.1, "Default p_l0 должен быть 0.1"
    assert bkt.p_t == 0.3, "Default p_t должен быть 0.3"
    assert bkt.p_g == 0.25, "Default p_g должен быть 0.25"
    assert bkt.p_s == 0.1, "Default p_s должен быть 0.1"
    print("✓ Тест 1: инициализация с дефолтными параметрами")


def test_bkt_update_correct():
    """Тест: обновление после правильного ответа увеличивает P(know)."""
    bkt = BayesianKnowledgeTracing()
    p_initial = 0.5
    p_updated = bkt.update(p_initial, is_correct=True)
    assert p_updated > p_initial, "P(know) должен расти после правильного ответа"
    assert 0.01 <= p_updated <= 0.99, "P(know) должен быть в [0.01, 0.99]"
    print("✓ Тест 2: правильный ответ увеличивает P(know)")


def test_bkt_update_incorrect():
    """Тест: обновление после неправильного ответа уменьшает P(know)."""
    bkt = BayesianKnowledgeTracing()
    p_initial = 0.5
    p_updated = bkt.update(p_initial, is_correct=False)
    assert p_updated < p_initial, "P(know) должен падать после неправильного ответа"
    assert 0.01 <= p_updated <= 0.99, "P(know) должен быть в [0.01, 0.99]"
    print("✓ Тест 3: неправильный ответ уменьшает P(know)")


def test_bkt_predict_mastery():
    """Тест: предсказание mastery по истории ответов."""
    bkt = BayesianKnowledgeTracing()
    
    # Все правильные ответы → высокий mastery
    history_all_correct = [
        {"is_correct": True, "time_ms": 5000},
        {"is_correct": True, "time_ms": 4000},
        {"is_correct": True, "time_ms": 3000},
    ]
    mastery = bkt.predict_mastery(history_all_correct)
    assert mastery > 0.5, "Все правильные → mastery > 0.5"
    print(f"✓ Тест 4: все правильные → mastery = {mastery:.2f}")
    
    # Все неправильные ответы → низкий mastery
    history_all_wrong = [
        {"is_correct": False, "time_ms": 20000},
        {"is_correct": False, "time_ms": 25000},
        {"is_correct": False, "time_ms": 30000},
    ]
    mastery = bkt.predict_mastery(history_all_wrong)
    assert mastery < 0.3, "Все неправильные → mastery < 0.3"
    print(f"✓ Тест 5: все неправильные → mastery = {mastery:.2f}")


def test_bkt_predict_next_performance():
    """Тест: предсказание вероятности правильного ответа."""
    bkt = BayesianKnowledgeTracing()
    
    # Высокий mastery + лёгкий вопрос → высокая P(correct)
    p_correct = bkt.predict_next_performance(p_know=0.8, difficulty=1)
    assert p_correct > 0.6, "Высокий mastery + лёгкий вопрос → P > 0.6"
    print(f"✓ Тест 6: высокий mastery + лёгкий → P(correct) = {p_correct:.2f}")
    
    # Низкий mastery + сложный вопрос → низкая P(correct)
    p_correct = bkt.predict_next_performance(p_know=0.2, difficulty=3)
    assert p_correct < 0.4, "Низкий mastery + сложный вопрос → P < 0.4"
    print(f"✓ Тест 7: низкий mastery + сложный → P(correct) = {p_correct:.2f}")


def test_multi_topic_bkt():
    """Тест: MultiTopicBKT для нескольких тем."""
    topics = ["stocks", "etf", "risk"]
    multi_bkt = MultiTopicBKT(topics)
    
    assert len(multi_bkt.models) == 3, "Должно быть 3 модели"
    assert "stocks" in multi_bkt.models, "stocks должен быть в моделях"
    
    # Предсказание для всех тем
    histories = {
        "stocks": [{"is_correct": True, "time_ms": 5000}] * 3,
        "etf": [{"is_correct": False, "time_ms": 20000}] * 2,
        "risk": [{"is_correct": True, "time_ms": 8000}],
    }
    
    mastery_all = multi_bkt.predict_mastery_all(histories)
    assert "stocks" in mastery_all, "stocks должен быть в результатах"
    assert mastery_all["stocks"] > mastery_all["etf"], "stocks mastery > etf mastery"
    print(f"✓ Тест 8: MultiTopicBKT работает корректно")
    print(f"  stocks: {mastery_all['stocks']:.2f}, etf: {mastery_all['etf']:.2f}, risk: {mastery_all['risk']:.2f}")


def test_bkt_bounds():
    """Тест: P(know) всегда в пределах [0.01, 0.99]."""
    bkt = BayesianKnowledgeTracing()
    
    # Много правильных ответов
    p = 0.5
    for _ in range(20):
        p = bkt.update(p, is_correct=True)
    assert 0.01 <= p <= 0.99, "P(know) должен быть в [0.01, 0.99]"
    print(f"✓ Тест 9: после 20 правильных → P(know) = {p:.2f} (в пределах)")
    
    # Много неправильных ответов
    p = 0.5
    for _ in range(20):
        p = bkt.update(p, is_correct=False)
    assert 0.01 <= p <= 0.99, "P(know) должен быть в [0.01, 0.99]"
    print(f"✓ Тест 10: после 20 неправильных → P(know) = {p:.2f} (в пределах)")


if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование Bayesian Knowledge Tracing")
    print("=" * 60)
    
    test_bkt_initialization()
    test_bkt_update_correct()
    test_bkt_update_incorrect()
    test_bkt_predict_mastery()
    test_bkt_predict_next_performance()
    test_multi_topic_bkt()
    test_bkt_bounds()
    
    print("\n" + "=" * 60)
    print("✅ Все тесты BKT прошли успешно!")
    print("=" * 60)
