import { useState, useEffect } from "react"
import { getLessons } from "../api"

const TOPIC_ICONS = {
  "акции": "📈",
  "облигации": "📄",
  "бюджет": "💰",
  "налоги": "🏛️",
}

const TOPIC_COLORS = {
  "акции": { bg: "#e3f2fd", border: "#90caf9", fill: "#1565c0" },
  "облигации": { bg: "#f3e5f5", border: "#ce93d8", fill: "#7b1fa2" },
  "бюджет": { bg: "#e8f5e9", border: "#a5d6a7", fill: "#2e7d32" },
  "налоги": { bg: "#fff3e0", border: "#ffcc80", fill: "#e65100" },
}

const DIFFICULTY_LABELS = {
  1: "Легко",
  2: "Средне",
  3: "Сложно",
}

function formatCountdown(targetIso) {
  const diff = new Date(targetIso) - new Date()
  if (diff <= 0) return null
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
}

export default function HomeScreen({ onSelectLesson }) {
  const [lessons, setLessons] = useState([])
  const [loading, setLoading] = useState(true)
  const [, setTick] = useState(0)

  useEffect(() => {
    getLessons().then(data => {
      setLessons(data)
      setLoading(false)
    })
  }, [])

  // Timer tick every second for countdown
  useEffect(() => {
    const hasTimer = lessons.some(l => l.unlock_at)
    if (!hasTimer) return
    const interval = setInterval(() => setTick(t => t + 1), 1000)
    return () => clearInterval(interval)
  }, [lessons])

  if (loading) {
    return (
      <div style={s.page}>
        <div style={s.header}>
          <h1 style={s.title}>Сегодняшний путь</h1>
          <p style={s.subtitle}>Загрузка...</p>
        </div>
        <div style={s.path}>
          {[1, 2, 3, 4].map(i => (
            <div key={i} style={s.skeletonCircle} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h1 style={s.title}>Сегодняшний путь</h1>
        <p style={s.subtitle}>Пройди все уроки от простого к сложному</p>
      </div>

      <div style={s.path}>
        {lessons.map((lesson, index) => {
          const colors = TOPIC_COLORS[lesson.topic] || TOPIC_COLORS["акции"]
          const icon = TOPIC_ICONS[lesson.topic] || "📚"
          const offsetX = index % 2 === 0 ? -50 : 50
          const countdown = lesson.unlock_at ? formatCountdown(lesson.unlock_at) : null
          const isTimeLocked = lesson.locked && countdown

          return (
            <div key={lesson.id}>
              {/* Difficulty section */}
              {(index === 0 || lesson.difficulty !== lessons[index - 1]?.difficulty) && (
                <div style={s.sectionHeader}>
                  <div style={{
                    ...s.sectionBadge,
                    background: colors.bg,
                    borderColor: colors.border,
                  }}>
                    <span style={s.sectionIcon}>
                      {"⭐".repeat(lesson.difficulty)}
                    </span>
                    <span style={{ ...s.sectionText, color: colors.fill }}>
                      {DIFFICULTY_LABELS[lesson.difficulty]}
                    </span>
                  </div>
                </div>
              )}

              {/* Connector */}
              {index > 0 && (
                <div style={s.connectorWrap}>
                  <div style={{
                    ...s.connector,
                    borderColor: lesson.completed ? "#4caf50" : lesson.locked ? "#e0e0e0" : "#FFD600",
                  }} />
                </div>
              )}

              {/* Circle node */}
              <div style={{ ...s.nodeWrap, transform: `translateX(${offsetX}px)` }}>
                <button
                  style={{
                    ...s.circle,
                    background: lesson.completed
                      ? "#4caf50"
                      : lesson.locked
                        ? "#f5f5f5"
                        : colors.bg,
                    borderColor: lesson.completed
                      ? "#388e3c"
                      : lesson.locked
                        ? "#e0e0e0"
                        : colors.border,
                    cursor: lesson.locked ? "not-allowed" : "pointer",
                    opacity: lesson.locked ? 0.6 : 1,
                    boxShadow: !lesson.locked && !lesson.completed
                      ? `0 4px 20px ${colors.border}80`
                      : lesson.completed
                        ? "0 4px 12px rgba(76,175,80,0.3)"
                        : "none",
                  }}
                  onClick={() => !lesson.locked && onSelectLesson(lesson)}
                  disabled={lesson.locked}
                  className={!lesson.locked && !lesson.completed ? "pulse-glow" : ""}
                >
                  {lesson.completed ? (
                    <span style={s.checkmark}>✓</span>
                  ) : lesson.locked ? (
                    <span style={s.lockIcon}>🔒</span>
                  ) : (
                    <span style={s.circleIcon}>{icon}</span>
                  )}
                </button>

                {/* Label */}
                <div style={{ ...s.nodeLabel, color: lesson.locked ? "#bbb" : "#333" }}>
                  Урок {lesson.id} · {lesson.topic}
                </div>

                {/* Question count */}
                <div style={{ ...s.questionCount, color: lesson.locked ? "#ccc" : "#888" }}>
                  {lesson.question_count} вопроса
                </div>

                {/* Timer for time-locked lessons */}
                {isTimeLocked && (
                  <div style={s.timerBadge}>
                    <span style={s.timerIcon}>⏰</span>
                    <span style={s.timerText}>{countdown || "Скоро..."}</span>
                  </div>
                )}
              </div>
            </div>
          )
        })}

        {/* Finish */}
        <div style={s.connectorWrap}>
          <div style={{ ...s.connector, borderColor: "#e0e0e0" }} />
        </div>
        <div style={s.nodeWrap}>
          <div style={s.finishCircle}>
            <span style={{ fontSize: 32 }}>🏆</span>
          </div>
          <div style={s.nodeLabel}>Финиш</div>
        </div>
      </div>

      <div style={{ height: 80 }} />
    </div>
  )
}

const s = {
  page: {
    padding: "32px 24px",
    maxWidth: 500,
    margin: "0 auto",
    fontFamily: "Inter, sans-serif",
  },
  header: {
    textAlign: "center",
    marginBottom: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 800,
    color: "#1a1a1a",
    margin: "0 0 8px",
  },
  subtitle: {
    fontSize: 15,
    color: "#888",
    margin: 0,
  },
  path: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  sectionHeader: {
    marginBottom: 16,
    marginTop: 8,
  },
  sectionBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 20px",
    borderRadius: 20,
    border: "2px solid",
  },
  sectionIcon: {
    fontSize: 14,
  },
  sectionText: {
    fontSize: 14,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  connectorWrap: {
    display: "flex",
    justifyContent: "center",
    height: 32,
  },
  connector: {
    width: 0,
    height: "100%",
    borderLeft: "3px dashed #e0e0e0",
  },
  nodeWrap: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
    transition: "transform 0.3s ease",
  },
  circle: {
    width: 88,
    height: 88,
    borderRadius: "50%",
    border: "4px solid",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.2s ease",
    fontFamily: "Inter, sans-serif",
  },
  circleIcon: {
    fontSize: 36,
  },
  checkmark: {
    fontSize: 36,
    color: "#fff",
    fontWeight: 700,
  },
  lockIcon: {
    fontSize: 28,
  },
  nodeLabel: {
    fontSize: 14,
    fontWeight: 600,
    textTransform: "capitalize",
  },
  questionCount: {
    fontSize: 12,
    fontWeight: 500,
  },
  timerBadge: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "6px 14px",
    background: "#fff3e0",
    borderRadius: 12,
    border: "1px solid #ffe0b2",
    marginTop: 4,
  },
  timerIcon: {
    fontSize: 14,
  },
  timerText: {
    fontSize: 13,
    fontWeight: 700,
    color: "#e65100",
    fontVariantNumeric: "tabular-nums",
  },
  finishCircle: {
    width: 88,
    height: 88,
    borderRadius: "50%",
    background: "#f5f5f5",
    border: "4px dashed #e0e0e0",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  skeletonCircle: {
    width: 88,
    height: 88,
    borderRadius: "50%",
    background: "#f0f0f0",
    margin: "16px 0",
    animation: "pulse 1.4s ease-in-out infinite",
  },
}
