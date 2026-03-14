import { useState } from "react"
import { loginUser, registerUser, setUserId } from "../api"

export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login")
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    if (mode === "login") {
      const res = await loginUser(email, password)
      setLoading(false)
      if (!res.ok) return setError(res.error)
      setUserId(res.email)
      localStorage.setItem("pulse_name", res.name)
      onAuth(res.name, false) // login → not new user
    } else {
      if (!name.trim()) return setLoading(false) || setError("Введите имя")
      const res = await registerUser(email, name, password)
      setLoading(false)
      if (!res.ok) return setError(res.error)
      setUserId(res.email)
      localStorage.setItem("pulse_name", res.name)
      onAuth(res.name, true) // register → new user → show onboarding
    }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        {/* Logo */}
        <div style={s.logo}>
          <span style={{ fontSize: 36 }}>💹</span>
          <span style={s.logoText}>PULSE</span>
          <span style={s.version}>2.0</span>
        </div>
        <div style={s.tagline}>Научись инвестировать, управляя виртуальным портфелем</div>

        <h2 style={s.title}>{mode === "login" ? "Вход" : "Регистрация"}</h2>

        <form onSubmit={handleSubmit} style={s.form}>
          {mode === "register" && (
            <input style={s.input} type="text" placeholder="Имя" value={name}
              onChange={e => setName(e.target.value)} required />
          )}
          <input style={s.input} type="email" placeholder="Почта" value={email}
            onChange={e => setEmail(e.target.value)} required />
          <input style={s.input} type="password" placeholder="Пароль" value={password}
            onChange={e => setPassword(e.target.value)} required />

          {error && <div style={s.error}>{error}</div>}

          <button style={s.btn} type="submit" disabled={loading}>
            {loading ? "..." : mode === "login" ? "Войти" : "Создать аккаунт"}
          </button>
        </form>

        <button style={s.toggle}
          onClick={() => { setMode(m => m === "login" ? "register" : "login"); setError("") }}>
          {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
        </button>

        {/* Features */}
        <div style={s.features}>
          {[
            { icon: "📈", text: "Виртуальный портфель" },
            { icon: "📚", text: "25 интерактивных уроков" },
            { icon: "🏆", text: "Достижения и уровни" },
          ].map((f, i) => (
            <div key={i} style={s.feature}>
              <span>{f.icon}</span>
              <span>{f.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const s = {
  page: {
    background: "#0f1923", display: "flex", alignItems: "center", justifyContent: "center",
    minHeight: "100vh", padding: 16, fontFamily: "Inter, sans-serif",
  },
  card: {
    background: "#1a2634", borderRadius: 20, padding: "40px 32px", maxWidth: 420, width: "100%",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  logo: {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 8,
  },
  logoText: { fontSize: 28, fontWeight: 800, color: "#fff", letterSpacing: 3 },
  version: {
    fontSize: 11, fontWeight: 700, color: "#FFD600",
    background: "rgba(255,214,0,0.15)", padding: "2px 6px", borderRadius: 6,
  },
  tagline: {
    fontSize: 13, color: "rgba(255,255,255,0.4)", textAlign: "center", marginBottom: 28,
  },
  title: {
    fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 20, textAlign: "center",
  },
  form: { display: "flex", flexDirection: "column", gap: 12 },
  input: {
    padding: "14px 16px", fontSize: 14, borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.1)", outline: "none",
    fontFamily: "Inter, sans-serif", background: "rgba(255,255,255,0.04)",
    color: "#e8eaed",
  },
  error: {
    padding: "10px 14px", borderRadius: 8, background: "rgba(239,83,80,0.15)",
    color: "#ef5350", fontSize: 13,
  },
  btn: {
    width: "100%", padding: "14px 0", fontSize: 15, fontWeight: 700,
    borderRadius: 12, background: "#FFD600", color: "#000", border: "none",
    cursor: "pointer", marginTop: 4, fontFamily: "inherit",
  },
  toggle: {
    width: "100%", padding: "10px 0", fontSize: 13, color: "rgba(255,255,255,0.4)",
    background: "none", border: "none", cursor: "pointer", marginTop: 12,
    fontFamily: "inherit",
  },
  features: {
    display: "flex", justifyContent: "center", gap: 20,
    marginTop: 28, paddingTop: 20, borderTop: "1px solid rgba(255,255,255,0.06)",
  },
  feature: {
    display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
    fontSize: 11, color: "rgba(255,255,255,0.4)", textAlign: "center",
  },
}
