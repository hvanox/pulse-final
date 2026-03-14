import { useState, useEffect } from "react"
import { getLessonCards, postInteraction, completeLesson } from "../api"

export default function QuizScreen({ lessonId, onComplete, onBack }) {
  const [cards, setCards] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [result, setResult] = useState(null)
  const [correctIndex, setCorrectIndex] = useState(null)
  const [finished, setFinished] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)

  useEffect(() => {
    getLessonCards(lessonId).then(data => {
      setCards(data)
      setLoading(false)
    })
  }, [lessonId])

  const card = cards[currentIndex]
  const total = cards.length
  const progress = total > 0 ? ((currentIndex + (result?.is_correct ? 1 : 0)) / total) * 100 : 0

  const handleSelect = (index) => {
    if (result) return
    setSelected(index)
  }

  const handleConfirm = async () => {
    if (selected === null) return

    if (correctIndex !== null) {
      const isCorrect = selected === correctIndex
      setResult({ is_correct: isCorrect, correct_index: correctIndex })
      if (isCorrect) setCorrectCount(c => c + 1)
      return
    }

    const res = await postInteraction(card.id, selected)
    if (res.correct_index !== null && res.correct_index !== undefined) {
      setCorrectIndex(res.correct_index)
    }
    setResult(res)
    if (res.is_correct) setCorrectCount(c => c + 1)
  }

  const handleRetry = () => {
    setSelected(null)
    setResult(null)
  }

  const handleNext = async () => {
    if (currentIndex + 1 < total) {
      setCurrentIndex(currentIndex + 1)
      setSelected(null)
      setResult(null)
      setCorrectIndex(null)
    } else {
      // All questions done
      await completeLesson(lessonId)
      setFinished(true)
    }
  }

  if (loading) {
    return (
      <div style={s.page}>
        <div style={s.loadingWrap}>
          <div style={s.spinner} />
          <p style={{ color: "#888", marginTop: 16 }}>Загрузка урока...</p>
        </div>
      </div>
    )
  }

  if (finished) {
    return (
      <div style={s.page}>
        <div style={s.finishCard} className="fade-in">
          <div style={s.finishEmoji}>🎉</div>
          <h2 style={s.finishTitle}>Урок пройден!</h2>
          <p style={s.finishSub}>
            Правильных ответов: {correctCount} из {total}
          </p>
          <div style={s.finishStars}>
            {[...Array(total)].map((_, i) => (
              <span key={i} style={{ fontSize: 36, opacity: i < correctCount ? 1 : 0.2 }}>
                ⭐
              </span>
            ))}
          </div>
          <button style={s.btn} onClick={onComplete}>
            Вернуться к карте →
          </button>
        </div>
      </div>
    )
  }

  const isWrong = result && !result.is_correct

  return (
    <div style={s.page}>
      {/* Progress bar */}
      <div style={s.topBar}>
        <button style={s.closeBtn} onClick={onBack}>✕</button>
        <div style={s.progressTrack}>
          <div style={{ ...s.progressFill, width: `${progress}%` }} />
        </div>
        <span style={s.counter}>{currentIndex + 1}/{total}</span>
      </div>

      <div style={s.card} className="fade-in" key={currentIndex}>
        {/* Question */}
        <div style={s.questionNum}>Вопрос {currentIndex + 1}</div>
        <p style={s.question}>{card.text}</p>

        {/* Options */}
        <div style={s.options}>
          {card.options.map((opt, i) => {
            const isSelected = selected === i
            const correct = result?.is_correct && isSelected
            const wrong = isSelected && isWrong

            let optStyle = { ...s.option }
            if (correct) {
              optStyle = { ...optStyle, background: "#e8f5e9", borderColor: "#4caf50" }
            } else if (wrong) {
              optStyle = { ...optStyle, background: "#ffebee", borderColor: "#e53935" }
            } else if (isSelected) {
              optStyle = { ...optStyle, background: "#e3f2fd", borderColor: "#1976d2" }
            }

            return (
              <div key={i}>
                <button
                  style={optStyle}
                  onClick={() => handleSelect(i)}
                  disabled={!!result}
                >
                  <div style={{
                    ...s.optionCircle,
                    borderColor: correct ? "#4caf50" : wrong ? "#e53935" : isSelected ? "#1976d2" : "#ccc",
                    background: correct ? "#4caf50" : wrong ? "#e53935" : "transparent",
                  }}>
                    {(correct || wrong) && (
                      <span style={{ color: "#fff", fontSize: 14, fontWeight: 700 }}>
                        {correct ? "✓" : "✕"}
                      </span>
                    )}
                    {isSelected && !result && (
                      <div style={s.optionDot} />
                    )}
                  </div>
                  <span style={s.optionText}>{opt}</span>
                </button>

                {isWrong && card.explanations?.[i] && (
                  <div
                    className="hint-animate"
                    style={{
                      ...s.hint,
                      background: wrong ? "#fff5f5" : "#fafafa",
                      borderColor: wrong ? "#ffcdd2" : "#ebebeb",
                    }}
                  >
                    {card.explanations[i]}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Actions */}
        {!result && selected !== null && (
          <button style={s.btn} onClick={handleConfirm}>Подтвердить</button>
        )}

        {isWrong && (
          <button style={s.btn} onClick={handleRetry}>Попробовать ещё раз</button>
        )}

        {result?.is_correct && (
          <div style={s.correctWrap}>
            <div style={s.correctBanner}>
              <span style={{ fontSize: 20 }}>✅</span>
              <span style={s.correctText}>Правильно!</span>
            </div>
            <button style={s.btn} onClick={handleNext}>
              {currentIndex + 1 < total ? "Следующий вопрос →" : "Завершить урок →"}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

const s = {
  page: {
    background: "#f8f9fa",
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "0 16px",
    fontFamily: "Inter, sans-serif",
  },
  topBar: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    width: "100%",
    maxWidth: 640,
    padding: "20px 0 24px",
  },
  closeBtn: {
    background: "none",
    border: "none",
    fontSize: 20,
    color: "#999",
    cursor: "pointer",
    padding: "4px 8px",
    fontFamily: "Inter, sans-serif",
  },
  progressTrack: {
    flex: 1,
    height: 12,
    background: "#e0e0e0",
    borderRadius: 6,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    background: "linear-gradient(90deg, #FFD600, #ff9800)",
    borderRadius: 6,
    transition: "width 0.5s ease",
  },
  counter: {
    fontSize: 14,
    fontWeight: 700,
    color: "#666",
    minWidth: 32,
    textAlign: "right",
  },
  loadingWrap: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "60vh",
  },
  spinner: {
    width: 40,
    height: 40,
    border: "4px solid #e0e0e0",
    borderTop: "4px solid #FFD600",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  card: {
    background: "#fff",
    borderRadius: 20,
    padding: "32px 28px",
    maxWidth: 640,
    width: "100%",
    boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
    border: "1px solid #ebebeb",
  },
  questionNum: {
    fontSize: 13,
    fontWeight: 600,
    color: "#999",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 8,
  },
  question: {
    fontSize: 20,
    fontWeight: 600,
    color: "#1a1a1a",
    lineHeight: 1.5,
    marginBottom: 24,
    marginTop: 0,
  },
  options: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    marginBottom: 20,
  },
  option: {
    display: "flex",
    alignItems: "center",
    gap: 14,
    padding: "14px 16px",
    border: "2px solid #e5e5e5",
    borderRadius: 14,
    background: "#fff",
    cursor: "pointer",
    width: "100%",
    textAlign: "left",
    fontFamily: "Inter, sans-serif",
    transition: "all 0.15s",
    fontSize: 15,
    boxSizing: "border-box",
  },
  optionCircle: {
    width: 24,
    height: 24,
    borderRadius: "50%",
    border: "2px solid #ccc",
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.15s",
  },
  optionDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    background: "#1976d2",
  },
  optionText: {
    fontSize: 15,
    color: "#1a1a1a",
    lineHeight: 1.4,
  },
  hint: {
    marginLeft: 38,
    marginBottom: 8,
    padding: "10px 14px",
    borderRadius: 10,
    border: "1px solid #ebebeb",
    fontSize: 13,
    color: "#555",
    lineHeight: 1.5,
  },
  correctWrap: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  correctBanner: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "14px 16px",
    background: "#e8f5e9",
    borderRadius: 12,
  },
  correctText: {
    fontSize: 16,
    fontWeight: 700,
    color: "#2e7d32",
  },
  btn: {
    width: "100%",
    padding: "14px 0",
    fontSize: 16,
    fontWeight: 700,
    borderRadius: 14,
    background: "#FFD600",
    color: "#1a1a1a",
    border: "none",
    cursor: "pointer",
    fontFamily: "Inter, sans-serif",
  },
  finishCard: {
    background: "#fff",
    borderRadius: 24,
    padding: "48px 32px",
    maxWidth: 480,
    width: "100%",
    textAlign: "center",
    boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    marginTop: 60,
  },
  finishEmoji: {
    fontSize: 64,
    marginBottom: 16,
  },
  finishTitle: {
    fontSize: 28,
    fontWeight: 800,
    color: "#1a1a1a",
    margin: "0 0 8px",
  },
  finishSub: {
    fontSize: 16,
    color: "#666",
    margin: "0 0 20px",
  },
  finishStars: {
    display: "flex",
    justifyContent: "center",
    gap: 8,
    marginBottom: 28,
  },
}
