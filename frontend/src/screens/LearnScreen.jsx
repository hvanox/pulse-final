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

  const getOffset = (i) => {
    const pattern = [0, 1, 1.8, 1, 0, -1, -1.8, -1]
    return pattern[i % pattern.length] * 56
  }

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div style={s.pageTitle}>Обучение</div>
        <div style={s.subtitle}>Уроки подобраны под тебя</div>
      </div>

      <div style={s.path}>
        <div style={s.pathLine} />

        {lessons.map((lesson, li) => {
          const icon = TOPIC_ICONS[lesson.weak_topic] || "📚"

          // Считаем сколько непройденных уже доступно до этого
          const uncompletedBefore = lessons.slice(0, li).filter(l => !l.completed).length
          const isAvailable = !lesson.completed && uncompletedBefore < 2
          const isLocked = !lesson.completed && !isAvailable
          const canClick = lesson.completed || isAvailable

          return (
            <div key={lesson.id} style={{
              ...s.nodeWrap,
              marginLeft: `calc(50% + ${getOffset(li)}px - 52px)`,
            }}>
              <div
                style={{
                  ...s.node,
                  ...(lesson.completed ? s.nodeCompleted : {}),
                  ...(isAvailable ? s.nodeActive : {}),
                  ...(isLocked ? s.nodeLocked : {}),
                }}
                onClick={() => canClick && handleStartLesson(lesson)}
              >
                <span style={{
                  fontSize: 38,
                  filter: lesson.completed ? "none" : isAvailable ? "none" : "grayscale(1) opacity(0.4)",
                  lineHeight: 1,
                  color: lesson.completed ? "#fff" : "inherit",
                }}>
                  {lesson.completed ? "✓" : isLocked ? "🔒" : icon}
                </span>
              </div>

              <div style={{
                ...s.nodeLabel,
                color: lesson.completed ? "#21a038" : isAvailable ? "#1a1a1a" : "rgba(0,0,0,0.3)",
                fontWeight: isAvailable ? 700 : 500,
              }}>
                {lesson.title}
              </div>

              {isAvailable && (
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
  header: { textAlign: "center", marginBottom: 40 },
  pageTitle: { fontSize: 28, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "rgba(0,0,0,0.4)", marginBottom: 8 },
  path: {
    position: "relative", display: "flex", flexDirection: "column",
    alignItems: "flex-start", gap: 24, paddingTop: 8,
  },
  pathLine: {
    position: "absolute", left: "50%", top: 0, bottom: 0,
    width: 4, background: "rgba(0,0,0,0.04)", transform: "translateX(-50%)",
    borderRadius: 2, zIndex: 0,
  },
  nodeWrap: {
    display: "flex", flexDirection: "column", alignItems: "center",
    position: "relative", zIndex: 1, width: 104,
    transition: "margin-left 0.3s ease",
  },
  node: {
    width: 104, height: 104, borderRadius: "50%",
    display: "flex", alignItems: "center", justifyContent: "center",
    cursor: "pointer", position: "relative",
    transition: "all 0.25s ease",
  },
  nodeCompleted: {
    background: "#21a038",
    border: "4px solid #1b8a2f",
    boxShadow: "0 4px 14px rgba(33,160,56,0.3), 0 2px 6px rgba(0,0,0,0.06)",
  },
  nodeActive: {
    background: "#fff",
    border: "4px solid #ffdd2d",
    boxShadow: "0 6px 24px rgba(255,221,45,0.3), 0 2px 8px rgba(0,0,0,0.08)",
  },
  nodeLocked: {
    background: "#f5f5f5",
    border: "4px solid rgba(0,0,0,0.06)",
    boxShadow: "0 2px 6px rgba(0,0,0,0.04)",
    cursor: "default",
  },
  nodeLabel: {
    fontSize: 13, marginTop: 10, textAlign: "center",
    maxWidth: 110, lineHeight: 1.3,
  },
  xpBadge: {
    fontSize: 11, fontWeight: 700, color: "#b8860b",
    background: "rgba(255,221,45,0.15)", padding: "3px 10px",
    borderRadius: 12, marginTop: 4,
  },
}
