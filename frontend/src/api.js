const BASE = "http://localhost:8000"
const USER_ID = "demo-user-1"

const USE_MOCK = true // ← поменяй на false когда backend готов

const MOCK_CARD = {
  id: 1,
  text: "Что такое акция?",
  difficulty: 1,
  topic: "акции",
  options: ["Долговая бумага", "Доля в компании", "Гос. облигация", "Фьючерс"],
  correct_index: 1,
  explanations: [
    "Долговая бумага — это облигация. Компания берёт деньги в долг и обещает вернуть с процентами.",
    "Акция — это доля в компании. Владелец акции становится совладельцем бизнеса и участвует в его прибыли.",
    "Государственная облигация — это долговая бумага, выпущенная государством, а не акция.",
    "Фьючерс — это контракт на покупку актива в будущем по заранее оговорённой цене."
  ]
}

export const getExperience = () =>
  USE_MOCK
    ? Promise.resolve(MOCK_CARD)
    : fetch(`${BASE}/experience?userId=${USER_ID}`).then(r => r.json())

export const postInteraction = (cardId, answer_index) =>
  USE_MOCK
    ? Promise.resolve({ is_correct: answer_index === 1, correct_index: 1, streak: 3 })
    : fetch(`${BASE}/interactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: USER_ID, cardId, answer_index })
      }).then(r => r.json())

export const getProgress = () =>
  USE_MOCK
    ? Promise.resolve({ streak: 3, correct_total: 7 })
    : fetch(`${BASE}/progress?userId=${USER_ID}`).then(r => r.json())
