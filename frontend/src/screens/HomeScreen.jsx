import { useState, useEffect } from "react"
import { getDashboard, marketEventAction, checkPortfolio } from "../api"

export default function HomeScreen({ onStartLesson, onNavigate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const load = () => { setLoading(true); setError(null); getDashboard().then(d => { setData(d); setLoading(false) }).catch(e => { setError(e.message||"Ошибка"); setLoading(false) }); checkPortfolio().catch(() => {}) }
  useEffect(() => { load() }, [])

  if (loading) return <div style={s.loading}>Загрузка...</div>
  if (error || !data) return <div style={s.loading}><div style={{fontSize:48,marginBottom:16}}>⚠️</div><div style={{marginBottom:16}}>{error||"Ошибка"}</div><button onClick={load} style={{padding:"10px 24px",borderRadius:10,border:"1px solid rgba(255,255,255,0.15)",background:"transparent",color:"#b8860b",cursor:"pointer",fontFamily:"inherit"}}>Повторить</button></div>

  const { portfolio, next_lesson, daily_missions, market_event, module_progress, stats } = data

  return (
    <div style={s.page}>
      {/* Portfolio Widget */}
      <div style={s.portfolioCard} onClick={() => onNavigate("portfolio")}>
        <div style={s.portfolioHeader}>
          <div>
            <div style={s.portfolioLabel}>ПОРТФЕЛЬ</div>
            <div style={s.portfolioValue}>
              {(portfolio?.total_value || 0).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽
            </div>
            <div style={{
              ...s.portfolioPnl,
              color: (portfolio?.total_pnl || 0) >= 0 ? "#21a038" : "#f44336"
            }}>
              {(portfolio?.total_pnl || 0) >= 0 ? "+" : ""}
              {(portfolio?.total_pnl || 0).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽
              {" "}({(portfolio?.total_pnl_pct || 0) >= 0 ? "+" : ""}{(portfolio?.total_pnl_pct || 0).toFixed(2)}%)
            </div>
          </div>
          <div style={{ opacity: 0.7, fontSize: 32 }}>📈</div>
        </div>
      </div>

      {/* Next Lesson + Daily Missions */}
      <div style={s.row}>
        <div style={s.card}>
          <div style={s.cardLabel}>СЛЕДУЮЩИЙ УРОК</div>
          {next_lesson ? (
            <>
              <div style={s.lessonModule}>{next_lesson.module_icon} {next_lesson.module_title}</div>
              <div style={s.lessonTitle}>{next_lesson.title}</div>
              <div style={s.lessonSub}>{next_lesson.subtitle}</div>
              <div style={s.lessonMeta}>
                <span>⏱ ~{next_lesson.duration_min} мин</span>
                <span>+{next_lesson.xp_reward} XP</span>
              </div>
              <button style={s.startBtn} onClick={() => onStartLesson(next_lesson.id)}>
                Начать →
              </button>
            </>
          ) : (
            <div style={s.allDone}><span style={{ fontSize: 40 }}>🎉</span><div>Все уроки пройдены!</div></div>
          )}
        </div>

        <div style={s.card}>
          <div style={s.cardLabel}>ЕЖЕДНЕВНЫЕ МИССИИ</div>
          <div style={s.missionsList}>
            {daily_missions?.map((m, i) => (
              <div key={i} style={s.missionItem}>
                <span style={{ fontSize: 16 }}>{m.completed ? "✅" : "⬜"}</span>
                <span style={{
                  flex: 1, fontSize: 13, color: "#1a1a1a",
                  textDecoration: m.completed ? "line-through" : "none",
                  opacity: m.completed ? 0.5 : 1,
                }}>
                  {m.icon} {m.text}
                </span>
                <span style={{ fontSize: 11, color: "#b8860b", fontWeight: 600 }}>+{m.xp}</span>
              </div>
            ))}
          </div>
          {daily_missions?.every(m => m.completed) && (
            <div style={s.bonusBanner}>🎁 Бонус: +50 XP</div>
          )}
        </div>
      </div>

      {/* Market Event */}
      {market_event && !market_event.seen && (
        <div style={s.eventCard}>
          <div style={{ fontSize: 11, color: "#b8860b", fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>
            📰 РЫНОЧНОЕ СОБЫТИЕ
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#1a1a1a", marginBottom: 6 }}>
            {market_event.headline}
          </div>
          <div style={{ fontSize: 13, color: "rgba(0,0,0,0.5)", marginBottom: 12, lineHeight: 1.5 }}>
            {market_event.detail}
          </div>
          {Object.keys(market_event.affected_holdings || {}).length > 0 && (
            <div style={{ marginBottom: 12 }}>
              {Object.entries(market_event.affected_holdings).map(([ticker, info]) => (
                <div key={ticker} style={{ display: "flex", gap: 12, fontSize: 14, padding: "4px 0", color: "#1a1a1a" }}>
                  <span>{info.name}</span>
                  <span style={{ color: info.impact_pct >= 0 ? "#21a038" : "#f44336", fontWeight: 700 }}>
                    {info.impact_pct >= 0 ? "+" : ""}{info.impact_pct}%
                  </span>
                  <span style={{ color: "rgba(0,0,0,0.45)", fontSize: 12 }}>
                    ({info.impact_amount >= 0 ? "+" : ""}{info.impact_amount?.toLocaleString("ru-RU")} ₽)
                  </span>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: 8 }}>
            {["Подробнее", "Продать?", "Держать"].map((label, i) => (
              <button key={i} onClick={() => {
                marketEventAction(market_event.id, ["details", "sell", "hold"][i])
                  .then(() => setData(d => ({ ...d, market_event: { ...market_event, seen: true } })))
              }} style={{
                flex: 1, padding: "10px 0", border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8, background: "transparent", fontSize: 13, cursor: "pointer",
                fontFamily: "inherit", transition: "all 0.2s",
                color: i === 1 ? "#f44336" : i === 2 ? "#21a038" : "rgba(255,255,255,0.7)",
                borderColor: i === 1 ? "rgba(239,83,80,0.3)" : i === 2 ? "rgba(76,175,80,0.3)" : "rgba(255,255,255,0.1)",
              }}>{label}</button>
            ))}
          </div>
        </div>
      )}

      {/* Module Progress */}
      <div style={s.card}>
        <div style={s.cardLabel}>ПРОГРЕСС ОБУЧЕНИЯ</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {module_progress?.map(m => (
            <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 20, width: 28, textAlign: "center" }}>{m.locked ? "🔒" : m.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a", marginBottom: 4 }}>{m.title}</div>
                <div style={{ height: 6, background: "rgba(0,0,0,0.06)", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{
                    height: "100%", width: `${m.progress_pct}%`,
                    background: "linear-gradient(90deg, #ffdd2d, #ffa000)",
                    borderRadius: 3, transition: "width 0.5s",
                    opacity: m.locked ? 0.3 : 1,
                  }} />
                </div>
              </div>
              <span style={{ fontSize: 12, color: "rgba(0,0,0,0.4)", width: 36, textAlign: "right" }}>
                {m.locked ? "" : `${m.progress_pct}%`}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div style={s.statsRow}>
        {[
          { emoji: "🏅", num: stats?.lessons_completed || 0, label: "уроков" },
          { emoji: "📊", num: stats?.trades_made || 0, label: "сделок" },
          { emoji: "💰", num: `${(stats?.portfolio_return_pct || 0) >= 0 ? "+" : ""}${stats?.portfolio_return_pct || 0}%`, label: "доходность" },
          { emoji: "🏆", num: stats?.achievements || 0, label: "достижений" },
        ].map((st, i) => (
          <div key={i} style={s.statCard}>
            <div style={{ fontSize: 24, marginBottom: 4 }}>{st.emoji}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#1a1a1a", marginBottom: 2 }}>{st.num}</div>
            <div style={{ fontSize: 11, color: "rgba(0,0,0,0.4)" }}>{st.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

const s = {
  page: { maxWidth: 900, margin: "0 auto" },
  loading: { color: "rgba(0,0,0,0.45)", padding: 40, textAlign: "center", fontSize: 16 },
  portfolioCard: {
    background: "#ffffff",
    borderRadius: 16, padding: "24px 28px", marginBottom: 20,
    cursor: "pointer", border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  portfolioHeader: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  portfolioLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", letterSpacing: 2, marginBottom: 8, fontWeight: 600 },
  portfolioValue: { fontSize: 32, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  portfolioPnl: { fontSize: 15, fontWeight: 600 },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 },
  card: {
    background: "#ffffff", borderRadius: 16, padding: "20px 24px",
    border: "1px solid rgba(0,0,0,0.08)", marginBottom: 20,
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  cardLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", letterSpacing: 2, marginBottom: 12, fontWeight: 600 },
  lessonModule: { fontSize: 12, color: "rgba(0,0,0,0.5)", marginBottom: 6 },
  lessonTitle: { fontSize: 18, fontWeight: 700, color: "#1a1a1a", marginBottom: 4 },
  lessonSub: { fontSize: 13, color: "rgba(0,0,0,0.5)", marginBottom: 12 },
  lessonMeta: { display: "flex", gap: 16, fontSize: 12, color: "rgba(0,0,0,0.4)", marginBottom: 16 },
  startBtn: {
    width: "100%", padding: "12px 0", border: "none", borderRadius: 10,
    background: "#ffdd2d", color: "#1a1a1a", fontSize: 15, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit",
  },
  allDone: { textAlign: "center", padding: "20px 0", color: "rgba(0,0,0,0.5)", fontSize: 14 },
  missionsList: { display: "flex", flexDirection: "column", gap: 10 },
  missionItem: { display: "flex", alignItems: "center", gap: 8 },
  bonusBanner: {
    marginTop: 12, padding: "8px 12px", background: "rgba(255,221,45,0.15)",
    borderRadius: 8, color: "#b8860b", fontSize: 12, fontWeight: 600, textAlign: "center",
  },
  eventCard: {
    background: "#ffffff",
    borderRadius: 16, padding: "20px 24px", marginBottom: 20,
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  statsRow: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 },
  statCard: {
    background: "#ffffff", borderRadius: 12, padding: "16px 12px",
    textAlign: "center", border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
  },
}
