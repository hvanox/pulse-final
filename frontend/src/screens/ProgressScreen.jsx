import { useState, useEffect } from "react"
import { getProgress } from "../api"

export default function ProgressScreen({ onNext }) {
  const [progress, setProgress] = useState(null)

  useEffect(() => {
    getProgress().then(setProgress)
  }, [])

  if (!progress)
    return <div style={s.loading}>Загрузка...</div>

  const pct = Math.min(100, progress.correct_total * 10)

  return (
    <div style={s.page}>
      {/* Course card (top) */}
      <div style={s.courseCard}>
        <div style={s.courseIconWrap}>
          <div style={s.courseIcon}>📊</div>
        </div>
        <div style={s.courseInfo}>
          <div style={s.courseTitle}>Твой прогресс</div>
          <div style={s.courseSub}>Урок {progress.correct_total} · финансы</div>
          <div style={s.barTrack}>
            <div style={{ ...s.barFill, width: `${pct}%` }} />
          </div>
          <div style={s.barRow}>
            <span style={s.barLabel}>Прогресс</span>
            <span style={s.barLabel}>{pct}%</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div style={s.statsRow}>
        <div style={s.statCard}>
          <div style={s.statValue}>🔥 {progress.streak}</div>
          <div style={s.statLabel}>дней подряд</div>
        </div>
        <div style={s.statCard}>
          <div style={s.statValue}>✓ {progress.correct_total}</div>
          <div style={s.statLabel}>правильных ответов</div>
        </div>
      </div>

      <p style={s.hint}>Приходи завтра — карточка будет другая 💡</p>

      <button style={s.btn} onClick={onNext}>Следующая карточка →</button>
    </div>
  )
}

const s = {
  page:        { background: "#fff", display: "flex", flexDirection: "column", alignItems: "center", padding: "32px 16px", fontFamily: "'Inter', sans-serif", gap: 16, minHeight: "calc(100vh - 56px)" },
  loading:     { textAlign: "center", marginTop: 100, color: "#888", fontFamily: "sans-serif" },
  courseCard:  { background: "#fff", borderRadius: 16, padding: "24px", maxWidth: 680, width: "100%", boxShadow: "0 1px 4px rgba(0,0,0,0.08)", border: "1px solid #ebebeb", display: "flex", gap: 20, alignItems: "center" },
  courseIconWrap: { flexShrink: 0 },
  courseIcon:  { width: 80, height: 80, background: "#7c4dff", borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 36 },
  courseInfo:  { flex: 1 },
  courseTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a", marginBottom: 4 },
  courseSub:   { fontSize: 13, color: "#888", marginBottom: 12 },
  barTrack:    { height: 8, background: "#f0f0f0", borderRadius: 4, overflow: "hidden", marginBottom: 6 },
  barFill:     { height: "100%", background: "#FFD600", borderRadius: 4 },
  barRow:      { display: "flex", justifyContent: "space-between" },
  barLabel:    { fontSize: 12, color: "#aaa" },
  statsRow:    { display: "flex", gap: 12, maxWidth: 680, width: "100%" },
  statCard:    { flex: 1, background: "#fff", borderRadius: 16, padding: "24px 16px", textAlign: "center", boxShadow: "0 1px 4px rgba(0,0,0,0.06)", border: "1px solid #ebebeb" },
  statValue:   { fontSize: 36, fontWeight: 700, color: "#1a1a1a", marginBottom: 6 },
  statLabel:   { fontSize: 14, color: "#888" },
  hint:        { fontSize: 14, color: "#aaa", maxWidth: 680, width: "100%", textAlign: "center", margin: "4px 0" },
  btn:         { maxWidth: 680, width: "100%", padding: "14px 0", fontSize: 15, fontWeight: 600, borderRadius: 12, background: "#FFD600", color: "#1a1a1a", border: "none", cursor: "pointer" },
}
