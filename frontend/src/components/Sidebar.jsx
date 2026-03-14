import { useState, useEffect } from "react"
import { getDashboard } from "../api"

export default function Sidebar({ active, onNavigate, userName, onLogout, refreshKey }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    getDashboard().then(setData).catch(() => {})
  }, [refreshKey, active])

  const level = data?.level_info?.current || { name: "Наблюдатель", icon: "👁️", level: 1 }
  const xp = data?.xp || 0
  const xpProgress = data?.level_info?.progress || 0
  const streak = data?.streak || 0
  const portfolioValue = data?.portfolio?.total_value || 1000000
  const portfolioPnl = data?.portfolio?.total_pnl_pct || 0

  const tabs = [
    { id: "home", label: "Главная", icon: "/icons/free-icon-home-6529015.png" },
    { id: "portfolio", label: "Портфель", icon: "/icons/free-icon-graphic-progression-69856.png" },
    { id: "learn", label: "Обучение", icon: "/icons/free-icon-star-11465609.png" },
    { id: "achievements", label: "Достижения", icon: "/icons/free-icon-checkmark-16703458.png" },
    { id: "settings", label: "Настройки", icon: "/icons/free-icon-setting-6619132.png" },
  ]

  return (
    <div style={s.sidebar}>
      {/* Logo */}
      <div style={s.logo}>
        <img src="/icons/T-Bank_RU_logo.svg.png" alt="T-Bank" style={s.logoImg} />
      </div>

      <div style={s.divider} />

      {/* Portfolio Summary */}
      <div style={s.portfolioBox} onClick={() => onNavigate("portfolio")}>
        <div style={s.portfolioLabel}>ПОРТФЕЛЬ</div>
        <div style={s.portfolioValue}>
          {portfolioValue.toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽
        </div>
        <div style={{
          ...s.portfolioPnl,
          color: portfolioPnl >= 0 ? "#21a038" : "#f44336"
        }}>
          {portfolioPnl >= 0 ? "+" : ""}{portfolioPnl.toFixed(2)}%
          {portfolioPnl >= 0 ? " ↑" : " ↓"}
        </div>
      </div>

      <div style={s.divider} />

      {/* Navigation */}
      <nav style={s.nav}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => onNavigate(t.id)}
            style={{
              ...s.navBtn,
              ...(active === t.id ? s.navBtnActive : {}),
            }}
          >
            <img src={t.icon} alt="" style={s.navIconImg} />
            <span>{t.label}</span>
          </button>
        ))}
      </nav>

      <div style={s.divider} />

      {/* Level & XP */}
      <div style={s.levelBox}>
        <div style={s.levelHeader}>
          <span style={s.levelIcon}>{level.icon}</span>
          <span style={s.levelName}>{level.name}</span>
        </div>
        <div style={s.xpBar}>
          <div style={{ ...s.xpFill, width: `${Math.min(xpProgress * 100, 100)}%` }} />
        </div>
        <div style={s.xpText}>{xp} XP</div>
      </div>

      {/* Streak */}
      {streak > 0 && (
        <div style={s.streakBox}>
          <img src="/icons/free-icon-flames-4201705.png" alt="" style={{ width: 20, height: 20 }} />
          <span style={s.streakNum}>{streak}</span>
          <span style={s.streakLabel}>{streak === 1 ? "день" : streak < 5 ? "дня" : "дней"}</span>
        </div>
      )}

      <div style={{ flex: 1 }} />

      {/* User */}
      <div style={s.userBox}>
        <div style={s.avatar}>{userName?.[0]?.toUpperCase() || "?"}</div>
        <div style={s.userInfo}>
          <div style={s.userName}>{userName}</div>
          <div style={s.userEmail}>{localStorage.getItem("pulse_email") || ""}</div>
        </div>
      </div>
      <button onClick={onLogout} style={s.logoutBtn}>Выйти</button>
    </div>
  )
}

const s = {
  sidebar: {
    position: "fixed",
    left: 0,
    top: 0,
    bottom: 0,
    width: 260,
    background: "#ffffff",
    borderRight: "1px solid rgba(0,0,0,0.08)",
    display: "flex",
    flexDirection: "column",
    padding: "20px 16px",
    zIndex: 100,
    overflowY: "auto",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "4px 8px",
    marginBottom: 4,
  },
  logoImg: {
    height: 32,
    objectFit: "contain",
  },
  divider: {
    height: 1,
    background: "rgba(0,0,0,0.06)",
    margin: "12px 0",
  },
  portfolioBox: {
    background: "#f6f7f8",
    borderRadius: 12,
    padding: "12px 14px",
    cursor: "pointer",
    transition: "background 0.2s",
  },
  portfolioLabel: {
    fontSize: 11,
    color: "rgba(0,0,0,0.45)",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 4,
    fontWeight: 600,
  },
  portfolioValue: {
    fontSize: 20,
    fontWeight: 700,
    color: "#1a1a1a",
  },
  portfolioPnl: {
    fontSize: 13,
    fontWeight: 600,
    marginTop: 2,
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  navBtn: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 14px",
    border: "none",
    borderRadius: 10,
    background: "transparent",
    color: "rgba(0,0,0,0.55)",
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.2s",
    textAlign: "left",
    width: "100%",
    fontFamily: "inherit",
  },
  navBtnActive: {
    background: "rgba(255,221,45,0.15)",
    color: "#1a1a1a",
    fontWeight: 600,
  },
  navIconImg: {
    width: 22,
    height: 22,
    objectFit: "contain",
  },
  levelBox: {
    padding: "12px 14px",
    background: "#f6f7f8",
    borderRadius: 12,
    marginBottom: 8,
  },
  levelHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  levelIcon: { fontSize: 20 },
  levelName: {
    fontSize: 13,
    fontWeight: 600,
    color: "#1a1a1a",
  },
  xpBar: {
    height: 6,
    background: "rgba(0,0,0,0.06)",
    borderRadius: 3,
    overflow: "hidden",
    marginBottom: 4,
  },
  xpFill: {
    height: "100%",
    background: "linear-gradient(90deg, #ffdd2d, #ffa000)",
    borderRadius: 3,
    transition: "width 0.5s ease",
  },
  xpText: {
    fontSize: 11,
    color: "rgba(0,0,0,0.4)",
  },
  streakBox: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "10px 14px",
    background: "linear-gradient(135deg, rgba(255,152,0,0.1), rgba(255,87,34,0.06))",
    borderRadius: 12,
    marginTop: 4,
  },
  streakNum: {
    fontSize: 20,
    fontWeight: 800,
    color: "#ff9800",
  },
  streakLabel: {
    fontSize: 13,
    color: "rgba(0,0,0,0.45)",
  },
  userBox: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "8px 4px",
    marginBottom: 4,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: "50%",
    background: "#ffdd2d",
    color: "#1a1a1a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 16,
    flexShrink: 0,
  },
  userInfo: {
    overflow: "hidden",
  },
  userName: {
    fontSize: 13,
    fontWeight: 600,
    color: "#1a1a1a",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  userEmail: {
    fontSize: 11,
    color: "rgba(0,0,0,0.4)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  logoutBtn: {
    padding: "8px 14px",
    border: "1px solid rgba(0,0,0,0.08)",
    borderRadius: 8,
    background: "transparent",
    color: "rgba(0,0,0,0.45)",
    fontSize: 12,
    cursor: "pointer",
    fontFamily: "inherit",
    transition: "all 0.2s",
    width: "100%",
  },
}
