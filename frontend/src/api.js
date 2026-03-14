const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"
let USER_ID = localStorage.getItem("pulse_email") || "demo-user-1"

export const setUserId = (email) => {
  USER_ID = email
  localStorage.setItem("pulse_email", email)
}

export const getUserId = () => USER_ID

// ─── Centralized fetch with error handling ───
async function apiFetch(url, options = {}) {
  try {
    const res = await fetch(url, options)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || body.error || `Ошибка сервера (${res.status})`)
    }
    return await res.json()
  } catch (err) {
    if (err.name === "TypeError" && err.message === "Failed to fetch") {
      throw new Error("Сервер недоступен. Проверьте соединение с интернетом.")
    }
    throw err
  }
}

const POST_JSON = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
})

// ─── Auth ───
export const registerUser = (email, name, password) =>
  apiFetch(`${BASE}/register`, POST_JSON({ email, name, password }))

export const loginUser = (email, password) =>
  apiFetch(`${BASE}/login`, POST_JSON({ email, password }))

// ─── Dashboard ───
export const getDashboard = () =>
  apiFetch(`${BASE}/dashboard?userId=${USER_ID}`)

// ─── Progress ───
export const getProgress = () =>
  apiFetch(`${BASE}/progress?userId=${USER_ID}`)

// ─── Portfolio ───
export const getPortfolio = () =>
  apiFetch(`${BASE}/portfolio?userId=${USER_ID}`)

export const trade = (ticker, shares, action) =>
  apiFetch(`${BASE}/trade`, POST_JSON({ userId: USER_ID, ticker, shares, action }))

export const checkPortfolio = () =>
  apiFetch(`${BASE}/check-portfolio?userId=${USER_ID}`, { method: "POST" })

// ─── Stocks / Market ───
export const getStocks = () =>
  apiFetch(`${BASE}/stocks?userId=${USER_ID}`)

export const getStockDetail = (ticker) =>
  apiFetch(`${BASE}/stock/${ticker}?userId=${USER_ID}`)

export const getMarketEvent = () =>
  apiFetch(`${BASE}/market-event?userId=${USER_ID}`)

export const marketEventAction = (eventId, action) =>
  apiFetch(`${BASE}/market-event/action`, POST_JSON({ userId: USER_ID, eventId, action }))

// ─── Lessons V2 ───
export const getModules = () =>
  apiFetch(`${BASE}/v2/modules?userId=${USER_ID}`)

export const getModuleLessons = (moduleId) =>
  apiFetch(`${BASE}/v2/lessons?userId=${USER_ID}&moduleId=${moduleId}`)

export const getLessonDetail = (lessonId) =>
  apiFetch(`${BASE}/v2/lesson/${lessonId}?userId=${USER_ID}`)

export const completeLesson = (lessonId, correctAnswers = 0, totalQuestions = 0) =>
  apiFetch(`${BASE}/v2/complete-lesson`, POST_JSON({ userId: USER_ID, lessonId, correctAnswers, totalQuestions }))

// ─── Achievements ───
export const getAchievements = () =>
  apiFetch(`${BASE}/achievements?userId=${USER_ID}`)

// ─── Daily Missions ───
export const getDailyMissions = () =>
  apiFetch(`${BASE}/daily-missions?userId=${USER_ID}`)

// ─── Diary ───
export const getDiary = (limit = 20) =>
  apiFetch(`${BASE}/diary?userId=${USER_ID}&limit=${limit}`)

// ─── Transactions ───
export const getTransactions = (limit = 30) =>
  apiFetch(`${BASE}/transactions?userId=${USER_ID}&limit=${limit}`)

// ─── Levels ───
export const getLevels = () =>
  apiFetch(`${BASE}/levels`)

// ─── Streak Freeze ───
export const buyFreeze = () =>
  apiFetch(`${BASE}/buy-freeze`, POST_JSON({ userId: USER_ID }))

// ─── Onboarding ───
export const getOnboardingQuestions = () =>
  apiFetch(`${BASE}/onboarding/questions`)

export const getOnboardingStatus = () =>
  apiFetch(`${BASE}/onboarding/status?userId=${USER_ID}`)

export const submitOnboarding = (answers) =>
  apiFetch(`${BASE}/onboarding/submit`, POST_JSON({ userId: USER_ID, answers }))

export const getOnboardingResult = () =>
  apiFetch(`${BASE}/onboarding/result?userId=${USER_ID}`)

// ─── Adaptive Learning ───
export const getAdaptiveMastery = () =>
  apiFetch(`${BASE}/adaptive/mastery?userId=${USER_ID}`)

export const getAdaptiveRecommendation = () =>
  apiFetch(`${BASE}/adaptive/recommendation?userId=${USER_ID}`)

export const recordAdaptiveAnswer = (topic, questionId, isCorrect, timeMs = 0, source = "lesson") =>
  apiFetch(`${BASE}/adaptive/answer`, POST_JSON({ userId: USER_ID, topic, questionId, isCorrect, timeMs, source }))

// ─── Legacy ───
export const getExperience = () =>
  apiFetch(`${BASE}/experience?userId=${USER_ID}`)

export const postInteraction = (cardId, answer_index) =>
  apiFetch(`${BASE}/interactions`, POST_JSON({ userId: USER_ID, cardId, answer_index }))
