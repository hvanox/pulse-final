from datetime import date
import hashlib
import random

STOCKS = [
    {"ticker": "AAPL", "name": "Apple", "name_ru": "Эппл", "price": 180.0, "logo_emoji": "🍎", "color": "#111", "sector": "Tech"},
    {"ticker": "MSFT", "name": "Microsoft", "name_ru": "Майкрософт", "price": 410.0, "logo_emoji": "🪟", "color": "#1273de", "sector": "Tech"},
    {"ticker": "SBER", "name": "Sber", "name_ru": "Сбер", "price": 320.0, "logo_emoji": "🏦", "color": "#2e7d32", "sector": "Finance"},
    {"ticker": "GAZP", "name": "Gazprom", "name_ru": "Газпром", "price": 170.0, "logo_emoji": "⛽", "color": "#00acc1", "sector": "Energy"},
]

STOCK_MAP = {s["ticker"]: s for s in STOCKS}

LEVELS = [
    {"level": 1, "title": "Starter", "xp_from": 0, "xp_to": 199},
    {"level": 2, "title": "Investor", "xp_from": 200, "xp_to": 599},
    {"level": 3, "title": "Pro", "xp_from": 600, "xp_to": 9999},
]

ACHIEVEMENTS = [
    {"id": "first_step", "title": "Первый урок", "xp_reward": 20},
    {"id": "first_buy", "title": "Первая покупка", "xp_reward": 20},
    {"id": "streak_7", "title": "Стрик 7 дней", "xp_reward": 50},
]
ACHIEVEMENT_MAP = {a["id"]: a for a in ACHIEVEMENTS}

MARKET_EVENTS = [
    {"id": "inflation", "headline": "Инфляция выше прогноза", "detail": "Давление на tech", "category": "macro", "impact": {"AAPL": -0.03, "MSFT": -0.02}},
    {"id": "oil_up", "headline": "Нефть растет", "detail": "Поддержка energy", "category": "commodities", "impact": {"GAZP": 0.04}},
]


def get_stock(ticker: str):
    return STOCK_MAP.get(ticker.upper())


def get_level_for_xp(xp: int):
    current = LEVELS[0]
    for lvl in LEVELS:
        if lvl["xp_from"] <= xp <= lvl["xp_to"]:
            current = lvl
    nxt = next((x for x in LEVELS if x["level"] == current["level"] + 1), None)
    return {"current": current, "next": nxt}


def _daily_seed(user_id: str, ticker: str, day_offset: int):
    raw = f"{user_id}:{ticker}:{date.today().isoformat()}:{day_offset}"
    return int(hashlib.md5(raw.encode("utf-8")).hexdigest()[:8], 16)


def get_daily_prices(user_id: str, day_offset: int = 0):
    prices = {}
    for stock in STOCKS:
        rng = random.Random(_daily_seed(user_id, stock["ticker"], day_offset))
        drift = rng.uniform(-0.06, 0.06)
        prices[stock["ticker"]] = round(stock["price"] * (1 + drift), 2)
    return prices


def get_sparkline(user_id: str, ticker: str, days: int = 30):
    vals = []
    for d in range(days, -1, -1):
        vals.append(get_daily_prices(user_id, d).get(ticker, 0))
    return vals


def get_daily_event(user_id: str):
    idx = int(hashlib.md5(f"{user_id}:{date.today()}".encode("utf-8")).hexdigest(), 16) % len(MARKET_EVENTS)
    return MARKET_EVENTS[idx]


def get_daily_missions(user_id: str):
    return [
        {"id": "complete_lesson", "text": "Пройди урок", "icon": "📚", "xp": 25},
        {"id": "make_trade", "text": "Сделай сделку", "icon": "💰", "xp": 25},
        {"id": "check_portfolio", "text": "Проверь портфель", "icon": "📊", "xp": 25},
    ]
