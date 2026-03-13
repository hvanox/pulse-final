from typing import List


def select_next_card(
    user_id: str,
    history: List[dict],
    all_cards: List[dict]
) -> dict:
    """
    Выбирает следующую карточку для пользователя.

    history: [{"card_id": int, "is_correct": bool, "difficulty": int}, ...]
    all_cards: список всех карточек
    Возвращает: один словарь карточки
    """

    # Карточки которые пользователь уже видел сегодня
    seen_ids = {h["card_id"] for h in history}

    # Доступные карточки (не показанные)
    available = [c for c in all_cards if c["id"] not in seen_ids]

    # Все показаны — начинаем заново с самой лёгкой
    if not available:
        return sorted(all_cards, key=lambda c: c["difficulty"])[0]

    # Определяем целевую сложность
    if not history:
        target = 1
    else:
        last = history[-1]
        if last["is_correct"]:
            target = min(last["difficulty"] + 1, 3)
        else:
            target = max(last["difficulty"] - 1, 1)

    # Ищем карточку нужной сложности
    candidates = [c for c in available if c["difficulty"] == target]
    if candidates:
        return candidates[0]

    # Нет нужной — берём ближайшую по сложности
    return sorted(available, key=lambda c: abs(c["difficulty"] - target))[0]
