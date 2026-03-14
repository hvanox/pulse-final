import { useState, useEffect } from "react"
import { getProgress } from "../api"

export default function ProfileScreen({ userName }) {
  const [progress, setProgress] = useState(null)

  useEffect(() => {
    getProgress().then(setProgress)
  }, [])

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.avatarBig}>
          {userName?.charAt(0)?.toUpperCase()}
        </div>
        <h2 style={s.name}>{userName}</h2>
        <p style={s.email}>{localStorage.getItem("pulse_email")}</p>

        {progress && (
          <div style={s.statsRow}>
            <div style={s.stat}>
              <div style={s.statValue}>🔥 {progress.streak}</div>
              <div style={s.statLabel}>дней подряд</div>
            </div>
            <div style={s.divider} />
            <div style={s.stat}>
              <div style={s.statValue}>✓ {progress.correct_total}</div>
              <div style={s.statLabel}>правильных</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const s = {
  page: {
    padding: "40px 24px",
    maxWidth: 480,
    margin: "0 auto",
    fontFamily: "Inter, sans-serif",
  },
  card: {
    background: "#fff",
    borderRadius: 20,
    padding: "40px 32px",
    border: "1px solid #e5e5e5",
    textAlign: "center",
    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
  },
  avatarBig: {
    width: 80,
    height: 80,
    borderRadius: "50%",
    background: "#FFD600",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 36,
    fontWeight: 700,
    color: "#1a1a1a",
    margin: "0 auto 16px",
  },
  name: {
    fontSize: 24,
    fontWeight: 700,
    color: "#1a1a1a",
    margin: "0 0 4px",
  },
  email: {
    fontSize: 14,
    color: "#888",
    margin: "0 0 28px",
  },
  statsRow: {
    display: "flex",
    alignItems: "center",
    background: "#fafafa",
    border: "1px solid #ebebeb",
    borderRadius: 16,
    padding: "20px",
    gap: 0,
  },
  stat: {
    flex: 1,
    textAlign: "center",
  },
  statValue: {
    fontSize: 24,
    fontWeight: 700,
    color: "#1a1a1a",
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 13,
    color: "#888",
  },
  divider: {
    width: 1,
    height: 40,
    background: "#e0e0e0",
  },
}
