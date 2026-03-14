import { useState } from "react"
import Sidebar from "./components/Sidebar"
import HomeScreen from "./screens/HomeScreen"
import QuizScreen from "./screens/QuizScreen"
import ProgressScreen from "./screens/ProgressScreen"
import ProfileScreen from "./screens/ProfileScreen"
import SettingsScreen from "./screens/SettingsScreen"
import AuthScreen from "./screens/AuthScreen"
import { setUserId } from "./api"

export default function App() {
  const [screen, setScreen] = useState("home")
  const [tab, setTab] = useState("home")
  const [currentLessonId, setCurrentLessonId] = useState(null)
  const [user, setUser] = useState(localStorage.getItem("pulse_name") || null)

  const handleAuth = (name) => {
    setUser(name)
    setScreen("home")
    setTab("home")
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem("pulse_name")
    localStorage.removeItem("pulse_email")
    setUserId("demo-user-1")
  }

  const handleSelectLesson = (lesson) => {
    setCurrentLessonId(lesson.id)
    setScreen("quiz")
  }

  const handleNavigate = (id) => {
    setTab(id)
    setScreen(id)
  }

  const handleBackToHome = () => {
    setScreen("home")
    setTab("home")
  }

  // Auth screen — no sidebar
  if (!user) {
    return (
      <div style={{ minHeight: "100vh", background: "#f8f9fa", fontFamily: "Inter, sans-serif" }}>
        <AuthScreen onAuth={handleAuth} />
      </div>
    )
  }

  // Main layout with sidebar
  return (
    <div style={s.layout}>
      <Sidebar
        active={tab}
        onNavigate={handleNavigate}
        userName={user}
        onLogout={handleLogout}
      />
      <main style={s.main}>
        {screen === "home" && (
          <HomeScreen onSelectLesson={handleSelectLesson} />
        )}
        {screen === "quiz" && (
          <QuizScreen
            lessonId={currentLessonId}
            onComplete={handleBackToHome}
            onBack={handleBackToHome}
          />
        )}
        {screen === "progress" && (
          <ProgressScreen onNext={handleBackToHome} />
        )}
        {screen === "profile" && (
          <ProfileScreen userName={user} />
        )}
        {screen === "settings" && (
          <SettingsScreen />
        )}
      </main>
    </div>
  )
}

const s = {
  layout: {
    display: "flex",
    minHeight: "100vh",
    background: "#f8f9fa",
    fontFamily: "Inter, sans-serif",
  },
  main: {
    flex: 1,
    marginLeft: 240,
    minHeight: "100vh",
  },
}
