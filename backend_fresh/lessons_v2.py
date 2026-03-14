MODULES = [
    {"id": "m1", "title": "База", "icon": "📚", "required_level": 1},
    {"id": "m2", "title": "Акции", "icon": "📈", "required_level": 1},
    {"id": "m3", "title": "Риски", "icon": "⚠️", "required_level": 2},
]
MODULE_MAP = {m["id"]: m for m in MODULES}

LESSONS = [
    {
        "id": "1.1",
        "module_id": "m1",
        "title": "Что такое инвестиции",
        "subtitle": "Базовый старт",
        "duration_min": 8,
        "xp_reward": 30,
        "skill": "Основы",
        "order": 1,
        "screens": [{"type": "text", "content": "Инвестиции это..."}],
    },
    {
        "id": "2.1",
        "module_id": "m2",
        "title": "Как работают акции",
        "subtitle": "Доли компаний",
        "duration_min": 10,
        "xp_reward": 40,
        "skill": "Акции",
        "order": 1,
        "screens": [{"type": "text", "content": "Акция это доля..."}],
    },
    {
        "id": "3.1",
        "module_id": "m3",
        "title": "Риск и диверсификация",
        "subtitle": "Защита капитала",
        "duration_min": 12,
        "xp_reward": 50,
        "skill": "Риски",
        "order": 1,
        "screens": [{"type": "text", "content": "Не клади все яйца..."}],
    },
]

LESSON_MAP = {l["id"]: l for l in LESSONS}


def get_module_lessons(module_id: str):
    data = [l for l in LESSONS if l["module_id"] == module_id]
    data.sort(key=lambda x: x["order"])
    return data


def get_lesson(lesson_id: str):
    return LESSON_MAP.get(lesson_id)
