import { useState, useEffect } from "react"
import { getAchievements } from "../api"

export default function AchievementsScreen() {
  const [achievements, setAchievements] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState("all")

  const loadAchievements = () => {
    setLoading(true)
    setError(null)
    getAchievements()
      .then(a => { setAchievements(a); setLoading(false) })
      .catch(err => { setError(err.message || "Не удалось загрузить достижения"); setLoading(false) })
  }

  useEffect(() => { loadAchievements() }, [])

  if (loading) return <div style={s.loading}>Загрузка...</div>

  if (error) return (
    <div style={s.loading}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <div style={{ marginBottom: 16 }}>{error}</div>
      <button onClick={loadAchievements} style={{ padding: "10px 24px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.15)", background: "transparent", color: "#FFD600", cursor: "pointer", fontFamily: "inherit", fontSize: 14 }}>
        Попробовать снова
      </button>
    </div>
  )

  const categories = [
    { id: "all", label: "Все" },
    { id: "learning", label: "Обучение" },
    { id: "portfolio", label: "Портфель" },
    { id: "decisions", label: "Решения" },
    { id: "streak", label: "Серия" },
  ]

  const filtered = filter === "all" ? achievements : achievements.filter(a => a.category === filter)
  const unlockedCount = achievements.filter(a => a.unlocked).length

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div style={s.title}>Достижения</div>
        <div style={s.counter}>{unlockedCount}/{achievements.length}</div>
      </div>

      {/* Progress */}
      <div style={s.progressBox}>
        <div style={s.progressBar}>
          <div style={{
            ...s.progressFill,
            width: `${(unlockedCount / Math.max(achievements.length, 1)) * 100}%`
          }} />
        </div>
        <div style={s.progressText}>
          {Math.round((unlockedCount / Math.max(achievements.length, 1)) * 100)}% открыто
        </div>
      </div>

      {/* Filters */}
      <div style={s.filters}>
        {categories.map(c => (
          <button
            key={c.id}
            onClick={() => setFilter(c.id)}
            style={{
              ...s.filterBtn,
              ...(filter === c.id ? s.filterActive : {}),
            }}
          >{c.label}</button>
        ))}
      </div>

      {/* Grid */}
      <div style={s.grid}>
        {filtered.map(ach => (
          <div key={ach.id} style={{
            ...s.achCard,
            opacity: ach.unlocked ? 1 : 0.4,
            background: ach.unlocked ? "rgba(255,214,0,0.05)" : "#1a2634",
            borderColor: ach.unlocked ? "rgba(255,214,0,0.15)" : "rgba(255,255,255,0.04)",
          }}>
            <div style={s.achIcon}>{ach.unlocked ? ach.icon : "🔒"}</div>
            <div style={s.achName}>{ach.name}</div>
            <div style={s.achDesc}>{ach.description}</div>
            {ach.unlocked && (
              <div style={s.achDate}>
                {new Date(ach.unlocked_at).toLocaleDateString("ru-RU")}
              </div>
            )}
            <div style={s.achXp}>+{ach.xp_reward} XP</div>
          </div>
        ))}
      </div>
    </div>
  )
}

const s = {
  page: { maxWidth: 800, margin: "0 auto" },
  loading: { color: "rgba(255,255,255,0.5)", padding: 40, textAlign: "center" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  title: { fontSize: 28, fontWeight: 800, color: "#fff" },
  counter: { fontSize: 18, fontWeight: 700, color: "#FFD600" },
  progressBox: { marginBottom: 20 },
  progressBar: {
    height: 8, background: "rgba(255,255,255,0.08)", borderRadius: 4, overflow: "hidden", marginBottom: 4,
  },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #FFD600, #FFA000)",
    borderRadius: 4, transition: "width 0.5s",
  },
  progressText: { fontSize: 12, color: "rgba(255,255,255,0.4)" },
  filters: { display: "flex", gap: 4, marginBottom: 20, flexWrap: "wrap" },
  filterBtn: {
    padding: "6px 14px", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8,
    background: "transparent", color: "rgba(255,255,255,0.5)", fontSize: 12,
    cursor: "pointer", fontFamily: "inherit",
  },
  filterActive: { background: "rgba(255,214,0,0.1)", color: "#FFD600", borderColor: "rgba(255,214,0,0.2)" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 },
  achCard: {
    borderRadius: 14, padding: "20px 16px", textAlign: "center",
    border: "1px solid rgba(255,255,255,0.04)", transition: "all 0.2s",
  },
  achIcon: { fontSize: 36, marginBottom: 8 },
  achName: { fontSize: 14, fontWeight: 700, color: "#e8eaed", marginBottom: 4 },
  achDesc: { fontSize: 11, color: "rgba(255,255,255,0.4)", marginBottom: 8, lineHeight: 1.4 },
  achDate: { fontSize: 10, color: "rgba(255,255,255,0.3)", marginBottom: 4 },
  achXp: { fontSize: 11, color: "#FFD600", fontWeight: 600 },
}
