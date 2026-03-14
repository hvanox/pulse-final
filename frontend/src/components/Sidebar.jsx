import { useState, useEffect } from "react"
import { getProgress } from "../api"

const TABS = [
  { id: "home", icon: "🏠", label: "Обучение" },
  { id: "progress", icon: "📊", label: "Прогресс" },
  { id: "profile", icon: "👤", label: "Профиль" },
  { id: "settings", icon: "⚙️", label: "Настройки" },
]

export default function Sidebar({ active, onNavigate, userName, onLogout }) {
  const [progress, setProgress] = useState(null)

  useEffect(() => {
    getProgress().then(setProgress)
  }, [active])

  return (
    <aside style={s.sidebar}>
      {/* Logo */}
      <div style={s.logo}>
        <img src="/image.png" alt="Pulse" style={{ height: 32 }} />
      </div>

      {/* Navigation */}
      <nav style={s.nav}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            style={{
              ...s.navBtn,
              ...(active === tab.id ? s.navBtnActive : {}),
            }}
            onClick={() => onNavigate(tab.id)}
          >
            <span style={s.navIcon}>{tab.icon}</span>
            <span style={s.navLabel}>{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* Streak widget */}
      {progress && (
        <div style={s.streakCard}>
          <div style={s.streakFire}>🔥</div>
          <div style={s.streakNum}>{progress.streak}</div>
          <div style={s.streakLabel}>
            {progress.streak === 1 ? "день подряд" : "дней подряд"}
          </div>
        </div>
      )}

      {/* User */}
      <div style={s.userSection}>
        <div style={s.avatar}>{userName?.charAt(0)?.toUpperCase()}</div>
        <div style={s.userInfo}>
          <div style={s.userName}>{userName}</div>
          <button style={s.logoutBtn} onClick={onLogout}>Выйти</button>
        </div>
      </div>
    </aside>
  )
}

const s = {
  sidebar: {
    width: 240,
    minHeight: "100vh",
    background: "#fff",
    borderRight: "1px solid #e5e5e5",
    display: "flex",
    flexDirection: "column",
    padding: "0",
    position: "fixed",
    left: 0,
    top: 0,
    bottom: 0,
    zIndex: 100,
    fontFamily: "Inter, sans-serif",
  },
  logo: {
    padding: "20px 24px 16px",
    borderBottom: "1px solid #f0f0f0",
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    padding: "16px 12px",
    flex: 1,
  },
  navBtn: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "12px 16px",
    border: "none",
    background: "none",
    borderRadius: 12,
    cursor: "pointer",
    fontSize: 15,
    fontWeight: 500,
    color: "#666",
    fontFamily: "Inter, sans-serif",
    transition: "all 0.15s",
    textAlign: "left",
  },
  navBtnActive: {
    background: "#f0f7ff",
    color: "#1a73e8",
    fontWeight: 700,
  },
  navIcon: {
    fontSize: 20,
    width: 28,
    textAlign: "center",
  },
  navLabel: {
    fontSize: 15,
  },
  streakCard: {
    margin: "0 16px 16px",
    padding: "16px",
    background: "linear-gradient(135deg, #fff8e1, #fff3e0)",
    borderRadius: 16,
    textAlign: "center",
    border: "1px solid #ffe0b2",
  },
  streakFire: {
    fontSize: 32,
    marginBottom: 4,
  },
  streakNum: {
    fontSize: 28,
    fontWeight: 800,
    color: "#e65100",
  },
  streakLabel: {
    fontSize: 12,
    color: "#bf360c",
    fontWeight: 500,
  },
  userSection: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "16px 20px",
    borderTop: "1px solid #f0f0f0",
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: "50%",
    background: "#FFD600",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 18,
    fontWeight: 700,
    color: "#1a1a1a",
    flexShrink: 0,
  },
  userInfo: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    overflow: "hidden",
  },
  userName: {
    fontSize: 14,
    fontWeight: 600,
    color: "#1a1a1a",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  logoutBtn: {
    background: "none",
    border: "none",
    padding: 0,
    fontSize: 12,
    color: "#999",
    cursor: "pointer",
    textAlign: "left",
    fontFamily: "Inter, sans-serif",
  },
}
