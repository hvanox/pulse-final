import { useState, useEffect } from "react"
import { getLessonDetail, completeLesson, trade } from "../api"

export default function LessonScreen({ lessonId, onComplete, onBack }) {
  const [lesson, setLesson] = useState(null)
  const [screenIdx, setScreenIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [revealed, setRevealed] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [totalQuiz, setTotalQuiz] = useState(0)
  const [completed, setCompleted] = useState(false)
  const [result, setResult] = useState(null)
  const [buyTicker, setBuyTicker] = useState(null)
  const [buyShares, setBuyShares] = useState(1)
  const [buyDone, setBuyDone] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getLessonDetail(lessonId)
      .then(l => { setLesson(l); setLoading(false) })
      .catch(() => setLoading(false))
  }, [lessonId])

  if (loading || !lesson) {
    return <div style={s.loading}>Загрузка урока...</div>
  }

  const screens = lesson.screens || []
  const screen = screens[screenIdx]
  const progress = ((screenIdx + 1) / screens.length) * 100
  const isLast = screenIdx === screens.length - 1

  const nextScreen = () => {
    if (isLast) {
      // Complete lesson
      completeLesson(lessonId, correctCount, totalQuiz).then(res => {
        setResult(res)
        setCompleted(true)
      })
      return
    }
    setScreenIdx(screenIdx + 1)
    setSelected(null)
    setRevealed(false)
    setBuyTicker(null)
    setBuyDone(false)
    setBuyShares(1)
  }

  const handleOptionSelect = (idx) => {
    if (revealed) return
    setSelected(idx)
  }

  const handleReveal = () => {
    setRevealed(true)
    if (screen.type === "quiz") {
      setTotalQuiz(t => t + 1)
      if (selected === screen.correct_index) {
        setCorrectCount(c => c + 1)
      }
    }
  }

  const handleBuy = () => {
    if (!buyTicker || buyShares < 1) return
    trade(buyTicker, buyShares, "buy").then(res => {
      if (res.ok) setBuyDone(true)
    })
  }

  // Completion screen
  if (completed) {
    return (
      <div style={s.page}>
        <div style={s.completionCard}>
          <div style={s.confetti}>🎉</div>
          <div style={s.completionTitle}>{lesson.title}</div>
          <div style={s.completionSubtitle}>Урок пройден!</div>
          <div style={s.completionStats}>
            <div style={s.completionStat}>
              <span style={s.completionStatIcon}>⚡</span>
              <span>+{result?.xp_earned || lesson.xp_reward} XP</span>
            </div>
            <div style={s.completionStat}>
              <span style={s.completionStatIcon}>🧠</span>
              <span>Навык: {lesson.skill}</span>
            </div>
            {result?.streak > 0 && (
              <div style={s.completionStat}>
                <span style={s.completionStatIcon}>🔥</span>
                <span>Серия: {result.streak} дней</span>
              </div>
            )}
            {totalQuiz > 0 && (
              <div style={s.completionStat}>
                <span style={s.completionStatIcon}>✅</span>
                <span>Правильных: {correctCount}/{totalQuiz}</span>
              </div>
            )}
          </div>
          <div style={s.completionActions}>
            <button style={s.primaryBtn} onClick={onComplete}>На главную</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={s.page}>
      {/* Top bar */}
      <div style={s.topBar}>
        <button style={s.backBtn} onClick={onBack}>← Назад</button>
        <div style={s.progressBar}>
          <div style={{ ...s.progressFill, width: `${progress}%` }} />
        </div>
        <span style={s.progressText}>{screenIdx + 1}/{screens.length}</span>
      </div>

      {/* Screen content */}
      <div style={s.screenCard} key={screenIdx}>
        {screen.type === "hook" && (
          <HookScreen screen={screen} onNext={nextScreen} />
        )}
        {screen.type === "visual" && (
          <VisualScreen screen={screen} onNext={nextScreen} />
        )}
        {screen.type === "decision" && (
          <DecisionScreen
            screen={screen}
            selected={selected}
            revealed={revealed}
            onSelect={handleOptionSelect}
            onReveal={handleReveal}
            onNext={nextScreen}
          />
        )}
        {screen.type === "consequences" && (
          <ConsequencesScreen screen={screen} onNext={nextScreen} />
        )}
        {screen.type === "insight" && (
          <InsightScreen screen={screen} onNext={nextScreen} />
        )}
        {screen.type === "practice" && (
          <PracticeScreen
            screen={screen}
            buyTicker={buyTicker}
            buyShares={buyShares}
            buyDone={buyDone}
            onSelectTicker={setBuyTicker}
            onSetShares={setBuyShares}
            onBuy={handleBuy}
            onNext={nextScreen}
          />
        )}
        {screen.type === "quiz" && (
          <QuizScreen
            screen={screen}
            selected={selected}
            revealed={revealed}
            onSelect={handleOptionSelect}
            onReveal={handleReveal}
            onNext={nextScreen}
          />
        )}
        {screen.type === "result" && (
          <ResultScreen
            screen={screen}
            lesson={lesson}
            correctCount={correctCount}
            totalQuiz={totalQuiz}
            onFinish={nextScreen}
          />
        )}
      </div>
    </div>
  )
}

// ─── Screen Components ───

function HookScreen({ screen, onNext }) {
  return (
    <div style={s.screenInner}>
      {screen.highlight && (
        <div style={s.highlight}>{screen.highlight}</div>
      )}
      <div style={s.hookTitle}>{screen.title}</div>
      <div style={s.hookText}>{screen.text}</div>
      <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
    </div>
  )
}

function VisualScreen({ screen, onNext }) {
  return (
    <div style={s.screenInner}>
      <div style={s.visualTitle}>{screen.title}</div>
      <div style={s.visualText}>{screen.text}</div>

      {/* Interactive placeholder — visual representation */}
      {screen.interactive === "inflation_calculator" && (
        <InflationCalc params={screen.params} />
      )}
      {screen.interactive === "compound_calculator" && (
        <CompoundCalc params={screen.params} />
      )}
      {screen.interactive === "risk_return_scale" && (
        <RiskReturnScale params={screen.params} />
      )}
      {screen.interactive === "pe_comparison" && (
        <PEComparison params={screen.params} />
      )}
      {screen.interactive === "dividend_calculator" && (
        <DividendCalc params={screen.params} />
      )}

      {/* Generic interactive card */}
      {!["inflation_calculator", "compound_calculator", "risk_return_scale", "pe_comparison", "dividend_calculator"].includes(screen.interactive) && screen.interactive && (
        <div style={s.interactiveBox}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📊</div>
          <div style={{ fontSize: 13, color: "rgba(0,0,0,0.45)" }}>Интерактивная визуализация</div>
        </div>
      )}

      {screen.params?.tabs && (
        <TabsVisual tabs={screen.params.tabs} />
      )}
      {screen.params?.factors && (
        <FactorsVisual factors={screen.params.factors} />
      )}
      {screen.params?.items && !screen.params?.tabs && !screen.params?.factors && (
        <ItemsVisual items={screen.params.items} />
      )}

      <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
    </div>
  )
}

function DecisionScreen({ screen, selected, revealed, onSelect, onReveal, onNext }) {
  const options = screen.options || []
  return (
    <div style={s.screenInner}>
      <div style={s.decisionTitle}>{screen.title}</div>
      <div style={s.decisionText}>{screen.text}</div>
      <div style={s.optionsList}>
        {options.map((opt, i) => (
          <div key={i}>
            <button
              onClick={() => onSelect(i)}
              style={{
                ...s.optionBtn,
                ...(selected === i ? s.optionSelected : {}),
                ...(revealed && selected === i ? (opt.is_better ? s.optionBetter : s.optionNeutral) : {}),
              }}
            >
              <span style={s.optionEmoji}>{opt.emoji || "•"}</span>
              <span style={s.optionText}>{opt.text}</span>
              {opt.detail && <div style={s.optionDetail}>{opt.detail}</div>}
            </button>
            {revealed && selected === i && opt.outcome && (
              <div style={s.outcomeBox}>{opt.outcome}</div>
            )}
          </div>
        ))}
      </div>
      {screen.note && revealed && (
        <div style={s.noteBox}>{screen.note}</div>
      )}
      {screen.reveal && revealed && (
        <div style={s.noteBox}>{screen.reveal}</div>
      )}
      {!revealed && selected !== null ? (
        <button style={s.primaryBtn} onClick={onReveal}>Подтвердить выбор</button>
      ) : revealed ? (
        <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
      ) : null}
    </div>
  )
}

function ConsequencesScreen({ screen, onNext }) {
  return (
    <div style={s.screenInner}>
      <div style={s.consequencesTitle}>{screen.title}</div>
      <div style={s.consequencesText}>{screen.text}</div>
      <div style={s.interactiveBox}>
        <div style={{ fontSize: 48 }}>📊</div>
      </div>
      <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
    </div>
  )
}

function InsightScreen({ screen, onNext }) {
  return (
    <div style={s.screenInner}>
      <div style={s.insightIcon}>{screen.icon || "💡"}</div>
      <div style={s.insightText}>{screen.text}</div>
      <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
    </div>
  )
}

function PracticeScreen({ screen, buyTicker, buyShares, buyDone, onSelectTicker, onSetShares, onBuy, onNext }) {
  const suggestions = screen.suggestions || ["AAPL", "SBER", "KO"]
  const stockData = {
    AAPL: { name: "Apple", price: 17500, emoji: "🍎" },
    SBER: { name: "Сбербанк", price: 290, emoji: "🏦" },
    KO: { name: "Coca-Cola", price: 6000, emoji: "🥤" },
    TSLA: { name: "Tesla", price: 25000, emoji: "⚡" },
    MSFT: { name: "Microsoft", price: 42000, emoji: "🪟" },
    GAZP: { name: "Газпром", price: 165, emoji: "🔥" },
    NVDA: { name: "Nvidia", price: 88000, emoji: "🎮" },
  }

  return (
    <div style={s.screenInner}>
      <div style={s.practiceTitle}>{screen.title}</div>
      <div style={s.practiceText}>{screen.text}</div>

      {buyDone ? (
        <div style={s.buySuccess}>
          <div style={{ fontSize: 48 }}>🎉</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#21a038", marginTop: 8 }}>Акция куплена!</div>
          <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
        </div>
      ) : (
        <>
          <div style={s.stockPicker}>
            {suggestions.map(ticker => {
              const st = stockData[ticker] || { name: ticker, price: 0, emoji: "📊" }
              return (
                <button
                  key={ticker}
                  onClick={() => onSelectTicker(ticker)}
                  style={{
                    ...s.stockPickBtn,
                    ...(buyTicker === ticker ? s.stockPickSelected : {}),
                  }}
                >
                  <span style={{ fontSize: 24 }}>{st.emoji}</span>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a" }}>{st.name}</div>
                  <div style={{ fontSize: 11, color: "rgba(0,0,0,0.4)" }}>{st.price?.toLocaleString("ru-RU")} ₽</div>
                </button>
              )
            })}
          </div>

          {buyTicker && (
            <div style={s.buyControls}>
              <div style={s.sharesRow}>
                <button style={s.shareBtn} onClick={() => onSetShares(Math.max(1, buyShares - 1))}>−</button>
                <div style={s.sharesDisplay}>
                  <div style={s.sharesNum}>{buyShares}</div>
                  <div style={s.sharesLabel}>акций</div>
                </div>
                <button style={s.shareBtn} onClick={() => onSetShares(buyShares + 1)}>+</button>
              </div>
              <div style={s.totalRow}>
                Итого: {(buyShares * (stockData[buyTicker]?.price || 0)).toLocaleString("ru-RU")} ₽
              </div>
              <button style={s.buyBtn} onClick={onBuy}>Купить 🛒</button>
            </div>
          )}

          {!buyTicker && (
            <button style={{ ...s.primaryBtn, opacity: 0.5 }} disabled>Выбери акцию</button>
          )}
        </>
      )}
    </div>
  )
}

function QuizScreen({ screen, selected, revealed, onSelect, onReveal, onNext }) {
  const options = screen.options || []
  const correct = screen.correct_index
  return (
    <div style={s.screenInner}>
      <div style={s.quizQuestion}>{screen.question}</div>
      <div style={s.optionsList}>
        {options.map((opt, i) => (
          <button
            key={i}
            onClick={() => onSelect(i)}
            disabled={revealed}
            style={{
              ...s.quizOption,
              ...(selected === i && !revealed ? s.quizOptionSelected : {}),
              ...(revealed && i === correct ? s.quizOptionCorrect : {}),
              ...(revealed && selected === i && i !== correct ? s.quizOptionWrong : {}),
            }}
          >
            <span style={s.quizDot}>
              {revealed ? (i === correct ? "✓" : selected === i ? "✗" : "") : String.fromCharCode(65 + i)}
            </span>
            <span>{opt}</span>
          </button>
        ))}
      </div>
      {revealed && screen.explanation && (
        <div style={s.explanationBox}>
          <span style={{ fontWeight: 700 }}>💡 </span>{screen.explanation}
        </div>
      )}
      {!revealed && selected !== null ? (
        <button style={s.primaryBtn} onClick={onReveal}>Проверить</button>
      ) : revealed ? (
        <button style={s.primaryBtn} onClick={onNext}>Далее →</button>
      ) : null}
    </div>
  )
}

function ResultScreen({ screen, lesson, correctCount, totalQuiz, onFinish }) {
  return (
    <div style={s.screenInner}>
      <div style={s.resultIcon}>🎉</div>
      <div style={s.resultTitle}>{screen.title || "Урок пройден!"}</div>
      <div style={s.resultStats}>
        <div style={s.resultStat}>✅ +{lesson.xp_reward} XP</div>
        <div style={s.resultStat}>🧠 Навык: {lesson.skill}</div>
        {totalQuiz > 0 && (
          <div style={s.resultStat}>📝 Правильных ответов: {correctCount}/{totalQuiz}</div>
        )}
      </div>
      <button style={s.primaryBtn} onClick={onFinish}>
        {screen.is_final ? "Завершить курс 🏆" : "Завершить урок"}
      </button>
    </div>
  )
}

// ─── Interactive Widgets ───

function InflationCalc({ params }) {
  const [rate, setRate] = useState(params?.rates?.[2] || 8)
  const initial = params?.initial || 100000
  const years = params?.years || 10
  const values = Array.from({ length: years + 1 }, (_, y) => Math.round(initial / Math.pow(1 + rate / 100, y)))
  return (
    <div style={s.widget}>
      <div style={s.widgetLabel}>Ставка инфляции: {rate}%</div>
      <input type="range" min={params?.rates?.[0] || 4} max={params?.rates?.[4] || 12}
        value={rate} onChange={e => setRate(+e.target.value)} style={s.slider} />
      <div style={s.widgetGrid}>
        {[0, 1, 3, 5, 10].filter(y => y <= years).map(y => (
          <div key={y} style={s.widgetItem}>
            <div style={s.widgetItemLabel}>{y === 0 ? "Сейчас" : `Через ${y} лет`}</div>
            <div style={{
              ...s.widgetItemValue,
              color: y === 0 ? "#21a038" : values[y] < initial * 0.7 ? "#f44336" : "#ffdd2d",
            }}>
              {values[y]?.toLocaleString("ru-RU")} ₽
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CompoundCalc({ params }) {
  const [rate, setRate] = useState(10)
  const monthly = params?.monthly || 10000
  const results = [10, 20, 30].map(years => {
    let total = 0
    for (let m = 0; m < years * 12; m++) {
      total = (total + monthly) * (1 + rate / 100 / 12)
    }
    return { years, total: Math.round(total), invested: monthly * years * 12 }
  })
  return (
    <div style={s.widget}>
      <div style={s.widgetLabel}>Доходность: {rate}% годовых</div>
      <input type="range" min={5} max={15} value={rate} onChange={e => setRate(+e.target.value)} style={s.slider} />
      <div style={s.widgetGrid}>
        {results.map(r => (
          <div key={r.years} style={s.widgetItem}>
            <div style={s.widgetItemLabel}>{r.years} лет</div>
            <div style={s.widgetItemValue}>{r.total.toLocaleString("ru-RU")} ₽</div>
            <div style={{ fontSize: 10, color: "rgba(0,0,0,0.3)" }}>
              вложено: {r.invested.toLocaleString("ru-RU")} ₽
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function RiskReturnScale({ params }) {
  const items = params?.items || []
  return (
    <div style={s.widget}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0" }}>
          <span style={{ fontSize: 20 }}>{item.emoji}</span>
          <span style={{ flex: 1, fontSize: 13, color: "#1a1a1a" }}>{item.name}</span>
          <div style={{ display: "flex", gap: 4 }}>
            {Array.from({ length: 5 }, (_, j) => (
              <div key={j} style={{
                width: 12, height: 12, borderRadius: 2,
                background: j < item.risk ? (item.risk >= 4 ? "#f44336" : item.risk >= 3 ? "#FFA000" : "#21a038") : "rgba(0,0,0,0.06)",
              }} />
            ))}
          </div>
          <span style={{ fontSize: 12, color: "#ffdd2d", width: 40, textAlign: "right" }}>~{item.return_pct}%</span>
        </div>
      ))}
    </div>
  )
}

function PEComparison({ params }) {
  const companies = params?.companies || []
  return (
    <div style={s.widget}>
      {companies.map((c, i) => (
        <div key={i} style={{ padding: "10px 0", borderBottom: i < companies.length - 1 ? "1px solid rgba(0,0,0,0.04)" : "none" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#1a1a1a" }}>{c.name}</span>
            <span style={{ fontSize: 14, fontWeight: 700, color: "#ffdd2d" }}>P/E {c.pe}</span>
          </div>
          <div style={{ fontSize: 12, color: "rgba(0,0,0,0.4)" }}>{c.comment}</div>
          <div style={{ marginTop: 4, height: 4, background: "rgba(0,0,0,0.08)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${Math.min(c.pe / 80 * 100, 100)}%`, background: c.pe > 40 ? "#f44336" : c.pe > 20 ? "#FFA000" : "#21a038", borderRadius: 2 }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function DividendCalc({ params }) {
  const stocks = params?.stocks || []
  const [amounts, setAmounts] = useState(stocks.reduce((acc, st) => ({ ...acc, [st.ticker]: 0 }), {}))
  const totalInvested = Object.values(amounts).reduce((s, v) => s + v, 0)
  const totalDividend = stocks.reduce((s, st) => s + (amounts[st.ticker] || 0) * st.yield / 100, 0)
  return (
    <div style={s.widget}>
      {stocks.map(st => (
        <div key={st.ticker} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0" }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a", width: 90 }}>{st.name}</span>
          <span style={{ fontSize: 11, color: "#21a038" }}>{st.yield}%</span>
          <input type="range" min={0} max={500000} step={10000}
            value={amounts[st.ticker] || 0}
            onChange={e => setAmounts(prev => ({ ...prev, [st.ticker]: +e.target.value }))}
            style={{ ...s.slider, flex: 1 }} />
          <span style={{ fontSize: 11, color: "rgba(0,0,0,0.4)", width: 60, textAlign: "right" }}>
            {(amounts[st.ticker] || 0).toLocaleString("ru-RU")}
          </span>
        </div>
      ))}
      <div style={{ marginTop: 12, padding: "12px", background: "rgba(255,221,45,0.1)", borderRadius: 8, textAlign: "center" }}>
        <div style={{ fontSize: 12, color: "rgba(0,0,0,0.45)" }}>Годовой дивидендный доход</div>
        <div style={{ fontSize: 24, fontWeight: 800, color: "#ffdd2d" }}>{Math.round(totalDividend).toLocaleString("ru-RU")} ₽/год</div>
        <div style={{ fontSize: 11, color: "rgba(0,0,0,0.3)" }}>{Math.round(totalDividend / 12).toLocaleString("ru-RU")} ₽/мес</div>
      </div>
    </div>
  )
}

function TabsVisual({ tabs }) {
  const [active, setActive] = useState(0)
  return (
    <div style={s.widget}>
      <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
        {tabs.map((t, i) => (
          <button key={i} onClick={() => setActive(i)} style={{
            flex: 1, padding: "8px", border: "1px solid rgba(0,0,0,0.06)", borderRadius: 6,
            background: active === i ? "rgba(255,221,45,0.1)" : "transparent",
            color: active === i ? "#ffdd2d" : "rgba(0,0,0,0.45)",
            fontSize: 12, cursor: "pointer", fontFamily: "inherit",
          }}>{t.icon}</button>
        ))}
      </div>
      <div style={{ textAlign: "center", padding: "12px", fontSize: 14, color: "#1a1a1a" }}>
        {tabs[active]?.title}
      </div>
    </div>
  )
}

function FactorsVisual({ factors }) {
  return (
    <div style={s.widget}>
      {factors.map((f, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0" }}>
          <span style={{ fontSize: 18 }}>{f.icon}</span>
          <span style={{ flex: 1, fontSize: 13, color: "#1a1a1a" }}>{f.name}</span>
          <span style={{
            fontSize: 10, padding: "2px 8px", borderRadius: 4, fontWeight: 700,
            background: f.impact === "high" ? "rgba(244,67,54,0.15)" : f.impact === "medium" ? "rgba(255,160,0,0.15)" : "rgba(33,160,56,0.15)",
            color: f.impact === "high" ? "#f44336" : f.impact === "medium" ? "#FFA000" : "#21a038",
          }}>
            {f.impact === "high" ? "Сильное" : f.impact === "medium" ? "Среднее" : "Слабое"}
          </span>
        </div>
      ))}
    </div>
  )
}

function ItemsVisual({ items }) {
  return (
    <div style={s.widget}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0" }}>
          <span style={{ fontSize: 18 }}>{item.emoji}</span>
          <span style={{ flex: 1, fontSize: 13, color: "#1a1a1a" }}>{item.name}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Styles ───

const s = {
  page: { maxWidth: 680, margin: "0 auto" },
  loading: { color: "rgba(0,0,0,0.45)", padding: 60, textAlign: "center", fontSize: 16 },
  topBar: { display: "flex", alignItems: "center", gap: 12, marginBottom: 24 },
  backBtn: {
    background: "transparent", border: "none", color: "rgba(0,0,0,0.45)",
    fontSize: 14, cursor: "pointer", fontFamily: "inherit", padding: "4px 0",
    flexShrink: 0,
  },
  progressBar: {
    flex: 1, height: 6, background: "rgba(0,0,0,0.06)", borderRadius: 3, overflow: "hidden",
  },
  progressFill: {
    height: "100%", background: "linear-gradient(90deg, #ffdd2d, #FFA000)",
    borderRadius: 3, transition: "width 0.4s ease",
  },
  progressText: { fontSize: 12, color: "rgba(0,0,0,0.3)", flexShrink: 0 },
  screenCard: {
    background: "#ffffff", borderRadius: 20, padding: "32px 28px",
    border: "1px solid rgba(0,0,0,0.08)",
    animation: "fadeIn 0.3s ease",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  screenInner: { display: "flex", flexDirection: "column", gap: 20 },
  // Hook
  highlight: {
    padding: "8px 16px", background: "rgba(255,221,45,0.1)", borderRadius: 8,
    color: "#ffdd2d", fontSize: 14, fontWeight: 700, textAlign: "center",
  },
  hookTitle: { fontSize: 24, fontWeight: 800, color: "#1a1a1a" },
  hookText: { fontSize: 16, color: "rgba(0,0,0,0.6)", lineHeight: 1.7, whiteSpace: "pre-line" },
  // Visual
  visualTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  visualText: { fontSize: 14, color: "rgba(0,0,0,0.55)", lineHeight: 1.6, whiteSpace: "pre-line" },
  interactiveBox: {
    padding: "32px 20px", background: "rgba(0,0,0,0.03)", borderRadius: 12,
    textAlign: "center", border: "1px dashed rgba(0,0,0,0.06)",
  },
  // Decision
  decisionTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  decisionText: { fontSize: 14, color: "rgba(0,0,0,0.55)", lineHeight: 1.6 },
  optionsList: { display: "flex", flexDirection: "column", gap: 8 },
  optionBtn: {
    width: "100%", padding: "14px 16px", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 12, background: "rgba(0,0,0,0.03)", color: "#1a1a1a",
    fontSize: 14, cursor: "pointer", textAlign: "left", fontFamily: "inherit",
    display: "flex", alignItems: "flex-start", gap: 12, transition: "all 0.2s",
  },
  optionSelected: { borderColor: "#ffdd2d", background: "rgba(255,221,45,0.08)" },
  optionBetter: { borderColor: "#21a038", background: "rgba(33,160,56,0.1)" },
  optionNeutral: { borderColor: "rgba(0,0,0,0.1)" },
  optionEmoji: { fontSize: 20, flexShrink: 0 },
  optionText: { fontSize: 14, lineHeight: 1.5 },
  optionDetail: { fontSize: 11, color: "rgba(0,0,0,0.4)", marginTop: 4 },
  outcomeBox: {
    padding: "12px 16px", background: "rgba(255,221,45,0.06)", borderRadius: 8,
    fontSize: 13, color: "rgba(0,0,0,0.55)", lineHeight: 1.5, marginTop: 4,
    borderLeft: "3px solid #ffdd2d",
  },
  noteBox: {
    padding: "12px 16px", background: "rgba(0,0,0,0.04)", borderRadius: 8,
    fontSize: 13, color: "rgba(0,0,0,0.55)", lineHeight: 1.5, fontStyle: "italic",
  },
  // Consequences
  consequencesTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  consequencesText: { fontSize: 14, color: "rgba(0,0,0,0.55)", lineHeight: 1.6 },
  // Insight
  insightIcon: { fontSize: 48, textAlign: "center" },
  insightText: {
    fontSize: 18, fontWeight: 600, color: "#1a1a1a", textAlign: "center",
    lineHeight: 1.7, whiteSpace: "pre-line",
  },
  // Practice
  practiceTitle: { fontSize: 20, fontWeight: 700, color: "#1a1a1a" },
  practiceText: { fontSize: 14, color: "rgba(0,0,0,0.55)", lineHeight: 1.6 },
  stockPicker: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 },
  stockPickBtn: {
    padding: "16px 8px", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 12, background: "rgba(0,0,0,0.03)",
    cursor: "pointer", textAlign: "center", fontFamily: "inherit",
    display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
    transition: "all 0.2s",
  },
  stockPickSelected: { borderColor: "#ffdd2d", background: "rgba(255,221,45,0.08)" },
  buyControls: { display: "flex", flexDirection: "column", gap: 12, alignItems: "center" },
  sharesRow: { display: "flex", alignItems: "center", gap: 20 },
  shareBtn: {
    width: 40, height: 40, borderRadius: 10, border: "1px solid rgba(0,0,0,0.06)",
    background: "transparent", color: "#1a1a1a", fontSize: 20, cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  sharesDisplay: { textAlign: "center" },
  sharesNum: { fontSize: 28, fontWeight: 800, color: "#1a1a1a" },
  sharesLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)" },
  totalRow: { fontSize: 14, color: "rgba(0,0,0,0.45)" },
  buyBtn: {
    padding: "12px 40px", border: "none", borderRadius: 10,
    background: "#21a038", color: "#fff", fontSize: 15, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit",
  },
  buySuccess: { textAlign: "center", padding: "20px 0" },
  // Quiz
  quizQuestion: { fontSize: 18, fontWeight: 700, color: "#1a1a1a", lineHeight: 1.5 },
  quizOption: {
    width: "100%", padding: "14px 16px", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 12, background: "rgba(0,0,0,0.03)", color: "#1a1a1a",
    fontSize: 14, cursor: "pointer", textAlign: "left", fontFamily: "inherit",
    display: "flex", alignItems: "center", gap: 12, transition: "all 0.2s",
  },
  quizOptionSelected: { borderColor: "#ffdd2d", background: "rgba(255,221,45,0.08)" },
  quizOptionCorrect: { borderColor: "#21a038", background: "rgba(33,160,56,0.1)" },
  quizOptionWrong: { borderColor: "#f44336", background: "rgba(244,67,54,0.1)" },
  quizDot: {
    width: 28, height: 28, borderRadius: "50%", background: "rgba(0,0,0,0.08)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 12, fontWeight: 700, flexShrink: 0,
  },
  explanationBox: {
    padding: "12px 16px", background: "rgba(33,160,56,0.08)", borderRadius: 10,
    fontSize: 13, color: "rgba(0,0,0,0.55)", lineHeight: 1.5,
    borderLeft: "3px solid #21a038",
  },
  // Result
  resultIcon: { fontSize: 64, textAlign: "center" },
  resultTitle: { fontSize: 24, fontWeight: 800, color: "#1a1a1a", textAlign: "center" },
  resultStats: { display: "flex", flexDirection: "column", gap: 8, alignItems: "center" },
  resultStat: { fontSize: 14, color: "rgba(0,0,0,0.55)" },
  // Completion
  completionCard: {
    background: "#ffffff", borderRadius: 20, padding: "48px 32px",
    textAlign: "center", border: "1px solid rgba(0,0,0,0.08)",
    maxWidth: 500, margin: "60px auto",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  confetti: { fontSize: 72, marginBottom: 16 },
  completionTitle: { fontSize: 24, fontWeight: 800, color: "#1a1a1a", marginBottom: 8 },
  completionSubtitle: { fontSize: 16, color: "rgba(0,0,0,0.45)", marginBottom: 24 },
  completionStats: { display: "flex", flexDirection: "column", gap: 12, marginBottom: 32 },
  completionStat: {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
    fontSize: 15, color: "#1a1a1a",
  },
  completionStatIcon: { fontSize: 20 },
  completionActions: { display: "flex", gap: 8, justifyContent: "center" },
  // Shared
  primaryBtn: {
    width: "100%", padding: "14px 0", border: "none", borderRadius: 12,
    background: "#ffdd2d", color: "#000", fontSize: 15, fontWeight: 700,
    cursor: "pointer", fontFamily: "inherit", transition: "all 0.2s",
  },
  // Widgets
  widget: {
    padding: "16px", background: "#f6f7f8", borderRadius: 12,
    border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  widgetLabel: { fontSize: 13, color: "rgba(0,0,0,0.45)", marginBottom: 8 },
  slider: { width: "100%", accentColor: "#ffdd2d" },
  widgetGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", gap: 8, marginTop: 12 },
  widgetItem: { textAlign: "center", padding: "8px" },
  widgetItemLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", marginBottom: 4 },
  widgetItemValue: { fontSize: 15, fontWeight: 700 },
}
