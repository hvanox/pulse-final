import { useState, useEffect } from "react"
import { getModules, getModuleLessons } from "../api"

export default function LearnScreen({ onStartLesson }) {
  const [modules, setModules] = useState([])
  const [expandedModule, setExpandedModule] = useState(null)
  const [lessons, setLessons] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const loadMods = () => { setLoading(true); setError(null); getModules().then(m => { setModules(m); setLoading(false) }).catch(e => { setError(e.message||"Ошибка"); setLoading(false) }) }
  useEffect(() => { loadMods() }, [])

  const toggleModule = async (moduleId) => {
    if (expandedModule === moduleId) { setExpandedModule(null); return }
    setExpandedModule(moduleId)
    if (!lessons[moduleId]) {
      try { const data = await getModuleLessons(moduleId); setLessons(prev => ({ ...prev, [moduleId]: data })) } catch {}
    }
  }

  if (loading) return <div style={s.loading}>Загрузка...</div>
  if (error) return <div style={s.loading}><div style={{fontSize:48,marginBottom:16}}>⚠️</div><div style={{marginBottom:16}}>{error}</div><button onClick={loadMods} style={{padding:"10px 24px",borderRadius:10,border:"1px solid rgba(255,255,255,0.15)",background:"transparent",color:"#FFD600",cursor:"pointer",fontFamily:"inherit"}}>Повторить</button></div>

  return (
    <div style={s.page}>
      <div style={s.pageTitle}>Обучение</div>
      <div style={s.subtitle}>6 модулей · 25 уроков · от основ до стратегий</div>

      <div style={s.modulesList}>
        {modules.map((m, idx) => (
          <div key={m.id} style={s.moduleCard}>
            <div style={{
              ...s.moduleHeader,
              opacity: m.locked ? 0.5 : 1,
              cursor: m.locked ? "default" : "pointer",
            }} onClick={() => !m.locked && toggleModule(m.id)}>
              <div style={s.moduleNum}>{idx + 1}</div>
              <div style={s.moduleIcon}>{m.locked ? "🔒" : m.icon}</div>
              <div style={s.moduleInfo}>
                <div style={s.moduleTitle}>{m.title}</div>
                <div style={s.moduleDesc}>{m.description}</div>
                <div style={s.moduleProgress}>
                  <div style={s.progressBar}>
                    <div style={{ ...s.progressFill, width: `${m.progress_pct}%` }} />
                  </div>
                  <span style={s.progressText}>
                    {m.completed_count}/{m.total_lessons} уроков
                  </span>
                </div>
              </div>
              <div style={s.moduleArrow}>
                {m.locked ? "" : expandedModule === m.id ? "▲" : "▼"}
              </div>
            </div>

            {/* Expanded lessons */}
            {expandedModule === m.id && lessons[m.id] && (
              <div style={s.lessonsList}>
                {lessons[m.id].map((lesson, li) => (
                  <div key={lesson.id} style={{
                    ...s.lessonRow,
                    opacity: lesson.locked ? 0.4 : 1,
                    cursor: lesson.locked ? "default" : "pointer",
                  }} onClick={() => !lesson.locked && onStartLesson(lesson.id)}>
                    <div style={{
                      ...s.lessonDot,
                      background: lesson.completed ? "#4caf50" : lesson.locked ? "rgba(255,255,255,0.1)" : "#FFD600",
                    }}>
                      {lesson.completed ? "✓" : lesson.locked ? "🔒" : li + 1}
                    </div>
                    <div style={s.lessonInfo}>
                      <div style={s.lessonTitle}>{lesson.title}</div>
                      <div style={s.lessonSub}>{lesson.subtitle}</div>
                    </div>
                    <div style={s.lessonMeta}>
                      <span>⏱ {lesson.duration_min} мин</span>
                      <span style={{ color: "#FFD600" }}>+{lesson.xp_reward} XP</span>
                    </div>
                    {lesson.completed && (
                      <span style={s.completedBadge}>✅</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const s = {
  page: { maxWidth: 800, margin: "0 auto" },
  loading: { color: "rgba(255,255,255,0.5)", padding: 40, textAlign: "center" },
  pageTitle: { fontSize: 28, fontWeight: 800, color: "#fff", marginBottom: 4 },
  subtitle: { fontSize: 14, color: "rgba(255,255,255,0.4)", marginBottom: 24 },
  modulesList: { display: "flex", flexDirection: "column", gap: 12 },
  moduleCard: {
    background: "#1a2634", borderRadius: 16,
    border: "1px solid rgba(255,255,255,0.06)", overflow: "hidden",
  },
  moduleHeader: {
    display: "flex", alignItems: "center", gap: 14,
    padding: "18px 20px",
  },
  moduleNum: {
    width: 28, height: 28, borderRadius: "50%",
    background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.3)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 13, fontWeight: 700, flexShrink: 0,
  },
  moduleIcon: { fontSize: 24, flexShrink: 0 },
  moduleInfo: { flex: 1 },
  moduleTitle: { fontSize: 16, fontWeight: 700, color: "#e8eaed", marginBottom: 2 },
  moduleDesc: { fontSize: 12, color: "rgba(255,255,255,0.4)", marginBottom: 8 },
  moduleProgress: { display: "flex", alignItems: "center", gap: 10 },
  progressBar: {
    flex: 1, height: 5, background: "rgba(255,255,255,0.08)",
    borderRadius: 3, overflow: "hidden",
  },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #FFD600, #FFA000)",
    borderRadius: 3, transition: "width 0.4s",
  },
  progressText: { fontSize: 11, color: "rgba(255,255,255,0.4)", flexShrink: 0 },
  moduleArrow: { fontSize: 12, color: "rgba(255,255,255,0.3)", flexShrink: 0 },
  lessonsList: {
    borderTop: "1px solid rgba(255,255,255,0.04)",
    padding: "8px 12px 12px",
  },
  lessonRow: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "12px 14px", borderRadius: 10,
    transition: "background 0.2s",
  },
  lessonDot: {
    width: 28, height: 28, borderRadius: "50%",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 12, fontWeight: 700, color: "#000", flexShrink: 0,
  },
  lessonInfo: { flex: 1 },
  lessonTitle: { fontSize: 14, fontWeight: 600, color: "#e8eaed" },
  lessonSub: { fontSize: 12, color: "rgba(255,255,255,0.4)" },
  lessonMeta: {
    display: "flex", flexDirection: "column", alignItems: "flex-end",
    gap: 2, fontSize: 11, color: "rgba(255,255,255,0.4)",
  },
  completedBadge: { fontSize: 16, marginLeft: 4 },
}
