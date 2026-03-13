import { useState, useEffect } from "react"
import { getProgress } from "../api"

export default function FeedbackScreen({ result, onNext }) {
  const [progress, setProgress] = useState(null)

  useEffect(() => {
    getProgress().then(setProgress)
  }, [])

  const correct = result?.is_correct

  return (
    <div style={s.page}>
      <div style={s.card}>
        {/* Status banner */}
        <div style={{ ...s.banner, background: correct ? "#e8f5e9" : "#ffebee" }}>
          <span style={{ fontSize: 28 }}>{correct ? "✅" : "❌"}</span>
          <div>
            <div style={{ ...s.bannerTitle, color: correct ? "#2e7d32" : "#c62828" }}>
              {correct ? "Правильно!" : "Неправильно"}
            </div>
            {!correct && result?.correct_index != null && (
              <div style={s.bannerSub}>
                Правильный ответ: <strong>{result.card.options[result.correct_index]}</strong>
              </div>
            )}
          </div>
        </div>

        {/* Progress bar block */}
        {progress && (
          <div style={s.progressBlock}>
            <div style={s.progressRow}>
              <span style={s.progressLabel}>Прогресс</span>
              <span style={s.progressPct}>{Math.min(100, progress.correct_total * 10)}%</span>
            </div>
            <div style={s.barTrack}>
              <div style={{ ...s.barFill, width: `${Math.min(100, progress.correct_total * 10)}%` }} />
            </div>
          </div>
        )}

        {/* Stats */}
        {progress && (
          <div style={s.stats}>
            <div style={s.stat}>
              <span style={s.statValue}>🔥 {progress.streak}</span>
              <span style={s.statLabel}>{declension(progress.streak, ["день подряд", "дня подряд", "дней подряд"])}</span>
            </div>
            <div style={s.divider} />
            <div style={s.stat}>
              <span style={s.statValue}>✓ {progress.correct_total}</span>
              <span style={s.statLabel}>правильных ответов</span>
            </div>
          </div>
        )}

        <button style={s.btn} onClick={onNext}>Посмотреть прогресс →</button>
      </div>
    </div>
  )
}

function declension(n, [one, few, many]) {
  const mod10 = n % 10, mod100 = n % 100
  if (mod100 >= 11 && mod100 <= 14) return many
  if (mod10 === 1) return one
  if (mod10 >= 2 && mod10 <= 4) return few
  return many
}

const s = {
  page:         { background: "#fff", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "32px 16px", fontFamily: "'Inter', sans-serif", minHeight: "calc(100vh - 56px)" },
  card:         { background: "#fff", borderRadius: 16, padding: "28px 28px 32px", maxWidth: 680, width: "100%", boxShadow: "0 1px 4px rgba(0,0,0,0.08)", border: "1px solid #ebebeb" },
  banner:       { display: "flex", alignItems: "center", gap: 16, padding: "18px 20px", borderRadius: 12, marginBottom: 24 },
  bannerTitle:  { fontSize: 18, fontWeight: 700, marginBottom: 4 },
  bannerSub:    { fontSize: 14, color: "#555" },
  progressBlock:{ marginBottom: 24 },
  progressRow:  { display: "flex", justifyContent: "space-between", marginBottom: 8 },
  progressLabel:{ fontSize: 14, color: "#888" },
  progressPct:  { fontSize: 14, color: "#888" },
  barTrack:     { height: 8, background: "#f0f0f0", borderRadius: 4, overflow: "hidden" },
  barFill:      { height: "100%", background: "#FFD600", borderRadius: 4, transition: "width 0.5s ease" },
  stats:        { display: "flex", alignItems: "center", background: "#fafafa", border: "1px solid #ebebeb", borderRadius: 12, padding: "16px 24px", marginBottom: 24, gap: 0 },
  stat:         { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 },
  statValue:    { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  statLabel:    { fontSize: 13, color: "#888" },
  divider:      { width: 1, height: 40, background: "#e0e0e0" },
  btn:          { width: "100%", padding: "14px 0", fontSize: 15, fontWeight: 600, borderRadius: 12, background: "#FFD600", color: "#1a1a1a", border: "none", cursor: "pointer" },
}
