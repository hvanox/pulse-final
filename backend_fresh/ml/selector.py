def select_next_card(user_id, history, all_cards):
    """
    Deterministic fallback selector:
    - prefer cards that were answered incorrectly most recently;
    - avoid returning the same card twice in a row.
    """
    if not all_cards:
        return None

    if not history:
        return all_cards[0]

    last_card_id = history[-1]["card_id"]
    wrong_recent = [h for h in reversed(history) if not h.get("is_correct")]
    if wrong_recent:
        target = wrong_recent[0]["card_id"]
        for c in all_cards:
            if c["id"] == target and c["id"] != last_card_id:
                return c

    for c in all_cards:
        if c["id"] != last_card_id:
            return c
    return all_cards[0]
