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
            opacity: ach.unlocked ? 1 : 0.5,
            background: ach.unlocked ? "#fff" : "#f0f0f0",
            borderColor: ach.unlocked ? "rgba(33,160,56,0.2)" : "rgba(0,0,0,0.06)",
            boxShadow: ach.unlocked ? "0 2px 12px rgba(33,160,56,0.1)" : "none",
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
  counter: { fontSize: 18, fontWeight: 700, color: "#b8860b" },
  progressBox: { marginBottom: 20 },
  progressBar: {
    height: 8, background: "rgba(0,0,0,0.08)", borderRadius: 4, overflow: "hidden", marginBottom: 6,
  },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #ffdd2d, #FFA000)",
    borderRadius: 4, transition: "width 0.5s",
  },
  progressText: { fontSize: 12, color: "rgba(0,0,0,0.5)" },
  filters: { display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" },
  filterBtn: {
    padding: "8px 16px", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 10,
    background: "#fff", color: "rgba(0,0,0,0.55)", fontSize: 13,
    cursor: "pointer", fontFamily: "inherit", fontWeight: 500,
  },
  filterActive: { background: "#1a1a1a", color: "#fff", borderColor: "#1a1a1a" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 14 },
  achCard: {
    borderRadius: 16, padding: "24px 18px", textAlign: "center",
    border: "1px solid rgba(0,0,0,0.08)", transition: "all 0.2s",
    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  },
  achIcon: { fontSize: 40, marginBottom: 10 },
  achName: { fontSize: 15, fontWeight: 700, color: "#1a1a1a", marginBottom: 6 },
  achDesc: { fontSize: 12, color: "rgba(0,0,0,0.55)", marginBottom: 10, lineHeight: 1.5 },
  achDate: { fontSize: 11, color: "rgba(0,0,0,0.4)", marginBottom: 6 },
  achXp: { fontSize: 12, color: "#b8860b", fontWeight: 700 },
}
