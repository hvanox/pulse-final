export default function SettingsScreen() {
  return (
    <div style={s.page}>
      <div style={s.title}>Настройки</div>

      <div style={s.card}>
        <div style={s.sectionTitle}>Уведомления</div>
        <label style={s.toggle}>
          <span>Напоминания о занятиях</span>
          <input type="checkbox" defaultChecked style={s.checkbox} />
        </label>
        <label style={s.toggle}>
          <span>Рыночные события</span>
          <input type="checkbox" defaultChecked style={s.checkbox} />
        </label>
        <label style={s.toggle}>
          <span>Еженедельный отчёт</span>
          <input type="checkbox" style={s.checkbox} />
        </label>
      </div>

      <div style={s.card}>
        <div style={s.sectionTitle}>Обучение</div>
        <label style={s.toggle}>
          <span>Показывать подсказки</span>
          <input type="checkbox" defaultChecked style={s.checkbox} />
        </label>
        <label style={s.toggle}>
          <span>Звуковые эффекты</span>
          <input type="checkbox" defaultChecked style={s.checkbox} />
        </label>
      </div>

      <div style={s.card}>
        <div style={s.sectionTitle}>Портфель</div>
        <label style={s.toggle}>
          <span>Уведомления об изменениях цен</span>
          <input type="checkbox" defaultChecked style={s.checkbox} />
        </label>
        <label style={s.toggle}>
          <span>Подсказки по ошибкам</span>
          <input type="checkbox" defaultChecked style={s.checkbox} />
        </label>
      </div>

      <div style={s.card}>
        <div style={s.sectionTitle}>О приложении</div>
        <div style={s.about}>Pulse — платформа для обучения инвестированию через интерактивные уроки и виртуальный портфель</div>
        <div style={s.version}>Версия 2.0.0</div>
      </div>
    </div>
  )
}

const s = {
  page: { maxWidth: 500, margin: "0 auto" },
  title: { fontSize: 28, fontWeight: 800, color: "#fff", marginBottom: 20 },
  card: {
    background: "#1a2634", borderRadius: 16, padding: "20px 24px",
    border: "1px solid rgba(255,255,255,0.06)", marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.4)",
    textTransform: "uppercase", letterSpacing: 1, marginBottom: 12,
  },
  toggle: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "10px 0", fontSize: 14, color: "#e8eaed", cursor: "pointer",
    borderBottom: "1px solid rgba(255,255,255,0.04)",
  },
  checkbox: { width: 18, height: 18, accentColor: "#FFD600", cursor: "pointer" },
  about: { fontSize: 13, color: "rgba(255,255,255,0.5)", marginBottom: 8, lineHeight: 1.5 },
  version: { fontSize: 12, color: "rgba(255,255,255,0.3)" },
}
