import { useState, useEffect, useRef } from "react"
import { getOnboardingQuestions, submitOnboarding } from "../api"

/**
 * OnboardingScreen — "Инвестиционный квест"
 *
 * Flow: Welcome → 10 scenario-based questions → Animated result
 * Design: NOT a boring exam — gamified quest with scenarios
 * Time: ~3-4 minutes (20 sec per question average)
 */

export default function OnboardingScreen({ onComplete, userName, onLogout }) {
  const [phase, setPhase] = useState("welcome") // welcome | quiz | result
  const [questions, setQuestions] = useState([])
  const [currentQ, setCurrentQ] = useState(0)
  const [selected, setSelected] = useState(null)
  const [revealed, setRevealed] = useState(false)
  const [answers, setAnswers] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingQuestions, setLoadingQuestions] = useState(true)
  const [error, setError] = useState(null)
  const [showConfetti, setShowConfetti] = useState(false)
  const timerRef = useRef(null)
  const startTimeRef = useRef(null)

  const fetchQuestions = () => {
    setLoadingQuestions(true)
    setError(null)
    getOnboardingQuestions()
      .then(data => { setQuestions(data.questions || []); setLoadingQuestions(false) })
      .catch(() => { setError("Не удалось загрузить тест. Проверьте соединение."); setLoadingQuestions(false) })
  }

  useEffect(() => { fetchQuestions() }, [])

  const startQuiz = () => {
    setPhase("quiz")
    startTimeRef.current = Date.now()
  }

  const handleSelect = (idx) => {
    if (revealed) return
    setSelected(idx)
  }

  const handleConfirm = () => {
    if (selected === null) return
    setRevealed(true)

    // Record answer with timing
    const timeMs = Date.now() - (startTimeRef.current || Date.now())
    const answer = {
      question_id: questions[currentQ].id,
      selected_index: selected,
      time_ms: timeMs,
    }
    setAnswers(prev => [...prev, answer])
  }

  const handleNext = () => {
    if (currentQ < questions.length - 1) {
      setCurrentQ(currentQ + 1)
      setSelected(null)
      setRevealed(false)
      startTimeRef.current = Date.now()
    } else {
      // Submit test
      setLoading(true)
      const allAnswers = [...answers]
      // Include current answer if not already added
      if (allAnswers.length <= currentQ) {
        allAnswers.push({
          question_id: questions[currentQ].id,
          selected_index: selected,
          time_ms: Date.now() - (startTimeRef.current || Date.now()),
        })
      }
      submitOnboarding(allAnswers)
        .then(res => { setResult(res); setPhase("result"); setLoading(false); setShowConfetti(true); setTimeout(() => setShowConfetti(false), 3000) })
        .catch(() => { setLoading(false); setError("Не удалось отправить ответы. Проверьте соединение.") })
    }
  }

  const accountBadge = (
    <div style={s.accountBadge}>
      <div style={s.accountAvatar}>{userName?.[0]?.toUpperCase() || "?"}</div>
      <div style={s.accountInfo}>
        <div style={s.accountName}>{userName}</div>
        <div style={s.accountEmail}>{localStorage.getItem("pulse_email") || ""}</div>
      </div>
      {onLogout && (
        <button onClick={onLogout} style={s.accountLogout} title="Сменить аккаунт">
          Сменить
        </button>
      )}
    </div>
  )

  // ─── LOADING / ERROR ───
  if (loadingQuestions) {
    return (<div style={s.page}>{accountBadge}<div style={s.loadingCard}><div style={{ fontSize: 48, marginBottom: 16 }}>📝</div><div style={{ fontSize: 18, fontWeight: 700, color: "#fff" }}>Загрузка вопросов...</div></div></div>)
  }
  if (error) {
    return (<div style={s.page}>{accountBadge}<div style={s.loadingCard}><div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div><div style={{ fontSize: 18, fontWeight: 700, color: "#fff", marginBottom: 16 }}>{error}</div><button style={s.startBtn} onClick={fetchQuestions}>Попробовать снова</button></div></div>)
  }

  // ─── WELCOME SCREEN ───
  if (phase === "welcome") {
    return (
      <div style={s.page}>
        {accountBadge}
        <div style={s.welcomeCard}>
          <div style={s.questBadge}>ИНВЕСТИЦИОННЫЙ КВЕСТ</div>
          <div style={s.welcomeIcon}>🎯</div>
          <div style={s.welcomeTitle}>Узнаем твой уровень!</div>
          <div style={s.welcomeText}>
            10 ситуаций из мира инвестиций.{"\n"}
            Никаких скучных определений — только решения.{"\n"}
            Это займёт 3-4 минуты.
          </div>

          <div style={s.welcomeFeatures}>
            {[
              { icon: "📊", text: "Определим уровень знаний" },
              { icon: "🎯", text: "Найдём сильные стороны" },
              { icon: "📚", text: "Составим персональный план" },
            ].map((f, i) => (
              <div key={i} style={s.welcomeFeature}>
                <span style={{ fontSize: 20 }}>{f.icon}</span>
                <span style={s.welcomeFeatureText}>{f.text}</span>
              </div>
            ))}
          </div>

          <button style={s.startBtn} onClick={startQuiz}>
            Начать квест →
          </button>

          <button style={s.skipBtn} onClick={() => onComplete(null)}>
            Пропустить и начать с нуля
          </button>
        </div>
      </div>
    )
  }

  // ─── RESULT SCREEN ───
  if (phase === "result" && result) {
    const level = result.level || {}
    const topicScores = result.topic_scores || {}

    return (
      <div style={s.page}>
        {accountBadge}
        {showConfetti && <div style={s.confettiOverlay}>🎉</div>}

        <div style={s.resultCard}>
          {/* Level Badge */}
          <div style={{
            ...s.levelBadge,
            background: `linear-gradient(135deg, ${level.color || "#4caf50"}22, ${level.color || "#4caf50"}11)`,
            borderColor: `${level.color || "#4caf50"}44`,
          }}>
            <div style={s.levelIcon}>{level.icon}</div>
            <div style={s.levelName}>{level.name_full || level.name}</div>
            <div style={s.levelDesc}>{level.description}</div>
          </div>

          {/* Score */}
          <div style={s.scoreSection}>
            <div style={s.scoreCircle}>
              <div style={s.scoreNum}>{result.total_correct}</div>
              <div style={s.scoreOf}>из {result.total_questions}</div>
            </div>
            <div style={s.scorePct}>{result.score_pct}% правильно</div>
          </div>

          {/* Topic Breakdown */}
          <div style={s.topicSection}>
            <div style={s.sectionLabel}>ТВОИ НАВЫКИ</div>
            {Object.entries(topicScores).map(([id, data]) => (
              <div key={id} style={s.topicRow}>
                <span style={s.topicIcon}>{data.icon || "📊"}</span>
                <span style={s.topicName}>{data.name || id}</span>
                <div style={s.topicBar}>
                  <div style={{
                    ...s.topicFill,
                    width: `${Math.max(data.score * 100, 5)}%`,
                    background: data.score >= 0.7 ? "#4caf50" : data.score >= 0.4 ? "#FFD600" : "#ef5350",
                  }} />
                </div>
                <span style={{
                  ...s.topicPct,
                  color: data.score >= 0.7 ? "#4caf50" : data.score >= 0.4 ? "#FFD600" : "#ef5350",
                }}>
                  {Math.round(data.score * 100)}%
                </span>
              </div>
            ))}
          </div>

          {/* Strong / Weak */}
          <div style={s.swRow}>
            {result.strong_topics?.length > 0 && (
              <div style={s.swCard}>
                <div style={s.swTitle}>💪 Сильные темы</div>
                {result.strong_topics.map((t, i) => (
                  <div key={i} style={s.swItem}>
                    <span>{t.icon}</span> {t.name}
                  </div>
                ))}
              </div>
            )}
            {result.weak_topics?.length > 0 && (
              <div style={s.swCard}>
                <div style={s.swTitle}>📌 Подтянуть</div>
                {result.weak_topics.map((t, i) => (
                  <div key={i} style={s.swItem}>
                    <span>{t.icon}</span> {t.name}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Learning Plan */}
          {result.learning_plan?.length > 0 && (
            <div style={s.planSection}>
              <div style={s.sectionLabel}>ТВОЙ ПЛАН ОБУЧЕНИЯ</div>
              {result.learning_plan.map((step, i) => (
                <div key={i} style={s.planStep}>
                  <div style={{
                    ...s.planDot,
                    background: step.priority === "high" ? "#FFD600" : step.priority === "focus" ? "#ef5350" : "rgba(255,255,255,0.2)",
                  }}>
                    {i + 1}
                  </div>
                  <div style={s.planInfo}>
                    <div style={s.planAction}>{step.action}</div>
                    <div style={s.planReason}>{step.reason}</div>
                  </div>
                  {step.priority === "focus" && (
                    <span style={s.focusBadge}>Фокус</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* XP Bonus */}
          <div style={s.xpBonus}>
            ⚡ +{result.xp_bonus} XP за прохождение квеста!
          </div>

          <button style={s.startBtn} onClick={() => onComplete(result)}>
            Начать обучение →
          </button>
        </div>
      </div>
    )
  }

  // ─── QUIZ SCREEN ───
  if (loading) {
    return (
      <div style={s.page}>
        <div style={s.loadingCard}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🧠</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#fff", marginBottom: 8 }}>Анализируем ответы...</div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)" }}>Составляем персональный план</div>
        </div>
      </div>
    )
  }

  const q = questions[currentQ]
  if (!q) return null

  const progress = ((currentQ + 1) / questions.length) * 100
  const difficultyLabel = q.difficulty === 1 ? "Базовый" : q.difficulty === 2 ? "Средний" : "Продвинутый"
  const typeEmoji = {
    scenario: "📖", news_reaction: "📰", decision: "🤔",
    portfolio_choice: "💼", analysis: "🔬", crisis: "🌪️",
    calculation: "🧮", emotional: "🧠",
  }

  return (
    <div style={s.page}>
      {accountBadge}
      {/* Top bar */}
      <div style={s.topBar}>
        <div style={s.questLabel}>
          {typeEmoji[q.type] || "📊"} Вопрос {currentQ + 1} из {questions.length}
        </div>
        <div style={s.progressBar}>
          <div style={{ ...s.progressFill, width: `${progress}%` }} />
        </div>
        <div style={s.diffBadge}>{difficultyLabel}</div>
      </div>

      <div style={s.quizCard}>
        {/* Scenario */}
        <div style={s.scenario}>{q.scenario}</div>

        {/* Question */}
        <div style={s.question}>{q.question}</div>

        {/* Options */}
        <div style={s.options}>
          {q.options.map((opt, i) => (
            <button
              key={i}
              onClick={() => handleSelect(i)}
              disabled={revealed}
              style={{
                ...s.optionBtn,
                ...(selected === i && !revealed ? s.optionSelected : {}),
                ...(revealed && selected === i ? s.optionRevealed : {}),
              }}
            >
              <span style={s.optionLetter}>{String.fromCharCode(65 + i)}</span>
              <span style={s.optionText}>{typeof opt === "string" ? opt : opt.text}</span>
            </button>
          ))}
        </div>

        {/* Confirm / Next */}
        {!revealed && selected !== null && (
          <button style={s.confirmBtn} onClick={handleConfirm}>
            Подтвердить
          </button>
        )}
        {revealed && (
          <button style={s.nextBtn} onClick={handleNext}>
            {currentQ < questions.length - 1 ? "Следующий вопрос →" : "Узнать результат 🎯"}
          </button>
        )}
      </div>
    </div>
  )
}

const s = {
  page: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "20px",
    background: "#0f1923",
    fontFamily: "Inter, sans-serif",
    color: "#e8eaed",
  },
  // ─── Welcome ───
  welcomeCard: {
    background: "#1a2634",
    borderRadius: 24,
    padding: "48px 36px",
    maxWidth: 480,
    width: "100%",
    textAlign: "center",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  questBadge: {
    display: "inline-block",
    padding: "6px 16px",
    background: "rgba(255,214,0,0.1)",
    borderRadius: 20,
    color: "#FFD600",
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 2,
    marginBottom: 20,
  },
  welcomeIcon: { fontSize: 56, marginBottom: 16 },
  welcomeTitle: { fontSize: 28, fontWeight: 800, color: "#fff", marginBottom: 12 },
  welcomeText: {
    fontSize: 15, color: "rgba(255,255,255,0.6)", lineHeight: 1.7,
    marginBottom: 28, whiteSpace: "pre-line",
  },
  welcomeFeatures: { display: "flex", flexDirection: "column", gap: 12, marginBottom: 32 },
  welcomeFeature: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "10px 16px", background: "rgba(255,255,255,0.03)",
    borderRadius: 10, textAlign: "left",
  },
  welcomeFeatureText: { fontSize: 14, color: "#e8eaed" },
  startBtn: {
    width: "100%", padding: "16px 0", border: "none", borderRadius: 14,
    background: "#FFD600", color: "#000", fontSize: 16, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit", marginBottom: 12,
    transition: "all 0.2s",
  },
  skipBtn: {
    background: "transparent", border: "none", color: "rgba(255,255,255,0.3)",
    fontSize: 13, cursor: "pointer", fontFamily: "inherit", padding: "8px 0",
  },
  // ─── Quiz ───
  topBar: {
    width: "100%", maxWidth: 620,
    display: "flex", alignItems: "center", gap: 12,
    marginBottom: 20,
  },
  questLabel: { fontSize: 13, color: "rgba(255,255,255,0.5)", flexShrink: 0 },
  progressBar: {
    flex: 1, height: 6, background: "rgba(255,255,255,0.08)",
    borderRadius: 3, overflow: "hidden",
  },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #FFD600, #FFA000)",
    borderRadius: 3, transition: "width 0.4s ease",
  },
  diffBadge: {
    fontSize: 10, padding: "3px 10px", borderRadius: 6,
    background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.4)",
    fontWeight: 600, flexShrink: 0,
  },
  quizCard: {
    background: "#1a2634", borderRadius: 20, padding: "32px 28px",
    maxWidth: 620, width: "100%",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  scenario: {
    fontSize: 15, color: "rgba(255,255,255,0.7)", lineHeight: 1.7,
    marginBottom: 16, padding: "16px", background: "rgba(255,255,255,0.03)",
    borderRadius: 12, borderLeft: "3px solid #FFD600", whiteSpace: "pre-line",
  },
  question: {
    fontSize: 18, fontWeight: 700, color: "#fff", marginBottom: 20, lineHeight: 1.5,
  },
  options: { display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 },
  optionBtn: {
    width: "100%", padding: "14px 16px",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 12, background: "rgba(255,255,255,0.03)",
    color: "#e8eaed", fontSize: 14, cursor: "pointer",
    textAlign: "left", fontFamily: "inherit",
    display: "flex", alignItems: "center", gap: 12,
    transition: "all 0.2s",
  },
  optionSelected: {
    borderColor: "#FFD600", background: "rgba(255,214,0,0.08)",
  },
  optionRevealed: {
    borderColor: "rgba(255,255,255,0.15)", opacity: 0.8,
  },
  optionLetter: {
    width: 28, height: 28, borderRadius: "50%",
    background: "rgba(255,255,255,0.06)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 12, fontWeight: 700, flexShrink: 0,
  },
  optionText: { flex: 1, lineHeight: 1.5 },
  confirmBtn: {
    width: "100%", padding: "14px 0", border: "none", borderRadius: 12,
    background: "#FFD600", color: "#000", fontSize: 15, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit",
  },
  nextBtn: {
    width: "100%", padding: "14px 0", border: "none", borderRadius: 12,
    background: "rgba(255,214,0,0.15)", color: "#FFD600", fontSize: 15, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit",
  },
  // ─── Loading ───
  loadingCard: {
    textAlign: "center", padding: 40,
  },
  // ─── Result ───
  confettiOverlay: {
    position: "fixed", inset: 0, display: "flex",
    alignItems: "center", justifyContent: "center",
    fontSize: 120, opacity: 0.3, pointerEvents: "none",
    zIndex: 1000,
  },
  resultCard: {
    background: "#1a2634", borderRadius: 24, padding: "36px 28px",
    maxWidth: 560, width: "100%",
    border: "1px solid rgba(255,255,255,0.06)",
    maxHeight: "90vh", overflowY: "auto",
  },
  levelBadge: {
    padding: "24px 20px", borderRadius: 16,
    border: "1px solid", textAlign: "center", marginBottom: 24,
  },
  levelIcon: { fontSize: 48, marginBottom: 8 },
  levelName: { fontSize: 22, fontWeight: 800, color: "#fff", marginBottom: 6 },
  levelDesc: { fontSize: 13, color: "rgba(255,255,255,0.6)", lineHeight: 1.6 },
  // Score
  scoreSection: { textAlign: "center", marginBottom: 24 },
  scoreCircle: {
    width: 80, height: 80, borderRadius: "50%",
    border: "3px solid #FFD600",
    display: "inline-flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center",
    marginBottom: 8,
  },
  scoreNum: { fontSize: 28, fontWeight: 800, color: "#FFD600" },
  scoreOf: { fontSize: 11, color: "rgba(255,255,255,0.4)" },
  scorePct: { fontSize: 14, color: "rgba(255,255,255,0.5)" },
  // Topics
  topicSection: { marginBottom: 24 },
  sectionLabel: {
    fontSize: 11, color: "rgba(255,255,255,0.4)",
    letterSpacing: 2, marginBottom: 12, fontWeight: 700,
  },
  topicRow: { display: "flex", alignItems: "center", gap: 8, marginBottom: 8 },
  topicIcon: { fontSize: 16, width: 24, textAlign: "center" },
  topicName: { fontSize: 12, color: "rgba(255,255,255,0.6)", width: 100, flexShrink: 0 },
  topicBar: {
    flex: 1, height: 6, background: "rgba(255,255,255,0.06)",
    borderRadius: 3, overflow: "hidden",
  },
  topicFill: { height: "100%", borderRadius: 3, transition: "width 0.5s" },
  topicPct: { fontSize: 12, fontWeight: 700, width: 36, textAlign: "right" },
  // Strong / Weak
  swRow: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 },
  swCard: {
    padding: "14px", background: "rgba(255,255,255,0.03)",
    borderRadius: 12, border: "1px solid rgba(255,255,255,0.04)",
  },
  swTitle: { fontSize: 13, fontWeight: 700, color: "#e8eaed", marginBottom: 8 },
  swItem: { fontSize: 12, color: "rgba(255,255,255,0.5)", padding: "3px 0", display: "flex", gap: 6 },
  // Plan
  planSection: { marginBottom: 24 },
  planStep: { display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 12 },
  planDot: {
    width: 28, height: 28, borderRadius: "50%",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 12, fontWeight: 700, color: "#000", flexShrink: 0,
  },
  planInfo: { flex: 1 },
  planAction: { fontSize: 14, fontWeight: 600, color: "#e8eaed", marginBottom: 2 },
  planReason: { fontSize: 12, color: "rgba(255,255,255,0.4)" },
  focusBadge: {
    fontSize: 10, padding: "2px 8px", borderRadius: 4,
    background: "rgba(239,83,80,0.15)", color: "#ef5350",
    fontWeight: 700, flexShrink: 0,
  },
  // XP
  xpBonus: {
    padding: "12px 16px", background: "rgba(255,214,0,0.1)",
    borderRadius: 10, color: "#FFD600", fontSize: 14, fontWeight: 700,
    textAlign: "center", marginBottom: 20,
  },
  // ─── Account badge (bottom-left) ───
  accountBadge: {
    position: "fixed",
    bottom: 20,
    left: 20,
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 14px",
    background: "#1a2634",
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.06)",
    zIndex: 50,
  },
  accountAvatar: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "#FFD600",
    color: "#000",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 14,
    flexShrink: 0,
  },
  accountInfo: {
    overflow: "hidden",
  },
  accountName: {
    fontSize: 12,
    fontWeight: 600,
    color: "#fff",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  accountEmail: {
    fontSize: 10,
    color: "rgba(255,255,255,0.35)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  accountLogout: {
    padding: "4px 10px",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 6,
    background: "transparent",
    color: "rgba(255,255,255,0.4)",
    fontSize: 11,
    cursor: "pointer",
    fontFamily: "inherit",
    marginLeft: 4,
    flexShrink: 0,
  },
}
