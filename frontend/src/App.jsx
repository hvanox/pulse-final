import { useState, useEffect } from "react"
import Sidebar from "./components/Sidebar"
import HomeScreen from "./screens/HomeScreen"
import PortfolioScreen from "./screens/PortfolioScreen"
import LearnScreen from "./screens/LearnScreen"
import LessonScreen from "./screens/LessonScreen"
import AchievementsScreen from "./screens/AchievementsScreen"
import SettingsScreen from "./screens/SettingsScreen"
import AuthScreen from "./screens/AuthScreen"
import OnboardingScreen from "./screens/OnboardingScreen"
import { setUserId, getOnboardingStatus, loginUser } from "./api"

export default function App() {
  const [screen, setScreen] = useState("home")
  const [tab, setTab] = useState("home")
  const [user, setUser] = useState(null)
  const [lessonId, setLessonId] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [needsOnboarding, setNeedsOnboarding] = useState(false)
  const [initializing, setInitializing] = useState(true)

  // On mount: verify saved session is still valid
  useEffect(() => {
    const savedName = localStorage.getItem("pulse_name")
    const savedEmail = localStorage.getItem("pulse_email")
    if (savedName && savedEmail) {
      // Verify user exists on backend by checking onboarding status
      setUserId(savedEmail)
      getOnboardingStatus()
        .then(status => {
          setUser(savedName)
          setNeedsOnboarding(!status.completed)
          setInitializing(false)
        })
        .catch(() => {
          // Backend unreachable or user doesn't exist — clear and show auth
          localStorage.removeItem("pulse_name")
          localStorage.removeItem("pulse_email")
          setInitializing(false)
        })
    } else {
      setInitializing(false)
    }
  }, [])

  const handleAuth = (name, isNewUser = false) => {
    setUser(name)
    if (isNewUser) {
      setNeedsOnboarding(true)
    } else {
      getOnboardingStatus()
        .then(status => setNeedsOnboarding(!status.completed))
        .catch(() => setNeedsOnboarding(false))
    }
  }

  const handleOnboardingComplete = () => {
    setNeedsOnboarding(false)
    setRefreshKey(k => k + 1)
    setScreen("home")
    setTab("home")
  }

  const handleLogout = () => {
    setUser(null)
    setNeedsOnboarding(false)
    localStorage.removeItem("pulse_name")
    localStorage.removeItem("pulse_email")
    setUserId("demo-user-1")
  }

  const handleNavigate = (id) => {
    setTab(id)
    setScreen(id)
  }

  const handleStartLesson = (id) => {
    setLessonId(id)
    setScreen("lesson")
  }

  const handleLessonComplete = () => {
    setRefreshKey(k => k + 1)
    setScreen("home")
    setTab("home")
  }

  const handleBack = () => {
    setScreen("home")
    setTab("home")
  }

  // Initial loading
  if (initializing) {
    return (
      <div style={s.center}>Загрузка...</div>
    )
  }

  // Step 1: Not logged in → Auth screen
  if (!user) {
    return (
      <div style={s.fullPage}>
        <AuthScreen onAuth={handleAuth} />
      </div>
    )
  }

  // Step 2: Logged in but needs onboarding → Test
  if (needsOnboarding) {
    return (
      <div style={s.fullPage}>
        <OnboardingScreen
          onComplete={handleOnboardingComplete}
          userName={user}
          onLogout={handleLogout}
        />
      </div>
    )
  }

  // Step 3: Main app
  return (
    <div style={s.layout}>
      <Sidebar
        active={tab}
        onNavigate={handleNavigate}
        userName={user}
        onLogout={handleLogout}
        refreshKey={refreshKey}
      />
      <main style={s.main}>
        {screen === "home" && (
          <HomeScreen
            key={refreshKey}
            onStartLesson={handleStartLesson}
            onNavigate={handleNavigate}
          />
        )}
        {screen === "portfolio" && <PortfolioScreen />}
        {screen === "learn" && <LearnScreen onStartLesson={handleStartLesson} />}
        {screen === "lesson" && (
          <LessonScreen
            lessonId={lessonId}
            onComplete={handleLessonComplete}
            onBack={handleBack}
          />
        )}
        {screen === "achievements" && <AchievementsScreen />}
        {screen === "settings" && <SettingsScreen />}
      </main>
    </div>
  )
}

const s = {
  fullPage: {
    minHeight: "100vh",
    background: "#0f1923",
    fontFamily: "Inter, sans-serif",
  },
  center: {
    minHeight: "100vh",
    background: "#0f1923",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "Inter, sans-serif",
    color: "rgba(255,255,255,0.5)",
  },
  layout: {
    display: "flex",
    minHeight: "100vh",
    background: "#0f1923",
    fontFamily: "Inter, sans-serif",
    color: "#e8eaed",
  },
  main: {
    flex: 1,
    marginLeft: 260,
    minHeight: "100vh",
    padding: "24px 32px",
    overflowY: "auto",
  },
}
