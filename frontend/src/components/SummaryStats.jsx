export function SummaryStats({ stats }) {
  const { reliability_today, reliability_30_days, weather_risk_future } = stats

  // Reliability Color (Today)
  const cancelled = reliability_today.cancelled
  const relColor = cancelled > 0 ? 'var(--status-red)' : 'var(--status-green)'
  const relBg = cancelled > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)'

  // 30-Day Rate Color
  const rate = reliability_30_days.rate
  const rateColor = rate > 10 ? 'var(--status-red)' : (rate > 5 ? 'var(--status-orange)' : 'var(--status-green)')
  const rateBg = rate > 10 ? 'rgba(239, 68, 68, 0.1)' : (rate > 5 ? 'rgba(249, 115, 22, 0.1)' : 'rgba(34, 197, 94, 0.1)')

  // Risk Color
  const risks = weather_risk_future.at_risk
  const riskColor = risks > 0 ? 'var(--status-orange)' : 'var(--status-green)'
  const riskBg = risks > 0 ? 'rgba(249, 115, 22, 0.1)' : 'rgba(34, 197, 94, 0.1)'

  return (
    <div className="summary-stats">
      <div className="stat-card" style={{ borderColor: relColor, background: relBg }}>
        <div className="stat-title">Today</div>
        <div className="stat-value" style={{ color: relColor }}>
          {cancelled} / {reliability_today.total}
        </div>
        <div className="stat-desc">Cancelled</div>
      </div>

      <div className="stat-card" style={{ borderColor: rateColor, background: rateBg }}>
        <div className="stat-title">30-Day Rate</div>
        <div className="stat-value" style={{ color: rateColor }}>
          {rate.toFixed(1)}%
        </div>
        <div className="stat-desc">Cancellation Rate</div>
      </div>

      <div className="stat-card" style={{ borderColor: riskColor, background: riskBg }}>
        <div className="stat-title">Forecast Risk</div>
        <div className="stat-value" style={{ color: riskColor }}>
          {risks} / {weather_risk_future.total}
        </div>
        <div className="stat-desc">Flights at Risk</div>
      </div>
    </div>
  )
}
