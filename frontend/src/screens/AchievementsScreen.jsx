import { useState, useEffect } from "react"
import { getAchievements } from "../api"

export default function AchievementsScreen() {
  const [achievements, setAchievements] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState("all")
  const loadAch = () => { setLoading(true); setError(null); getAchievements().then(a => { setAchievements(a); setLoading(false) }).catch(e => { setError(e.message||"Ошибка"); setLoading(false) }) }
  useEffect(() => { loadAch() }, [])

  if (loading) return <div style={s.loading}>Загрузка...</div>
  if (error) return <div style={s.loading}><div style={{fontSize:48,marginBottom:16}}>⚠️</div><div style={{marginBottom:16}}>{error}</div><button onClick={loadAch} style={{padding:"10px 24px",borderRadius:10,border:"1px solid rgba(0,0,0,0.1)",background:"transparent",color:"#ffdd2d",cursor:"pointer",fontFamily:"inherit"}}>Повторить</button></div>

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
            background: ach.unlocked ? "rgba(255,221,45,0.05)" : "#f6f7f8",
            borderColor: ach.unlocked ? "rgba(255,221,45,0.15)" : "rgba(0,0,0,0.04)",
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
  loading: { color: "rgba(0,0,0,0.45)", padding: 40, textAlign: "center" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  title: { fontSize: 28, fontWeight: 800, color: "#1a1a1a" },
  counter: { fontSize: 18, fontWeight: 700, color: "#ffdd2d" },
  progressBox: { marginBottom: 20 },
  progressBar: {
    height: 8, background: "rgba(0,0,0,0.06)", borderRadius: 4, overflow: "hidden", marginBottom: 4,
  },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #ffdd2d, #FFA000)",
    borderRadius: 4, transition: "width 0.5s",
  },
  progressText: { fontSize: 12, color: "rgba(0,0,0,0.4)" },
  filters: { display: "flex", gap: 4, marginBottom: 20, flexWrap: "wrap" },
  filterBtn: {
    padding: "6px 14px", border: "1px solid rgba(0,0,0,0.06)", borderRadius: 8,
    background: "transparent", color: "rgba(0,0,0,0.45)", fontSize: 12,
    cursor: "pointer", fontFamily: "inherit",
  },
  filterActive: { background: "rgba(255,221,45,0.1)", color: "#ffdd2d", borderColor: "rgba(255,221,45,0.2)" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 },
  achCard: {
    borderRadius: 14, padding: "20px 16px", textAlign: "center",
    border: "1px solid rgba(0,0,0,0.04)", transition: "all 0.2s",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  achIcon: { fontSize: 36, marginBottom: 8 },
  achName: { fontSize: 14, fontWeight: 700, color: "#1a1a1a", marginBottom: 4 },
  achDesc: { fontSize: 11, color: "rgba(0,0,0,0.4)", marginBottom: 8, lineHeight: 1.4 },
  achDate: { fontSize: 10, color: "rgba(0,0,0,0.3)", marginBottom: 4 },
  achXp: { fontSize: 11, color: "#ffdd2d", fontWeight: 600 },
}
