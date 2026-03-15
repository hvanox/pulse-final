import { useState, useEffect, useRef } from "react"
import { getModuleLessons, generateLesson } from "../api"

const TOPIC_ICONS = {
  stocks: "📈", market_logic: "🧠", risk: "⚠️", dividends: "💰",
  diversification: "🎯", etf: "🏦", portfolio: "💼",
}

export default function LearnScreen({ onStartLesson }) {
  const [lessons, setLessons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const prefetchedRef = useRef(null)

  const loadLessons = () => {
    setLoading(true)
    setError(null)
    getModuleLessons("m_ai")
      .then(data => {
        setLessons(data)
        setLoading(false)
        const first = data.find(d => !d.completed && d.generated)
        if (first) {
          generateLesson(first.weak_topic, first.strong_topic)
            .then(lesson => { prefetchedRef.current = { key: first.weak_topic, lesson } })
            .catch(() => {})
        }
      })
      .catch(e => { setError(e.message || "Ошибка"); setLoading(false) })
  }

  useEffect(() => { loadLessons() }, [])

  const handleStartLesson = (lesson) => {
    if (lesson.completed) return
    if (prefetchedRef.current?.key === lesson.weak_topic) {
      onStartLesson(lesson.id, { ...lesson, _prefetched: prefetchedRef.current.lesson })
    } else {
      onStartLesson(lesson.id, lesson)
    }
  }

  if (loading) return <div style={s.loading}>Загрузка уроков...</div>
  if (error) return (
    <div style={s.loading}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <div style={{ marginBottom: 16 }}>{error}</div>
      <button onClick={loadLessons} style={s.retryBtn}>Повторить</button>
    </div>
  )

  // Разделяем на пройденные и новые
  const completedLessons = lessons.filter(l => l.completed)
  const newLessons = lessons.filter(l => !l.completed)

  // Зигзаг-позиции как в Duolingo
  const getOffset = (i) => {
    const pattern = [0, 1, 2, 1, 0, -1, -2, -1]
    return pattern[i % pattern.length] * 48
  }

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div style={s.pageTitle}>Обучение</div>
        <div style={s.subtitle}>Уроки подобраны под тебя</div>
        {completedLessons.length > 0 && (
          <div style={s.progressInfo}>
            Пройдено: {completedLessons.length} из {lessons.length}
          </div>
        )}
      </div>

      <div style={s.path}>
        {/* Линия пути */}
        <div style={s.pathLine} />

        {lessons.map((lesson, li) => {
          const icon = TOPIC_ICONS[lesson.weak_topic] || "📚"
          const isActive = !lesson.completed && (li === 0 || lessons[li - 1]?.completed)
          const masteryPct = Math.round((lesson.weak_mastery || 0) * 100)

          return (
            <div key={lesson.id} style={{
              ...s.nodeWrap,
              marginLeft: `calc(50% + ${getOffset(li)}px - 40px)`,
            }}>
              {/* Кружок */}
              <div
                style={{
                  ...s.node,
                  ...(lesson.completed ? s.nodeCompleted : {}),
                  ...(isActive ? s.nodeActive : {}),
                  ...(!lesson.completed && !isActive ? s.nodeLocked : {}),
                }}
                onClick={() => handleStartLesson(lesson)}
              >
                {/* Прогресс-кольцо */}
                {!lesson.completed && (
                  <svg style={s.progressRing} viewBox="0 0 88 88">
                    <circle cx="44" cy="44" r="40" fill="none" stroke="rgba(0,0,0,0.06)" strokeWidth="4" />
                    <circle cx="44" cy="44" r="40" fill="none"
                      stroke={isActive ? "#9c27b0" : "rgba(0,0,0,0.12)"}
                      strokeWidth="4"
                      strokeDasharray={`${masteryPct * 2.51} 251`}
                      strokeLinecap="round"
                      transform="rotate(-90 44 44)"
                    />
                  </svg>
                )}
                <div style={s.nodeInner}>
                  {lesson.completed
                    ? <span style={s.checkmark}>✓</span>
                    : <span style={s.nodeIcon}>{icon}</span>
                  }
                </div>
              </div>

              {/* Название */}
              <div style={{
                ...s.nodeLabel,
                color: lesson.completed ? "#21a038" : isActive ? "#1a1a1a" : "rgba(0,0,0,0.35)",
                fontWeight: isActive ? 700 : 500,
              }}>
                {lesson.title}
              </div>

              {/* Подзаголовок для активного */}
              {isActive && (
                <div style={s.nodeSubtitle}>{lesson.subtitle}</div>
              )}

              {/* Бейдж XP */}
              {!lesson.completed && isActive && (
                <div style={s.xpBadge}>+{lesson.xp_reward} XP</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const s = {
  page: { maxWidth: 500, margin: "0 auto", paddingBottom: 60 },
  loading: { color: "rgba(0,0,0,0.45)", padding: 60, textAlign: "center", fontSize: 16 },
  retryBtn: {
    padding: "10px 24px", borderRadius: 10, border: "1px solid rgba(0,0,0,0.1)",
    background: "transparent", color: "#ffdd2d", cursor: "pointer", fontFamily: "inherit",
  },
  header: { textAlign: "center", marginBottom: 32 },
  pageTitle: { fontSize: 28, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "rgba(0,0,0,0.4)", marginBottom: 8 },
  progressInfo: {
    fontSize: 12, color: "#9c27b0", fontWeight: 600,
    background: "rgba(156,39,176,0.08)", display: "inline-block",
    padding: "4px 12px", borderRadius: 20,
  },
  path: {
    position: "relative", display: "flex", flexDirection: "column",
    alignItems: "flex-start", gap: 16, paddingTop: 8,
  },
  pathLine: {
    position: "absolute", left: "50%", top: 0, bottom: 0,
    width: 3, background: "rgba(0,0,0,0.06)", transform: "translateX(-50%)",
    borderRadius: 2, zIndex: 0,
  },
  nodeWrap: {
    display: "flex", flexDirection: "column", alignItems: "center",
    position: "relative", zIndex: 1, width: 80,
    transition: "margin-left 0.3s ease",
  },
  node: {
    width: 80, height: 80, borderRadius: "50%",
    display: "flex", alignItems: "center", justifyContent: "center",
    cursor: "pointer", position: "relative",
    transition: "all 0.2s ease", background: "#fff",
  },
  nodeCompleted: {
    background: "#21a038",
    boxShadow: "0 4px 12px rgba(33,160,56,0.3)",
  },
  nodeActive: {
    background: "#fff",
    boxShadow: "0 4px 16px rgba(156,39,176,0.25)",
    border: "3px solid #9c27b0",
  },
  nodeLocked: {
    background: "#f0f0f0",
    border: "3px solid rgba(0,0,0,0.08)",
    opacity: 0.5,
    cursor: "default",
  },
  progressRing: {
    position: "absolute", top: -4, left: -4,
    width: 88, height: 88,
  },
  nodeInner: {
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  checkmark: { fontSize: 28, color: "#fff", fontWeight: 700 },
  nodeIcon: { fontSize: 32 },
  nodeLabel: {
    fontSize: 13, marginTop: 8, textAlign: "center",
    maxWidth: 100, lineHeight: 1.2,
  },
  nodeSubtitle: {
    fontSize: 11, color: "rgba(0,0,0,0.4)", textAlign: "center",
    maxWidth: 120, marginTop: 2,
  },
  xpBadge: {
    fontSize: 10, fontWeight: 700, color: "#9c27b0",
    background: "rgba(156,39,176,0.1)", padding: "2px 8px",
    borderRadius: 10, marginTop: 4,
  },
}
