"""
Интеграционный тест для Adaptive Learning Engine.

Тестирует полный workflow: BKT → Recommender → Spaced Repetition.

Запуск: cd pulse-final/ml && python test_integration.py
"""

import sqlite3
from datetime import datetime, timedelta
from adaptive_engine import AdaptiveLearningEngine


def create_test_db():
    """Создать тестовую БД с данными."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # Создать таблицы
    conn.executescript("""
        CREATE TABLE adaptive_answers (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            question_id TEXT,
            is_correct INTEGER NOT NULL,
            time_ms INTEGER DEFAULT 0,
            source TEXT DEFAULT 'lesson',
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE topic_mastery (
            user_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            mastery REAL DEFAULT 0.0,
            answers INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, topic)
        );
    """)
    
    # Добавить тестовые данные
    now = datetime.utcnow()
    test_data = [
        # stocks: хорошо знает (7/10 правильных)
        ("user1", "stocks", 1, 5000, (now - timedelta(days=5)).isoformat()),
        ("user1", "stocks", 1, 6000, (now - timedelta(days=4)).isoformat()),
        ("user1", "stocks", 1, 4000, (now - timedelta(days=3)).isoformat()),
        ("user1", "stocks", 0, 15000, (now - timedelta(days=2)).isoformat()),
        ("user1", "stocks", 1, 5000, (now - timedelta(days=1)).isoformat()),
        ("user1", "stocks", 1, 7000, now.isoformat()),
        ("user1", "stocks", 1, 5500, now.isoformat()),
        ("user1", "stocks", 0, 18000, now.isoformat()),
        ("user1", "stocks", 1, 6000, now.isoformat()),
        ("user1", "stocks", 0, 12000, now.isoformat()),
        
        # etf: слабо знает (2/5 правильных)
        ("user1", "etf", 0, 20000, (now - timedelta(days=10)).isoformat()),
        ("user1", "etf", 0, 25000, (now - timedelta(days=9)).isoformat()),
        ("user1", "etf", 1, 15000, (now - timedelta(days=8)).isoformat()),
        ("user1", "etf", 0, 22000, (now - timedelta(days=7)).isoformat()),
        ("user1", "etf", 1, 18000, (now - timedelta(days=6)).isoformat()),
        
        # risk: struggling (1/6 правильных, недавно)
        ("user1", "risk", 0, 30000, (now - timedelta(hours=5)).isoformat()),
        ("user1", "risk", 0, 28000, (now - timedelta(hours=4)).isoformat()),
        ("user1", "risk", 0, 35000, (now - timedelta(hours=3)).isoformat()),
        ("user1", "risk", 1, 20000, (now - timedelta(hours=2)).isoformat()),
        ("user1", "risk", 0, 32000, (now - timedelta(hours=1)).isoformat()),
        ("user1", "risk", 0, 29000, now.isoformat()),
    ]
    
    for user_id, topic, is_correct, time_ms, created_at in test_data:
        conn.execute(
            """INSERT INTO adaptive_answers (user_id, topic, is_correct, time_ms, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, topic, is_correct, time_ms, created_at)
        )
    
    conn.commit()
    return conn


def test_full_workflow():
    """Тест: полный workflow от данных до рекомендаций."""
    print("\n" + "=" * 60)
    print("Интеграционный тест: полный workflow")
    print("=" * 60)
    
    # 1. Создать engine и БД
    topics = ["stocks", "etf", "dividends", "risk", "diversification", "portfolio", "market_logic"]
    engine = AdaptiveLearningEngine(topics)
    db = create_test_db()
    
    print("\n1️⃣  Вычисление mastery из БД...")
    
    # 2. Вычислить mastery
    user_mastery = engine.compute_mastery_from_db(db, "user1")
    
    print(f"   Результаты mastery:")
    for topic, data in user_mastery.items():
        if data["answers"] > 0:
            print(f"   • {topic}: mastery={data['mastery']:.3f}, "
                  f"answers={data['answers']}, trend={data['recent_trend']}")
    
    # Проверки
    assert user_mastery["stocks"]["mastery"] > 0.5, "stocks должен иметь высокий mastery"
    assert user_mastery["etf"]["mastery"] < 0.5, "etf должен иметь низкий mastery"
    assert user_mastery["risk"]["recent_trend"] == "struggling", "risk должен быть struggling"
    print("   ✓ Mastery вычислен корректно")
    
    print("\n2️⃣  Рекомендация контента...")
    
    # 3. Рекомендовать контент
    available_content = [
        {"id": "l1", "topic": "stocks", "difficulty": 2, "title": "Анализ акций"},
        {"id": "l2", "topic": "stocks", "difficulty": 3, "title": "Продвинутый трейдинг"},
        {"id": "l3", "topic": "etf", "difficulty": 1, "title": "Что такое ETF"},
        {"id": "l4", "topic": "etf", "difficulty": 2, "title": "Выбор ETF"},
        {"id": "l5", "topic": "risk", "difficulty": 1, "title": "Основы риска"},
        {"id": "l6", "topic": "risk", "difficulty": 2, "title": "Управление рисками"},
        {"id": "l7", "topic": "dividends", "difficulty": 1, "title": "Дивиденды 101"},
    ]
    
    recommendations = engine.recommend_content(user_mastery, available_content, top_k=3)
    
    print(f"   Топ-3 рекомендации:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec['title']} ({rec['topic']}, diff={rec['difficulty']})")
        print(f"      utility={rec['utility']:.3f}, P(correct)={rec['p_correct']:.3f}")
    
    # Проверки
    assert len(recommendations) == 3, "Должно быть 3 рекомендации"
    top_topics = [r["topic"] for r in recommendations]
    assert "risk" in top_topics or "etf" in top_topics, "Слабые темы должны быть в топе"
    print("   ✓ Рекомендации сгенерированы корректно")
    
    print("\n3️⃣  Расписание повторений...")
    
    # 4. Получить расписание повторений
    schedule = engine.get_review_schedule(db, "user1", user_mastery)
    
    print(f"   Темы для повтора (по urgency):")
    for s in schedule[:3]:
        print(f"   • {s['topic_id']}: urgency={s['urgency']:.2f}, "
              f"due={s['is_due']}, interval={s['interval_days']}d")
    
    # Проверки
    assert len(schedule) > 0, "Должно быть расписание"
    assert all("urgency" in s for s in schedule), "Все должны иметь urgency"
    print("   ✓ Расписание сгенерировано корректно")
    
    print("\n4️⃣  Приоритет тем...")
    
    # 5. Получить приоритет тем
    priorities = engine.get_topic_priorities(user_mastery)
    
    print(f"   Приоритет изучения:")
    for p in priorities[:3]:
        if p["answers"] > 0:
            print(f"   • {p['topic_id']}: priority={p['priority']:.2f}, "
                  f"mastery={p['mastery']:.3f}")
    
    # Проверки
    assert priorities[0]["topic_id"] == "risk", "risk (struggling) должен быть первым"
    print("   ✓ Приоритеты определены корректно")
    
    print("\n5️⃣  Предсказание производительности...")
    
    # 6. Предсказать производительность
    p_correct_stocks = engine.predict_performance("stocks", 0.7, difficulty=2)
    p_correct_risk = engine.predict_performance("risk", 0.15, difficulty=1)
    
    print(f"   • stocks (mastery=0.7, diff=2): P(correct)={p_correct_stocks:.3f}")
    print(f"   • risk (mastery=0.15, diff=1): P(correct)={p_correct_risk:.3f}")
    
    assert p_correct_stocks > p_correct_risk, "Высокий mastery → выше P(correct)"
    print("   ✓ Предсказания корректны")
    
    print("\n6️⃣  Real-time обновление mastery...")
    
    # 7. Real-time обновление после ответа
    old_mastery = user_mastery["stocks"]["mastery"]
    new_mastery = engine.update_mastery_after_answer("stocks", old_mastery, is_correct=True)
    
    print(f"   stocks mastery: {old_mastery:.3f} → {new_mastery:.3f} (после правильного ответа)")
    assert new_mastery > old_mastery, "Mastery должен расти после правильного ответа"
    print("   ✓ Real-time обновление работает")
    
    db.close()
    
    print("\n" + "=" * 60)
    print("✅ Интеграционный тест прошёл успешно!")
    print("=" * 60)


def test_edge_cases():
    """Тест: граничные случаи."""
    print("\n" + "=" * 60)
    print("Тест граничных случаев")
    print("=" * 60)
    
    topics = ["stocks", "etf"]
    engine = AdaptiveLearningEngine(topics)
    
    # Пустой mastery
    empty_mastery = {
        "stocks": {"mastery": 0.0, "answers": 0, "recent_trend": "unknown", "avg_time_ms": 15000},
        "etf": {"mastery": 0.0, "answers": 0, "recent_trend": "unknown", "avg_time_ms": 15000},
    }
    
    # Рекомендации для нового пользователя
    content = [
        {"id": "c1", "topic": "stocks", "difficulty": 1, "title": "Intro"},
        {"id": "c2", "topic": "etf", "difficulty": 1, "title": "ETF Basics"},
    ]
    
    recs = engine.recommend_content(empty_mastery, content, top_k=2)
    assert len(recs) == 2, "Должны быть рекомендации даже для нового пользователя"
    print("✓ Рекомендации работают для нового пользователя")
    
    # Пустой контент
    recs_empty = engine.recommend_content(empty_mastery, [], top_k=5)
    assert len(recs_empty) == 0, "Пустой контент → пустые рекомендации"
    print("✓ Пустой контент обрабатывается корректно")
    
    print("\n✅ Граничные случаи обработаны корректно!")


if __name__ == "__main__":
    print("=" * 60)
    print("ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ ML ENGINE")
    print("=" * 60)
    
    test_full_workflow()
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("🎉 Все интеграционные тесты прошли!")
    print("=" * 60)
