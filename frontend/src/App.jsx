import { useState } from "react"
import CardScreen from "./screens/CardScreen"
import FeedbackScreen from "./screens/FeedbackScreen"
import ProgressScreen from "./screens/ProgressScreen"

function TBankLogo() {
  return <img src="/image.png" alt="Т-Банк" style={{ height: 36 }} />
}

export default function App() {
  const [screen, setScreen] = useState("card")
  const [result, setResult] = useState(null)

  return (
    <div style={{ minHeight: "100vh", background: "#fff", fontFamily: "Inter, sans-serif" }}>
      {/* Header */}
      <header style={s.header}>
        <TBankLogo />
      </header>

      {/* Content */}
      {screen === "card" && (
        <CardScreen onDone={(r) => { setResult(r); setScreen("feedback") }} />
      )}
      {screen === "feedback" && (
        <FeedbackScreen result={result} onNext={() => setScreen("progress")} />
      )}
      {screen === "progress" && (
        <ProgressScreen onNext={() => setScreen("card")} />
      )}
    </div>
  )
}

const s = {
  header: {
    position: "sticky",
    top: 0,
    zIndex: 100,
    background: "#fff",
    borderBottom: "1px solid #ebebeb",
    padding: "0 32px",
    height: 56,
    display: "flex",
    alignItems: "center",
  },
}
