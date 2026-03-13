# Запуск: cd backend/ml && python test_selector.py

from selector import select_next_card

CARDS = [
    {"id": 1, "difficulty": 1, "topic": "акции",    "text": "q1", "options": [], "correct_index": 0},
    {"id": 2, "difficulty": 2, "topic": "акции",    "text": "q2", "options": [], "correct_index": 0},
    {"id": 3, "difficulty": 3, "topic": "акции",    "text": "q3", "options": [], "correct_index": 0},
    {"id": 4, "difficulty": 1, "topic": "бюджет",   "text": "q4", "options": [], "correct_index": 0},
    {"id": 5, "difficulty": 2, "topic": "бюджет",   "text": "q5", "options": [], "correct_index": 0},
]

# Тест 1: новый пользователь → difficulty 1
c = select_next_card("u1", [], CARDS)
assert c["difficulty"] == 1, f"[FAIL] Тест 1: ожидали difficulty=1, получили {c['difficulty']}"
print("✓ Тест 1: новый пользователь → difficulty 1")

# Тест 2: правильный ответ на difficulty 1 → difficulty 2
history = [{"card_id": 1, "is_correct": True, "difficulty": 1}]
c = select_next_card("u1", history, CARDS)
assert c["difficulty"] == 2, f"[FAIL] Тест 2: ожидали difficulty=2, получили {c['difficulty']}"
print("✓ Тест 2: правильный ответ → сложнее")

# Тест 3: неправильный ответ на difficulty 2 → difficulty 1
history = [{"card_id": 2, "is_correct": False, "difficulty": 2}]
c = select_next_card("u1", history, CARDS)
assert c["difficulty"] == 1, f"[FAIL] Тест 3: ожидали difficulty=1, получили {c['difficulty']}"
print("✓ Тест 3: неправильный ответ → проще")

# Тест 4: difficulty не падает ниже 1
history = [{"card_id": 4, "is_correct": False, "difficulty": 1}]
c = select_next_card("u1", history, CARDS)
assert c["difficulty"] >= 1, f"[FAIL] Тест 4: difficulty не может быть меньше 1"
print("✓ Тест 4: difficulty не падает ниже 1")

# Тест 5: difficulty не растёт выше 3
history = [{"card_id": 3, "is_correct": True, "difficulty": 3}]
c = select_next_card("u1", history, CARDS)
assert c["difficulty"] <= 3, f"[FAIL] Тест 5: difficulty не может быть больше 3"
print("✓ Тест 5: difficulty не растёт выше 3")

# Тест 6: уже показанные карточки не повторяются
history = [{"card_id": 1, "is_correct": True, "difficulty": 1}]
c = select_next_card("u1", history, CARDS)
assert c["id"] != 1, f"[FAIL] Тест 6: карточка 1 уже была, не должна повторяться"
print("✓ Тест 6: уже показанные карточки не повторяются")

# Тест 7: все карточки показаны → возвращает хоть какую-то карточку
history = [
    {"card_id": 1, "is_correct": True, "difficulty": 1},
    {"card_id": 2, "is_correct": True, "difficulty": 2},
    {"card_id": 3, "is_correct": True, "difficulty": 3},
    {"card_id": 4, "is_correct": True, "difficulty": 1},
    {"card_id": 5, "is_correct": True, "difficulty": 2},
]
c = select_next_card("u1", history, CARDS)
assert c is not None, "[FAIL] Тест 7: должна вернуть карточку даже если все показаны"
print("✓ Тест 7: все карточки показаны → сброс, возвращает карточку")

# Тест 8: нет карточки нужного difficulty → ближайшая
cards_only_1_and_3 = [
    {"id": 10, "difficulty": 1, "topic": "t", "text": "q", "options": [], "correct_index": 0},
    {"id": 11, "difficulty": 3, "topic": "t", "text": "q", "options": [], "correct_index": 0},
]
# Хотим difficulty 2, но есть только 1 и 3
history = [{"card_id": 10, "is_correct": True, "difficulty": 1}]  # хотим 2
c = select_next_card("u1", history, cards_only_1_and_3)
assert c is not None, "[FAIL] Тест 8: должна вернуть ближайшую карточку"
assert c["id"] in [10, 11], "[FAIL] Тест 8: должна вернуть одну из доступных"
print("✓ Тест 8: нет нужного difficulty → ближайшая")

print("\n✅ Все тесты прошли!")
