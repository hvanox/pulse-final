import { useState, useEffect, useRef } from "react"
import { getModuleLessons, generateLesson } from "../api"

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
        // Префетч первого урока — чтобы при клике открылся мгновенно
        if (data.length > 0 && data[0].generated && !data[0].locked) {
          const first = data[0]
          generateLesson(first.weak_topic, first.strong_topic)
            .then(lesson => { prefetchedRef.current = { key: first.weak_topic, lesson } })
            .catch(() => {})
        }
      })
      .catch(e => { setError(e.message || "Ошибка"); setLoading(false) })
  }

  useEffect(() => { loadLessons() }, [])

  const handleStartLesson = (lesson) => {
    if (!lesson.generated) {
      // Статический урок — открываем как обычно
      onStartLesson(lesson.id, null)
    } else if (prefetchedRef.current?.key === lesson.weak_topic) {
      // AI-урок уже префетчен
      onStartLesson(lesson.id, { ...lesson, _prefetched: prefetchedRef.current.lesson })
    } else {
      // AI-урок — генерируем
      onStartLesson(lesson.id, lesson)
    }
  }

  if (loading) return <div style={s.loading}>Загрузка уроков...</div>
  if (error) return <div style={s.loading}><div style={{fontSize:48,marginBottom:16}}>⚠️</div><div style={{marginBottom:16}}>{error}</div><button onClick={loadLessons} style={{padding:"10px 24px",borderRadius:10,border:"1px solid rgba(0,0,0,0.1)",background:"transparent",color:"#ffdd2d",cursor:"pointer",fontFamily:"inherit"}}>Повторить</button></div>

  return (
    <div style={s.page}>
      <div style={s.pageTitle}>Обучение</div>
      <div style={s.subtitle}>Уроки подобраны под тебя на основе твоих результатов</div>

      <div style={s.lessonsList}>
        {lessons.map((lesson, li) => (
          <div key={lesson.id} style={{
            ...s.lessonRow,
            opacity: lesson.locked ? 0.4 : 1,
            cursor: lesson.locked ? "default" : "pointer",
          }} onClick={() => !lesson.locked && handleStartLesson(lesson)}>
            <div style={{
              ...s.lessonDot,
              background: lesson.completed ? "#21a038" : lesson.locked ? "rgba(0,0,0,0.06)" : lesson.generated ? "#9c27b0" : "#ffdd2d",
            }}>
              {lesson.completed ? "✓" : lesson.locked ? "🔒" : lesson.generated ? "🤖" : li + 1}
            </div>
            <div style={s.lessonInfo}>
              <div style={s.lessonTitle}>{lesson.title}</div>
              <div style={s.lessonSub}>{lesson.subtitle}</div>
            </div>
            <div style={s.lessonMeta}>
              <span>⏱ {lesson.duration_min} мин</span>
              <span style={{ color: "#ffdd2d" }}>+{lesson.xp_reward} XP</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const s = {
  page: { maxWidth: 800, margin: "0 auto" },
  loading: { color: "rgba(0,0,0,0.45)", padding: 40, textAlign: "center" },
  pageTitle: { fontSize: 28, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "rgba(0,0,0,0.4)", marginBottom: 24 },
  lessonsList: { display: "flex", flexDirection: "column", gap: 8 },
  lessonRow: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "16px 18px", borderRadius: 14,
    background: "#ffffff", border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
    transition: "background 0.2s",
  },
  lessonDot: {
    width: 32, height: 32, borderRadius: "50%",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 13, fontWeight: 700, color: "#fff", flexShrink: 0,
  },
  lessonInfo: { flex: 1 },
  lessonTitle: { fontSize: 15, fontWeight: 600, color: "#1a1a1a" },
  lessonSub: { fontSize: 12, color: "rgba(0,0,0,0.4)" },
  lessonMeta: {
    display: "flex", flexDirection: "column", alignItems: "flex-end",
    gap: 2, fontSize: 11, color: "rgba(0,0,0,0.4)",
  },
}
