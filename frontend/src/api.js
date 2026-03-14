const BASE = "http://localhost:8000"
let USER_ID = localStorage.getItem("pulse_email") || "demo-user-1"

export const setUserId = (email) => {
  USER_ID = email
  localStorage.setItem("pulse_email", email)
}

export const getUserId = () => USER_ID

// ─── Auth ───
export const registerUser = (email, name, password) =>
  fetch(`${BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, password })
  }).then(r => r.json())

export const loginUser = (email, password) =>
  fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  }).then(r => r.json())

// ─── Dashboard ───
export const getDashboard = () =>
  fetch(`${BASE}/dashboard?userId=${USER_ID}`).then(r => r.json())

// ─── Progress ───
export const getProgress = () =>
  fetch(`${BASE}/progress?userId=${USER_ID}`).then(r => r.json())

// ─── Portfolio ───
export const getPortfolio = () =>
  fetch(`${BASE}/portfolio?userId=${USER_ID}`).then(r => r.json())

export const trade = (ticker, shares, action) =>
  fetch(`${BASE}/trade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId: USER_ID, ticker, shares, action })
  }).then(r => r.json())

export const checkPortfolio = () =>
  fetch(`${BASE}/check-portfolio?userId=${USER_ID}`, { method: "POST" }).then(r => r.json())

// ─── Stocks / Market ───
export const getStocks = () =>
  fetch(`${BASE}/stocks?userId=${USER_ID}`).then(r => r.json())

export const getStockDetail = (ticker) =>
  fetch(`${BASE}/stock/${ticker}?userId=${USER_ID}`).then(r => r.json())

export const getMarketEvent = () =>
  fetch(`${BASE}/market-event?userId=${USER_ID}`).then(r => r.json())

export const marketEventAction = (eventId, action) =>
  fetch(`${BASE}/market-event/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId: USER_ID, eventId, action })
  }).then(r => r.json())

// ─── Lessons V2 ───
export const getModules = () =>
  fetch(`${BASE}/v2/modules?userId=${USER_ID}`).then(r => r.json())

export const getModuleLessons = (moduleId) =>
  fetch(`${BASE}/v2/lessons?userId=${USER_ID}&moduleId=${moduleId}`).then(r => r.json())

export const getLessonDetail = (lessonId) =>
  fetch(`${BASE}/v2/lesson/${lessonId}?userId=${USER_ID}`).then(r => r.json())

export const completeLesson = (lessonId, correctAnswers = 0, totalQuestions = 0) =>
  fetch(`${BASE}/v2/complete-lesson`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId: USER_ID, lessonId, correctAnswers, totalQuestions })
  }).then(r => r.json())

// ─── Achievements ───
export const getAchievements = () =>
  fetch(`${BASE}/achievements?userId=${USER_ID}`).then(r => r.json())

// ─── Daily Missions ───
export const getDailyMissions = () =>
  fetch(`${BASE}/daily-missions?userId=${USER_ID}`).then(r => r.json())

// ─── Diary ───
export const getDiary = (limit = 20) =>
  fetch(`${BASE}/diary?userId=${USER_ID}&limit=${limit}`).then(r => r.json())

// ─── Transactions ───
export const getTransactions = (limit = 30) =>
  fetch(`${BASE}/transactions?userId=${USER_ID}&limit=${limit}`).then(r => r.json())

// ─── Levels ───
export const getLevels = () =>
  fetch(`${BASE}/levels`).then(r => r.json())

// ─── Streak Freeze ───
export const buyFreeze = () =>
  fetch(`${BASE}/buy-freeze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId: USER_ID })
  }).then(r => r.json())

// ─── Onboarding ───
export const getOnboardingQuestions = () =>
  fetch(`${BASE}/onboarding/questions`).then(r => r.json())

export const getOnboardingStatus = () =>
  fetch(`${BASE}/onboarding/status?userId=${USER_ID}`).then(r => r.json())

export const submitOnboarding = (answers) =>
  fetch(`${BASE}/onboarding/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId: USER_ID, answers })
  }).then(r => r.json())

export const getOnboardingResult = () =>
  fetch(`${BASE}/onboarding/result?userId=${USER_ID}`).then(r => r.json())

// ─── Adaptive Learning ───
export const getAdaptiveMastery = () =>
  fetch(`${BASE}/adaptive/mastery?userId=${USER_ID}`).then(r => r.json())

export const getAdaptiveRecommendation = () =>
  fetch(`${BASE}/adaptive/recommendation?userId=${USER_ID}`).then(r => r.json())

export const recordAdaptiveAnswer = (topic, questionId, isCorrect, timeMs = 0, source = "lesson") =>
  fetch(`${BASE}/adaptive/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId: USER_ID, topic, questionId, isCorrect, timeMs, source })
  }).then(r => r.json())

// ─── Legacy ───
export const getExperience = () =>
  fetch(`${BASE}/experience?userId=${USER_ID}`).then(r => r.json())

export const postInteraction = (cardId, answer_index) =>
  fetch(`${BASE}/interactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userId: USER_ID, cardId, answer_index })
  }).then(r => r.json())
