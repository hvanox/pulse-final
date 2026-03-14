import { useState } from "react"
import { registerUser, loginUser, setUserId } from "../api"

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
    try {
      if (mode === "login") {
        const res = await loginUser(email, password)
        setLoading(false)
        if (!res.ok) return setError(res.error || "Ошибка входа")
        setUserId(res.email)
        localStorage.setItem("pulse_name", res.name)
        onAuth(res.name, false)
      } else {
        if (!name.trim()) return setLoading(false) || setError("Введите имя")
        const res = await registerUser(email, name, password)
        setLoading(false)
        if (!res.ok) return setError(res.error || "Ошибка регистрации")
        setUserId(res.email)
        localStorage.setItem("pulse_name", res.name)
        onAuth(res.name, true)
      }
    } catch (err) {
      setLoading(false)
      const msg = err.message || ""
      if (msg.includes("user_already_exists")) setError("Пользователь уже существует")
      else if (msg.includes("invalid_credentials")) setError("Неверная почта или пароль")
      else setError(msg || "Произошла ошибка")
    }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        {/* Logo */}
        <div style={s.logo}>
          <img src="/icons/T-Bank_RU_logo.svg.png" alt="T-Bank" style={{ height: 36 }} />
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
    background: "#f6f7f8", display: "flex", alignItems: "center", justifyContent: "center",
    minHeight: "100vh", padding: 16, fontFamily: "Inter, sans-serif",
  },
  card: {
    background: "#ffffff", borderRadius: 20, padding: "40px 32px", maxWidth: 420, width: "100%",
    border: "1px solid rgba(0,0,0,0.08)", boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
  },
  logo: {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 8,
  },
  tagline: {
    fontSize: 13, color: "rgba(0,0,0,0.45)", textAlign: "center", marginBottom: 28,
  },
  title: {
    fontSize: 20, fontWeight: 700, color: "#1a1a1a", marginBottom: 20, textAlign: "center",
  },
  form: { display: "flex", flexDirection: "column", gap: 12 },
  input: {
    padding: "14px 16px", fontSize: 14, borderRadius: 12,
    border: "1px solid rgba(0,0,0,0.12)", outline: "none",
    fontFamily: "Inter, sans-serif", background: "#f6f7f8",
    color: "#1a1a1a",
  },
  error: {
    padding: "10px 14px", borderRadius: 8, background: "rgba(244,67,54,0.08)",
    color: "#f44336", fontSize: 13,
  },
  btn: {
    width: "100%", padding: "14px 0", fontSize: 15, fontWeight: 700,
    borderRadius: 12, background: "#ffdd2d", color: "#1a1a1a", border: "none",
    cursor: "pointer", marginTop: 4, fontFamily: "inherit",
  },
  toggle: {
    width: "100%", padding: "10px 0", fontSize: 13, color: "rgba(0,0,0,0.45)",
    background: "none", border: "none", cursor: "pointer", marginTop: 12,
    fontFamily: "inherit",
  },
  features: {
    display: "flex", justifyContent: "center", gap: 20,
    marginTop: 28, paddingTop: 20, borderTop: "1px solid rgba(0,0,0,0.06)",
  },
  feature: {
    display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
    fontSize: 11, color: "rgba(0,0,0,0.45)", textAlign: "center",
  },
}
