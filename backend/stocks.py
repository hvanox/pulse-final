"""
Stock data, market simulation, and market events for Pulse 2.0
"""

import random
import math
from datetime import datetime, timedelta

# ─── 12 AVAILABLE STOCKS ───

STOCKS = [
    {
        "ticker": "AAPL",
        "name": "Apple",
        "name_ru": "Apple",
        "sector": "Технологии",
        "sector_en": "tech",
        "price": 17500,
        "currency": "₽",
        "pe": 28.5,
        "dividend_yield": 0.5,
        "description": "Крупнейшая технологическая компания. iPhone, Mac, сервисы.",
        "logo_emoji": "🍎",
        "color": "#555555",
        "volatility": 0.02,
    },
    {
        "ticker": "TSLA",
        "name": "Tesla",
        "name_ru": "Tesla",
        "sector": "Авто/Технологии",
        "sector_en": "auto",
        "price": 25000,
        "currency": "₽",
        "pe": 65.0,
        "dividend_yield": 0.0,
        "description": "Электромобили и энергетика. Илон Маск.",
        "logo_emoji": "⚡",
        "color": "#e31937",
        "volatility": 0.04,
    },
    {
        "ticker": "AMZN",
        "name": "Amazon",
        "name_ru": "Amazon",
        "sector": "E-commerce",
        "sector_en": "ecommerce",
        "price": 18500,
        "currency": "₽",
        "pe": 60.0,
        "dividend_yield": 0.0,
        "description": "Маркетплейс, облачные сервисы AWS.",
        "logo_emoji": "📦",
        "color": "#ff9900",
        "volatility": 0.025,
    },
    {
        "ticker": "MSFT",
        "name": "Microsoft",
        "name_ru": "Microsoft",
        "sector": "Технологии",
        "sector_en": "tech",
        "price": 42000,
        "currency": "₽",
        "pe": 35.0,
        "dividend_yield": 0.8,
        "description": "Windows, Azure, Office, Xbox. Инвестор в OpenAI.",
        "logo_emoji": "🪟",
        "color": "#00a4ef",
        "volatility": 0.018,
    },
    {
        "ticker": "GOOG",
        "name": "Google",
        "name_ru": "Google",
        "sector": "Технологии",
        "sector_en": "tech",
        "price": 17500,
        "currency": "₽",
        "pe": 25.0,
        "dividend_yield": 0.0,
        "description": "Поиск, YouTube, Android, облака.",
        "logo_emoji": "🔍",
        "color": "#4285f4",
        "volatility": 0.022,
    },
    {
        "ticker": "NVDA",
        "name": "Nvidia",
        "name_ru": "Nvidia",
        "sector": "Полупроводники",
        "sector_en": "semiconductors",
        "price": 88000,
        "currency": "₽",
        "pe": 70.0,
        "dividend_yield": 0.03,
        "description": "Видеокарты и чипы для AI. Лидер AI-революции.",
        "logo_emoji": "🎮",
        "color": "#76b900",
        "volatility": 0.045,
    },
    {
        "ticker": "KO",
        "name": "Coca-Cola",
        "name_ru": "Coca-Cola",
        "sector": "Потребительский",
        "sector_en": "consumer",
        "price": 6000,
        "currency": "₽",
        "pe": 24.0,
        "dividend_yield": 3.1,
        "description": "Напитки. Дивиденды 60+ лет подряд. Защитная акция.",
        "logo_emoji": "🥤",
        "color": "#f40009",
        "volatility": 0.01,
    },
    {
        "ticker": "SBER",
        "name": "Сбербанк",
        "name_ru": "Сбербанк",
        "sector": "Финансы",
        "sector_en": "finance",
        "price": 290,
        "currency": "₽",
        "pe": 4.5,
        "dividend_yield": 9.5,
        "description": "Крупнейший банк России. Высокие дивиденды.",
        "logo_emoji": "🏦",
        "color": "#21a038",
        "volatility": 0.025,
    },
    {
        "ticker": "GAZP",
        "name": "Газпром",
        "name_ru": "Газпром",
        "sector": "Энергетика",
        "sector_en": "energy",
        "price": 165,
        "currency": "₽",
        "pe": 3.0,
        "dividend_yield": 5.0,
        "description": "Крупнейшая газовая компания мира.",
        "logo_emoji": "🔥",
        "color": "#0078c1",
        "volatility": 0.03,
    },
    {
        "ticker": "YNDX",
        "name": "Яндекс",
        "name_ru": "Яндекс",
        "sector": "Технологии",
        "sector_en": "tech",
        "price": 3800,
        "currency": "₽",
        "pe": 30.0,
        "dividend_yield": 0.0,
        "description": "Поиск, такси, доставка, AI. Российский Google.",
        "logo_emoji": "🔎",
        "color": "#fc3f1d",
        "volatility": 0.03,
    },
    {
        "ticker": "LKOH",
        "name": "Лукойл",
        "name_ru": "Лукойл",
        "sector": "Энергетика",
        "sector_en": "energy",
        "price": 7200,
        "currency": "₽",
        "pe": 5.5,
        "dividend_yield": 8.0,
        "description": "Нефтяная компания. Стабильные дивиденды.",
        "logo_emoji": "🛢️",
        "color": "#c8102e",
        "volatility": 0.02,
    },
    {
        "ticker": "TCSG",
        "name": "Тинькофф",
        "name_ru": "Тинькофф",
        "sector": "Финансы",
        "sector_en": "finance",
        "price": 2900,
        "currency": "₽",
        "pe": 8.0,
        "dividend_yield": 2.0,
        "description": "Онлайн-банк, брокер, страхование. Быстрый рост.",
        "logo_emoji": "💳",
        "color": "#ffdd2d",
        "volatility": 0.035,
    },
]

STOCK_MAP = {s["ticker"]: s for s in STOCKS}


def get_stock(ticker: str):
    return STOCK_MAP.get(ticker)


def simulate_price_change(base_price: float, volatility: float, seed: int = None):
    """Simulate realistic daily price change using historical-like patterns."""
    if seed is not None:
        random.seed(seed)
    # Use a combination of trend and random walk
    drift = random.gauss(0.0002, volatility)  # slight positive drift
    change = base_price * drift
    new_price = max(base_price * 0.5, base_price + change)  # floor at 50%
    return round(new_price, 2)


def get_daily_prices(user_id: str, day_offset: int = 0):
    """Get simulated prices for a given day. Deterministic per user+day."""
    today = datetime.now().date()
    target_date = today - timedelta(days=day_offset)
    seed_base = hash(user_id + str(target_date))

    prices = {}
    for stock in STOCKS:
        random.seed(seed_base + hash(stock["ticker"]))
        # Apply multiple small changes for more realistic movement
        price = stock["price"]
        for _ in range(max(1, day_offset)):
            price = simulate_price_change(price, stock["volatility"])
        prices[stock["ticker"]] = round(price, 2)

    return prices


def get_sparkline(user_id: str, ticker: str, days: int = 30):
    """Generate sparkline data for a stock."""
    stock = STOCK_MAP.get(ticker)
    if not stock:
        return []
    points = []
    price = stock["price"]
    for d in range(days, -1, -1):
        seed = hash(user_id + str(datetime.now().date() - timedelta(days=d)) + ticker)
        random.seed(seed)
        price = simulate_price_change(price, stock["volatility"])
        points.append(round(price, 2))
    return points


# ─── MARKET EVENTS ───

MARKET_EVENTS = [
    {
        "id": "evt_nvidia_earnings",
        "headline": "Nvidia отчиталась лучше ожиданий",
        "detail": "Выручка выросла на 120% за квартал. AI-чипы продолжают пользоваться огромным спросом.",
        "impact": {"NVDA": 0.08, "MSFT": 0.02, "GOOG": 0.01},
        "category": "earnings",
    },
    {
        "id": "evt_apple_iphone",
        "headline": "Apple представила новый iPhone",
        "detail": "Продажи превысили прогнозы аналитиков. Акции растут на премаркете.",
        "impact": {"AAPL": 0.05},
        "category": "product",
    },
    {
        "id": "evt_tesla_recall",
        "headline": "Tesla отзывает 500 000 автомобилей",
        "detail": "Проблема с автопилотом. Расходы на ремонт — $500 млн.",
        "impact": {"TSLA": -0.07},
        "category": "negative",
    },
    {
        "id": "evt_cbr_rate",
        "headline": "ЦБ повысил ключевую ставку на 1%",
        "detail": "Ставка теперь 17%. Облигации становятся привлекательнее акций.",
        "impact": {"SBER": -0.03, "GAZP": -0.02, "YNDX": -0.04, "LKOH": -0.02, "TCSG": -0.03},
        "category": "macro",
    },
    {
        "id": "evt_gazprom_dividends",
        "headline": "Газпром сократил дивиденды вдвое",
        "detail": "Совет директоров рекомендовал снижение дивидендов из-за падения экспорта.",
        "impact": {"GAZP": -0.10},
        "category": "dividends",
    },
    {
        "id": "evt_sber_record",
        "headline": "Сбербанк: рекордная прибыль за квартал",
        "detail": "Чистая прибыль — 400 млрд ₽. Дивидендная база растёт.",
        "impact": {"SBER": 0.06, "TCSG": 0.02},
        "category": "earnings",
    },
    {
        "id": "evt_yandex_ai",
        "headline": "Яндекс запустил прорывную AI-модель",
        "detail": "Модель YandexGPT 4 превзошла конкурентов в русском языке.",
        "impact": {"YNDX": 0.09},
        "category": "product",
    },
    {
        "id": "evt_oil_crisis",
        "headline": "Цена нефти упала на 15%",
        "detail": "ОПЕК+ не договорилась о сокращении добычи. Рынки в панике.",
        "impact": {"LKOH": -0.08, "GAZP": -0.05},
        "category": "macro",
    },
    {
        "id": "evt_amazon_cloud",
        "headline": "AWS обогнал Azure по росту",
        "detail": "Amazon Web Services показал рост 35% за квартал.",
        "impact": {"AMZN": 0.06, "MSFT": -0.02},
        "category": "earnings",
    },
    {
        "id": "evt_market_crash",
        "headline": "Мировые рынки упали на 5%",
        "detail": "Опасения рецессии. Инвесторы уходят в защитные активы.",
        "impact": {"AAPL": -0.05, "TSLA": -0.08, "NVDA": -0.07, "AMZN": -0.05, "MSFT": -0.04, "GOOG": -0.05, "KO": -0.01, "SBER": -0.06, "GAZP": -0.04, "YNDX": -0.06, "LKOH": -0.04, "TCSG": -0.05},
        "category": "crisis",
    },
    {
        "id": "evt_cocacola_div",
        "headline": "Coca-Cola увеличила дивиденды 62-й год подряд",
        "detail": "Повышение на 5%. Стабильность, проверенная десятилетиями.",
        "impact": {"KO": 0.03},
        "category": "dividends",
    },
    {
        "id": "evt_tinkoff_growth",
        "headline": "Тинькофф: 2 млн новых клиентов за квартал",
        "detail": "Экосистема растёт. Брокерский бизнес +40%.",
        "impact": {"TCSG": 0.07},
        "category": "earnings",
    },
]


def get_daily_event(user_id: str, day_offset: int = 0):
    """Get deterministic daily market event for user."""
    today = datetime.now().date()
    target_date = today - timedelta(days=day_offset)
    seed = hash(user_id + str(target_date) + "event")
    random.seed(seed)
    # 70% chance of an event each day
    if random.random() < 0.3:
        return None
    return random.choice(MARKET_EVENTS)


# ─── HISTORICAL SCENARIOS ───

SCENARIOS = [
    {
        "id": "covid_2020",
        "name": "COVID-обвал",
        "year": 2020,
        "description": "Март 2020: рынок -35% за месяц. Мир закрывается на карантин.",
        "duration_days": 150,
        "pattern": "crash_recovery",
        "crash_pct": -35,
        "recovery_months": 5,
    },
    {
        "id": "gamestop_2021",
        "name": "GameStop безумие",
        "year": 2021,
        "description": "Reddit-трейдеры vs хедж-фонды. +1500% за неделю, потом обвал.",
        "duration_days": 30,
        "pattern": "spike_crash",
        "spike_pct": 1500,
        "crash_pct": -80,
    },
    {
        "id": "crisis_2008",
        "name": "Кризис 2008",
        "year": 2008,
        "description": "Ипотечный кризис. 18 месяцев падения. Lehman Brothers банкрот.",
        "duration_days": 540,
        "pattern": "slow_crash",
        "crash_pct": -55,
    },
    {
        "id": "apple_growth",
        "name": "Рост Apple 2019–2024",
        "year": 2019,
        "description": "Стабильный рост x3.5 за 5 лет. Сервисы + iPhone.",
        "duration_days": 1825,
        "pattern": "steady_growth",
        "growth_pct": 250,
    },
    {
        "id": "nvidia_ai",
        "name": "Nvidia AI-хайп",
        "year": 2023,
        "description": "Рост x5 за год на волне AI-революции.",
        "duration_days": 365,
        "pattern": "explosive_growth",
        "growth_pct": 400,
    },
    {
        "id": "dotcom_2000",
        "name": "Пузырь доткомов",
        "year": 2000,
        "description": "Pets.com, Webvan и урок о пузырях. Nasdaq -78%.",
        "duration_days": 900,
        "pattern": "bubble_burst",
        "spike_pct": 200,
        "crash_pct": -78,
    },
    {
        "id": "cocacola_dividends",
        "name": "Дивидендная стабильность Coca-Cola",
        "year": 1990,
        "description": "60+ лет стабильных дивидендов. Медленный, но верный рост.",
        "duration_days": 3650,
        "pattern": "dividend_steady",
        "growth_pct": 150,
        "annual_dividend": 3.0,
    },
]


# ─── LEVELS ───

LEVELS = [
    {"level": 1, "name": "Наблюдатель", "name_en": "observer", "xp_required": 0, "icon": "👁️", "unlocks": "Базовые уроки, покупка акций"},
    {"level": 2, "name": "Новичок", "name_en": "beginner", "xp_required": 500, "icon": "🥉", "unlocks": "ETF, диверсификация"},
    {"level": 3, "name": "Практикант", "name_en": "intern", "xp_required": 1500, "icon": "📊", "unlocks": "Графики, P/E анализ"},
    {"level": 4, "name": "Инвестор", "name_en": "investor", "xp_required": 3500, "icon": "💼", "unlocks": "Дивидендная стратегия, облигации"},
    {"level": 5, "name": "Трейдер", "name_en": "trader", "xp_required": 6000, "icon": "📈", "unlocks": "Торговые сессии, кризисные сценарии"},
    {"level": 6, "name": "Аналитик", "name_en": "analyst", "xp_required": 10000, "icon": "🔬", "unlocks": "Финансовые отчёты, баттлы компаний"},
    {"level": 7, "name": "Портфельный управляющий", "name_en": "portfolio_manager", "xp_required": 15000, "icon": "🏛️", "unlocks": "Все инструменты, режим эксперта"},
    {"level": 8, "name": "Гуру рынка", "name_en": "guru", "xp_required": 25000, "icon": "👑", "unlocks": "Эксклюзивные сценарии, менторство"},
]


def get_level_for_xp(xp: int):
    """Return level info for given XP amount."""
    current = LEVELS[0]
    for lvl in LEVELS:
        if xp >= lvl["xp_required"]:
            current = lvl
        else:
            break
    next_level = None
    idx = LEVELS.index(current)
    if idx < len(LEVELS) - 1:
        next_level = LEVELS[idx + 1]
    return {
        "current": current,
        "next": next_level,
        "xp": xp,
        "xp_to_next": next_level["xp_required"] - xp if next_level else 0,
        "progress": (xp - current["xp_required"]) / (next_level["xp_required"] - current["xp_required"]) if next_level else 1.0,
    }


# ─── ACHIEVEMENTS ───

ACHIEVEMENTS = [
    # Learning
    {"id": "first_step", "name": "Первый шаг", "description": "Пройди первый урок", "icon": "🎯", "category": "learning", "xp_reward": 50},
    {"id": "diligent_student", "name": "Прилежный ученик", "description": "Пройди 10 уроков", "icon": "📚", "category": "learning", "xp_reward": 200},
    {"id": "marathon", "name": "Марафонец", "description": "Учись 30 дней подряд", "icon": "🏃", "category": "learning", "xp_reward": 500},
    {"id": "encyclopedist", "name": "Энциклопедист", "description": "Пройди все уроки одного модуля", "icon": "📖", "category": "learning", "xp_reward": 300},
    {"id": "master_basics", "name": "Мастер основ", "description": "Заверши модуль 'Основы инвестирования'", "icon": "🎓", "category": "learning", "xp_reward": 500},
    {"id": "course_complete", "name": "Дипломированный инвестор", "description": "Заверши весь курс", "icon": "🏆", "category": "learning", "xp_reward": 2000},
    # Portfolio
    {"id": "first_buy", "name": "Первая покупка", "description": "Купи свою первую акцию", "icon": "🛒", "category": "portfolio", "xp_reward": 50},
    {"id": "diversifier", "name": "Диверсификатор", "description": "Имей 5+ разных активов", "icon": "🎨", "category": "portfolio", "xp_reward": 200},
    {"id": "dividend_hunter", "name": "Дивидендный охотник", "description": "Получи первые дивиденды", "icon": "💰", "category": "portfolio", "xp_reward": 100},
    {"id": "steady_investor", "name": "Стойкий инвестор", "description": "Не продавай во время падения рынка", "icon": "🛡️", "category": "portfolio", "xp_reward": 300},
    {"id": "millionaire", "name": "Миллионер", "description": "Доведи портфель до 2 000 000 ₽", "icon": "💎", "category": "portfolio", "xp_reward": 1000},
    {"id": "global_investor", "name": "Глобальный инвестор", "description": "Купи российские и зарубежные акции", "icon": "🌍", "category": "portfolio", "xp_reward": 150},
    {"id": "patient", "name": "Терпеливый", "description": "Держи акцию 30+ дней", "icon": "⏳", "category": "portfolio", "xp_reward": 200},
    # Decisions
    {"id": "cool_headed", "name": "Хладнокровный", "description": "Не поддайся панике в кризисе", "icon": "🧊", "category": "decisions", "xp_reward": 300},
    {"id": "analyst_pro", "name": "Аналитик", "description": "Правильно оцени новость 5 раз", "icon": "🧠", "category": "decisions", "xp_reward": 200},
    {"id": "prophet", "name": "Провидец", "description": "Угадай направление графика 3 раза", "icon": "🔮", "category": "decisions", "xp_reward": 300},
    {"id": "lesson_learned", "name": "Урок извлечён", "description": "Исправь ошибку после подсказки", "icon": "💡", "category": "decisions", "xp_reward": 100},
    # Streaks
    {"id": "streak_7", "name": "Неделя без пропусков", "description": "7 дней подряд", "icon": "🔥", "category": "streak", "xp_reward": 100},
    {"id": "streak_30", "name": "Месяц дисциплины", "description": "30 дней подряд", "icon": "🌟", "category": "streak", "xp_reward": 500},
]

ACHIEVEMENT_MAP = {a["id"]: a for a in ACHIEVEMENTS}


# ─── DAILY MISSIONS ───

DAILY_MISSION_TEMPLATES = [
    {"id": "complete_lesson", "text": "Пройди один урок", "xp": 30, "icon": "📚"},
    {"id": "make_trade", "text": "Соверши одну сделку", "xp": 20, "icon": "💹"},
    {"id": "check_portfolio", "text": "Проверь свой портфель", "xp": 10, "icon": "📊"},
    {"id": "read_event", "text": "Прочитай рыночное событие", "xp": 10, "icon": "📰"},
    {"id": "answer_5", "text": "Правильно ответь на 5 вопросов", "xp": 50, "icon": "✅"},
    {"id": "crisis_scenario", "text": "Пройди кризисный сценарий", "xp": 40, "icon": "🌪️"},
]


def get_daily_missions(user_id: str):
    """Get 3 deterministic daily missions for user."""
    today = datetime.now().date()
    seed = hash(user_id + str(today) + "missions")
    random.seed(seed)
    selected = random.sample(DAILY_MISSION_TEMPLATES[:4], 3)  # Pick 3 from first 4 (achievable)
    return selected
