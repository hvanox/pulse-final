export default function SettingsScreen() {
  return (
    <div style={s.page}>
      <div style={s.card}>
        <h2 style={s.title}>Настройки</h2>

        <div style={s.section}>
          <div style={s.sectionTitle}>Уведомления</div>
          <label style={s.toggle}>
            <span>Напоминания о занятиях</span>
            <input type="checkbox" defaultChecked style={s.checkbox} />
          </label>
          <label style={s.toggle}>
            <span>Еженедельный отчёт</span>
            <input type="checkbox" style={s.checkbox} />
          </label>
        </div>

        <div style={s.section}>
          <div style={s.sectionTitle}>Обучение</div>
          <label style={s.toggle}>
            <span>Показывать подсказки</span>
            <input type="checkbox" defaultChecked style={s.checkbox} />
          </label>
        </div>

        <div style={s.section}>
          <div style={s.sectionTitle}>О приложении</div>
          <p style={s.about}>Pulse — приложение для изучения финансовой грамотности</p>
          <p style={s.version}>Версия 1.0.0</p>
        </div>
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
    padding: "32px",
    border: "1px solid #e5e5e5",
    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    color: "#1a1a1a",
    margin: "0 0 28px",
  },
  section: {
    marginBottom: 28,
    paddingBottom: 20,
    borderBottom: "1px solid #f0f0f0",
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: "#888",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 14,
  },
  toggle: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 0",
    fontSize: 15,
    color: "#333",
    cursor: "pointer",
  },
  checkbox: {
    width: 18,
    height: 18,
    accentColor: "#FFD600",
    cursor: "pointer",
  },
  about: {
    fontSize: 14,
    color: "#666",
    margin: "0 0 4px",
    lineHeight: 1.5,
  },
  version: {
    fontSize: 13,
    color: "#aaa",
    margin: 0,
  },
}
