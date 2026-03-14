import { useState, useEffect } from "react"
import { getPortfolio, getStocks, trade, getTransactions } from "../api"

export default function PortfolioScreen({ onRefresh }) {
  const [portfolio, setPortfolio] = useState(null)
  const [stocks, setStocks] = useState([])
  const [transactions, setTransactions] = useState([])
  const [view, setView] = useState("portfolio") // portfolio | market | history
  const [selectedStock, setSelectedStock] = useState(null)
  const [tradeAction, setTradeAction] = useState("buy")
  const [tradeShares, setTradeShares] = useState(1)
  const [tradeMsg, setTradeMsg] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = () => {
    setLoading(true); setError(null)
    Promise.all([getPortfolio(), getStocks(), getTransactions()])
      .then(([p, s, t]) => { setPortfolio(p); setStocks(s); setTransactions(t); setLoading(false) })
      .catch(e => { setError(e.message||"Ошибка"); setLoading(false) })
  }

  useEffect(() => { refresh() }, [])

  const handleTrade = () => {
    if (!selectedStock || tradeShares < 1) return
    setTradeMsg(null)
    trade(selectedStock.ticker, tradeShares, tradeAction)
      .then(res => {
        if (res.ok) {
          const msg = tradeAction === "buy"
            ? `Куплено ${tradeShares} акций ${selectedStock.name} за ${res.total?.toLocaleString("ru-RU")} ₽`
            : `Продано ${tradeShares} акций ${selectedStock.name} за ${res.total?.toLocaleString("ru-RU")} ₽`
          setTradeMsg({ type: "success", text: msg }); setSelectedStock(null); setTradeShares(1); refresh(); onRefresh?.()
        } else { setTradeMsg({ type: "error", text: res.error }) }
      })
      .catch(e => setTradeMsg({ type: "error", text: e.message||"Ошибка сделки" }))
  }

  if (loading) return <div style={s.loading}>Загрузка...</div>
  if (error || !portfolio) return <div style={s.loading}><div style={{fontSize:48,marginBottom:16}}>⚠️</div><div style={{marginBottom:16}}>{error||"Ошибка"}</div><button onClick={refresh} style={{padding:"10px 24px",borderRadius:10,border:"1px solid rgba(0,0,0,0.1)",background:"transparent",color:"#ffdd2d",cursor:"pointer",fontFamily:"inherit"}}>Повторить</button></div>

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div>
          <div style={s.headerLabel}>СТОИМОСТЬ ПОРТФЕЛЯ</div>
          <div style={s.headerValue}>
            {portfolio.total_value.toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽
          </div>
          <div style={{
            ...s.headerPnl,
            color: portfolio.total_pnl >= 0 ? "#21a038" : "#f44336"
          }}>
            {portfolio.total_pnl >= 0 ? "+" : ""}{portfolio.total_pnl.toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽
            {" "}({portfolio.total_pnl_pct >= 0 ? "+" : ""}{portfolio.total_pnl_pct}%)
          </div>
        </div>
        <div style={s.balanceBox}>
          <div style={s.balanceLabel}>Свободные средства</div>
          <div style={s.balanceValue}>{portfolio.balance.toLocaleString("ru-RU")} ₽</div>
        </div>
      </div>

      {/* Sparkline */}
      {portfolio.sparkline?.length > 1 && (
        <div style={s.sparklineBox}>
          <Sparkline data={portfolio.sparkline} color={portfolio.total_pnl >= 0 ? "#21a038" : "#f44336"} />
        </div>
      )}

      {/* Tabs */}
      <div style={s.tabs}>
        {[
          { id: "portfolio", label: "Мои активы" },
          { id: "market", label: "Рынок" },
          { id: "history", label: "История" },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setView(t.id)}
            style={{ ...s.tab, ...(view === t.id ? s.tabActive : {}) }}
          >{t.label}</button>
        ))}
      </div>

      {/* Trade Message */}
      {tradeMsg && (
        <div style={{
          ...s.tradeMsg,
          background: tradeMsg.type === "success" ? "rgba(33,160,56,0.15)" : "rgba(244,67,54,0.15)",
          color: tradeMsg.type === "success" ? "#21a038" : "#f44336",
        }}>
          {tradeMsg.text}
          <button onClick={() => setTradeMsg(null)} style={s.closeMsgBtn}>✕</button>
        </div>
      )}

      {/* Portfolio View */}
      {view === "portfolio" && (
        <div>
          {/* Allocation bar */}
          <div style={s.allocBar}>
            {portfolio.allocations?.map((a, i) => (
              <div
                key={i}
                style={{
                  width: `${Math.max(a.pct, 2)}%`,
                  height: 8,
                  background: a.color,
                  borderRadius: i === 0 ? "4px 0 0 4px" : i === portfolio.allocations.length - 1 ? "0 4px 4px 0" : 0,
                }}
                title={`${a.name}: ${a.pct}%`}
              />
            ))}
          </div>
          <div style={s.allocLabels}>
            {portfolio.allocations?.filter(a => a.pct > 3).map((a, i) => (
              <span key={i} style={s.allocLabel}>
                <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: a.color, marginRight: 4 }} />
                {a.name} {a.pct}%
              </span>
            ))}
          </div>

          {/* Holdings list */}
          {portfolio.holdings?.length > 0 ? (
            <div style={s.holdingsList}>
              {portfolio.holdings.map(h => (
                <div key={h.ticker} style={s.holdingRow} onClick={() => {
                  setSelectedStock(stocks.find(s => s.ticker === h.ticker) || h)
                  setTradeAction("sell")
                }}>
                  <div style={{ ...s.holdingLogo, background: h.color }}>{h.logo_emoji}</div>
                  <div style={s.holdingInfo}>
                    <div style={s.holdingName}>{h.name_ru || h.name}</div>
                    <div style={s.holdingTicker}>{h.ticker} · {h.shares} шт · {h.sector}</div>
                  </div>
                  <div style={s.holdingRight}>
                    <div style={s.holdingValue}>{h.value.toLocaleString("ru-RU")} ₽</div>
                    <div style={{ ...s.holdingPnl, color: h.pnl >= 0 ? "#21a038" : "#f44336" }}>
                      {h.pnl >= 0 ? "+" : ""}{h.pnl.toLocaleString("ru-RU")} ₽ ({h.pnl_pct >= 0 ? "+" : ""}{h.pnl_pct}%)
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={s.emptyState}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>📭</div>
              <div>Портфель пуст. Перейди в «Рынок», чтобы купить акции!</div>
            </div>
          )}
        </div>
      )}

      {/* Market View */}
      {view === "market" && (
        <div style={s.stocksList}>
          {stocks.map(stock => (
            <div key={stock.ticker} style={s.stockRow} onClick={() => {
              setSelectedStock(stock)
              setTradeAction("buy")
              setTradeShares(1)
            }}>
              <div style={{ ...s.holdingLogo, background: stock.color }}>{stock.logo_emoji}</div>
              <div style={s.holdingInfo}>
                <div style={s.holdingName}>{stock.name_ru}</div>
                <div style={s.holdingTicker}>{stock.ticker} · {stock.sector}</div>
              </div>
              <div style={s.holdingRight}>
                <div style={s.holdingValue}>{stock.current_price?.toLocaleString("ru-RU")} ₽</div>
                <div style={{ ...s.holdingPnl, color: stock.change_pct >= 0 ? "#21a038" : "#f44336" }}>
                  {stock.change_pct >= 0 ? "+" : ""}{stock.change_pct}%
                </div>
              </div>
              {/* Mini sparkline */}
              {stock.sparkline?.length > 1 && (
                <div style={{ width: 60, height: 24, marginLeft: 8 }}>
                  <Sparkline data={stock.sparkline} color={stock.change_pct >= 0 ? "#21a038" : "#f44336"} height={24} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* History View */}
      {view === "history" && (
        <div style={s.historyList}>
          {transactions.length > 0 ? transactions.map((t, i) => (
            <div key={i} style={s.historyRow}>
              <div style={{ fontSize: 20 }}>{t.logo_emoji}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#1a1a1a" }}>
                  {t.action === "buy" ? "Покупка" : "Продажа"} {t.name}
                </div>
                <div style={{ fontSize: 11, color: "rgba(0,0,0,0.4)" }}>
                  {t.shares} шт × {t.price?.toLocaleString("ru-RU")} ₽
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{
                  fontSize: 14, fontWeight: 600,
                  color: t.action === "buy" ? "#f44336" : "#21a038",
                }}>
                  {t.action === "buy" ? "-" : "+"}{t.total?.toLocaleString("ru-RU")} ₽
                </div>
                <div style={{ fontSize: 11, color: "rgba(0,0,0,0.3)" }}>
                  {new Date(t.created_at).toLocaleDateString("ru-RU")}
                </div>
              </div>
            </div>
          )) : (
            <div style={s.emptyState}>Ещё нет сделок</div>
          )}
        </div>
      )}

      {/* Trade Modal */}
      {selectedStock && (
        <div style={s.modalOverlay} onClick={() => setSelectedStock(null)}>
          <div style={s.modal} onClick={e => e.stopPropagation()}>
            <div style={s.modalHeader}>
              <div style={{ ...s.holdingLogo, background: selectedStock.color, width: 44, height: 44, fontSize: 22 }}>
                {selectedStock.logo_emoji}
              </div>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#1a1a1a" }}>{selectedStock.name_ru || selectedStock.name}</div>
                <div style={{ fontSize: 13, color: "rgba(0,0,0,0.45)" }}>{selectedStock.ticker} · {selectedStock.sector}</div>
              </div>
              <button onClick={() => setSelectedStock(null)} style={s.modalClose}>✕</button>
            </div>

            <div style={s.modalPrice}>
              {(selectedStock.current_price || selectedStock.price)?.toLocaleString("ru-RU")} ₽
            </div>

            {selectedStock.pe && (
              <div style={s.modalMeta}>
                <span>P/E: {selectedStock.pe}</span>
                <span>Дивиденды: {selectedStock.dividend_yield}%</span>
              </div>
            )}

            {selectedStock.description && (
              <div style={s.modalDesc}>{selectedStock.description}</div>
            )}

            {/* Buy / Sell Toggle */}
            <div style={s.tradeToggle}>
              <button
                style={{ ...s.tradeToggleBtn, ...(tradeAction === "buy" ? s.tradeToggleBuy : {}) }}
                onClick={() => setTradeAction("buy")}
              >Купить</button>
              <button
                style={{ ...s.tradeToggleBtn, ...(tradeAction === "sell" ? s.tradeToggleSell : {}) }}
                onClick={() => setTradeAction("sell")}
              >Продать</button>
            </div>

            {/* Shares input */}
            <div style={s.sharesRow}>
              <button style={s.shareBtn} onClick={() => setTradeShares(Math.max(1, tradeShares - 1))}>−</button>
              <div style={s.sharesDisplay}>
                <div style={s.sharesNum}>{tradeShares}</div>
                <div style={s.sharesLabel}>акций</div>
              </div>
              <button style={s.shareBtn} onClick={() => setTradeShares(tradeShares + 1)}>+</button>
            </div>

            <div style={s.totalRow}>
              <span>Итого:</span>
              <span style={{ fontWeight: 700, color: "#1a1a1a" }}>
                {(tradeShares * (selectedStock.current_price || selectedStock.price)).toLocaleString("ru-RU")} ₽
              </span>
            </div>

            <button style={{
              ...s.tradeBtn,
              background: tradeAction === "buy" ? "#21a038" : "#f44336",
            }} onClick={handleTrade}>
              {tradeAction === "buy" ? "Купить" : "Продать"} {tradeShares} акций
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function Sparkline({ data, color = "#21a038", height = 40 }) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const w = 100
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  }).join(" ")
  return (
    <svg viewBox={`0 0 ${w} ${height}`} style={{ width: "100%", height }} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  )
}

const s = {
  page: { maxWidth: 900, margin: "0 auto" },
  loading: { color: "rgba(0,0,0,0.45)", padding: 40, textAlign: "center" },
  header: {
    display: "flex", justifyContent: "space-between", alignItems: "flex-start",
    marginBottom: 16,
  },
  headerLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", letterSpacing: 2, marginBottom: 6 },
  headerValue: { fontSize: 36, fontWeight: 800, color: "#1a1a1a", marginBottom: 4 },
  headerPnl: { fontSize: 16, fontWeight: 600 },
  balanceBox: { textAlign: "right" },
  balanceLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)", marginBottom: 4 },
  balanceValue: { fontSize: 18, fontWeight: 700, color: "#1a1a1a" },
  sparklineBox: {
    background: "#ffffff", borderRadius: 12, padding: "12px 16px",
    marginBottom: 16, border: "1px solid rgba(0,0,0,0.08)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  tabs: { display: "flex", gap: 4, marginBottom: 16 },
  tab: {
    padding: "8px 20px", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 8, background: "transparent", color: "rgba(0,0,0,0.45)",
    fontSize: 13, cursor: "pointer", fontFamily: "inherit", fontWeight: 500,
  },
  tabActive: { background: "rgba(255,221,45,0.1)", color: "#ffdd2d", borderColor: "rgba(255,221,45,0.2)" },
  tradeMsg: {
    padding: "12px 16px", borderRadius: 10, marginBottom: 16,
    fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "space-between",
  },
  closeMsgBtn: {
    background: "transparent", border: "none", color: "inherit",
    fontSize: 16, cursor: "pointer", padding: "0 4px",
  },
  allocBar: { display: "flex", borderRadius: 4, overflow: "hidden", marginBottom: 8 },
  allocLabels: { display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 16 },
  allocLabel: { fontSize: 11, color: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center" },
  holdingsList: { display: "flex", flexDirection: "column", gap: 2 },
  holdingRow: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "12px 16px", borderRadius: 12,
    background: "#ffffff", cursor: "pointer",
    border: "1px solid rgba(0,0,0,0.04)",
    transition: "background 0.2s",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  holdingLogo: {
    width: 36, height: 36, borderRadius: 10, display: "flex",
    alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0,
  },
  holdingInfo: { flex: 1, minWidth: 0 },
  holdingName: { fontSize: 14, fontWeight: 600, color: "#1a1a1a" },
  holdingTicker: { fontSize: 11, color: "rgba(0,0,0,0.4)" },
  holdingRight: { textAlign: "right" },
  holdingValue: { fontSize: 14, fontWeight: 600, color: "#1a1a1a" },
  holdingPnl: { fontSize: 12, fontWeight: 600 },
  stocksList: { display: "flex", flexDirection: "column", gap: 2 },
  stockRow: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "12px 16px", borderRadius: 12,
    background: "#ffffff", cursor: "pointer",
    border: "1px solid rgba(0,0,0,0.04)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  historyList: { display: "flex", flexDirection: "column", gap: 2 },
  historyRow: {
    display: "flex", alignItems: "center", gap: 12,
    padding: "12px 16px", borderRadius: 12,
    background: "#ffffff",
    border: "1px solid rgba(0,0,0,0.04)",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  emptyState: {
    textAlign: "center", padding: "40px 20px",
    color: "rgba(0,0,0,0.4)", fontSize: 14,
  },
  // Modal
  modalOverlay: {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200,
  },
  modal: {
    background: "#ffffff", borderRadius: 20, padding: "28px 24px",
    width: 400, maxWidth: "90vw", border: "1px solid rgba(0,0,0,0.06)",
    boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
  },
  modalHeader: { display: "flex", alignItems: "center", gap: 12, marginBottom: 16 },
  modalClose: {
    marginLeft: "auto", background: "transparent", border: "none",
    color: "rgba(0,0,0,0.4)", fontSize: 20, cursor: "pointer",
  },
  modalPrice: { fontSize: 28, fontWeight: 800, color: "#1a1a1a", marginBottom: 8, textAlign: "center" },
  modalMeta: {
    display: "flex", justifyContent: "center", gap: 20,
    fontSize: 12, color: "rgba(0,0,0,0.45)", marginBottom: 12,
  },
  modalDesc: { fontSize: 13, color: "rgba(0,0,0,0.45)", marginBottom: 16, lineHeight: 1.5, textAlign: "center" },
  tradeToggle: { display: "flex", gap: 4, marginBottom: 16 },
  tradeToggleBtn: {
    flex: 1, padding: "10px 0", border: "1px solid rgba(0,0,0,0.06)",
    borderRadius: 8, background: "transparent", color: "rgba(0,0,0,0.45)",
    fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
  },
  tradeToggleBuy: { background: "rgba(33,160,56,0.15)", color: "#21a038", borderColor: "rgba(33,160,56,0.3)" },
  tradeToggleSell: { background: "rgba(244,67,54,0.15)", color: "#f44336", borderColor: "rgba(244,67,54,0.3)" },
  sharesRow: { display: "flex", alignItems: "center", justifyContent: "center", gap: 20, marginBottom: 16 },
  shareBtn: {
    width: 40, height: 40, borderRadius: 10, border: "1px solid rgba(0,0,0,0.06)",
    background: "transparent", color: "#1a1a1a", fontSize: 20, cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  sharesDisplay: { textAlign: "center" },
  sharesNum: { fontSize: 28, fontWeight: 800, color: "#1a1a1a" },
  sharesLabel: { fontSize: 11, color: "rgba(0,0,0,0.4)" },
  totalRow: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "12px 0", borderTop: "1px solid rgba(0,0,0,0.08)",
    marginBottom: 16, fontSize: 14, color: "rgba(0,0,0,0.45)",
  },
  tradeBtn: {
    width: "100%", padding: "14px 0", border: "none", borderRadius: 12,
    color: "#fff", fontSize: 15, fontWeight: 700, cursor: "pointer", fontFamily: "inherit",
  },
}
