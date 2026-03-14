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
import Tutorial from "./components/Tutorial"
import { setUserId, getOnboardingStatus, loginUser, clearAuth } from "./api"

export default function App() {
  const [screen, setScreen] = useState("home")
  const [tab, setTab] = useState("home")
  const [user, setUser] = useState(null)
  const [lessonId, setLessonId] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [needsOnboarding, setNeedsOnboarding] = useState(false)
  const [initializing, setInitializing] = useState(true)
  const [showTutorial, setShowTutorial] = useState(false)

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
    // Show tutorial for new users
    if (!localStorage.getItem("pulse_tutorial_done")) {
      setShowTutorial(true)
    }
  }

  const handleLogout = () => {
    setUser(null)
    setNeedsOnboarding(false)
    setShowTutorial(false)
    clearAuth()
    localStorage.removeItem("pulse_tutorial_done")
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
      {showTutorial && (
        <Tutorial
          userName={user}
          onComplete={() => setShowTutorial(false)}
        />
      )}
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
        {screen === "portfolio" && <PortfolioScreen onRefresh={() => setRefreshKey(k => k + 1)} />}
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
    background: "#f6f7f8",
    fontFamily: "Inter, sans-serif",
  },
  center: {
    minHeight: "100vh",
    background: "#f6f7f8",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "Inter, sans-serif",
    color: "rgba(0,0,0,0.45)",
  },
  layout: {
    display: "flex",
    minHeight: "100vh",
    background: "#f6f7f8",
    fontFamily: "Inter, sans-serif",
    color: "#1a1a1a",
  },
  main: {
    flex: 1,
    marginLeft: 260,
    minHeight: "100vh",
    padding: "24px 32px",
    overflowY: "auto",
  },
}
