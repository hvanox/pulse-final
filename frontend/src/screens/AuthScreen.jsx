import { useState } from "react"
import { loginUser, registerUser, setUserId } from "../api"

export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login") // "login" | "register"
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
      onAuth(res.name)
    } else {
      if (!name.trim()) return setLoading(false) || setError("Введите имя")
      const res = await registerUser(email, name, password)
      setLoading(false)
      if (!res.ok) return setError(res.error)
      setUserId(res.email)
      localStorage.setItem("pulse_name", res.name)
      onAuth(res.name)
    }
  }

  return (
    <div style={s.page}>
      <div style={s.card} className="fade-in">
        <h2 style={s.title}>{mode === "login" ? "Вход" : "Регистрация"}</h2>

        <form onSubmit={handleSubmit} style={s.form}>
          {mode === "register" && (
            <input
              style={s.input}
              type="text"
              placeholder="Имя"
              value={name}
              onChange={e => setName(e.target.value)}
              required
            />
          )}
          <input
            style={s.input}
            type="email"
            placeholder="Почта"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <input
            style={s.input}
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          {error && <div style={s.error}>{error}</div>}

          <button style={s.btn} type="submit" disabled={loading}>
            {loading ? "..." : mode === "login" ? "Войти" : "Зарегистрироваться"}
          </button>
        </form>

        <button
          style={s.toggle}
          onClick={() => { setMode(m => m === "login" ? "register" : "login"); setError("") }}
        >
          {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
        </button>
      </div>
    </div>
  )
}

const s = {
  page:   { background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", minHeight: "calc(100vh - 56px)", padding: 16, fontFamily: "Inter, sans-serif" },
  card:   { background: "#fff", borderRadius: 16, padding: "36px 32px", maxWidth: 420, width: "100%", boxShadow: "0 1px 4px rgba(0,0,0,0.08)", border: "1px solid #ebebeb" },
  title:  { fontSize: 22, fontWeight: 700, color: "#1a1a1a", marginBottom: 24, textAlign: "center" },
  form:   { display: "flex", flexDirection: "column", gap: 12 },
  input:  { padding: "12px 14px", fontSize: 15, borderRadius: 10, border: "1px solid #ddd", outline: "none", fontFamily: "Inter, sans-serif" },
  error:  { padding: "10px 14px", borderRadius: 8, background: "#ffebee", color: "#c62828", fontSize: 13 },
  btn:    { width: "100%", padding: "14px 0", fontSize: 15, fontWeight: 600, borderRadius: 12, background: "#FFD600", color: "#1a1a1a", border: "none", cursor: "pointer", marginTop: 4 },
  toggle: { width: "100%", padding: "10px 0", fontSize: 13, color: "#888", background: "none", border: "none", cursor: "pointer", marginTop: 8 },
}
