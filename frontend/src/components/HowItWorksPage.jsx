const formatDate = (dateStr) => {
  if (!dateStr) return '...'
  try {
    // Handle "2025-12-04 13:45Z" or "2025-06-06"
    const date = new Date(dateStr.replace("Z", ""))
    return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
  } catch (e) {
    return dateStr
  }
}

export function HowItWorksPage({ historyRange }) {
  return (
    <div className="page-content">
      <h2 style={{ marginTop: 0, marginBottom: '12px', fontSize: '1.5rem' }}>How Our Predictions Work</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: '1.6' }}>
        This is a straightforward pattern-matching system that combines weather data with historical outcomes. <strong>It's not fancy machine learning</strong> - just a simple approach to help you understand flight risk at Pullman-Moscow Regional Airport.
      </p>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.6', fontSize: '0.9rem' }}>
        <em>Important: These are probability estimates, not guarantees. Always check official airline status before your flight.</em>
      </p>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">The Three-Part Calculation</div>
        <div className="card-body">
          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
              1. Seasonal Baseline (from BTS data)
            </h4>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              We start with the historical average cancellation rate for that month. For example, January typically has a ~5% baseline, while July is closer to 0.5%. This comes from 5 years of <a href="https://www.transtats.bts.gov/ot_delay/OT_DelayCause1.asp?20=E" target="_blank" rel="noreferrer" style={{ color: '#3b82f6' }}>Bureau of Transportation Statistics</a> data showing actual PUW flight outcomes.
            </p>
            <div style={{ padding: '12px', background: 'rgba(100, 116, 139, 0.1)', borderRadius: '6px', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              baseline_score = historical_cancellation_rate[month]
            </div>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
              2. Current Weather Conditions
            </h4>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              We add risk points based on real-time weather at flight time. The main factors:
            </p>
            <ul style={{ margin: '0 0 12px 0', paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.8' }}>
              <li><strong>Visibility</strong>: Critical if &lt;0.5mi (+40 points), Low if &lt;1mi (+25 points), Reduced if &lt;3mi (+10 points)</li>
              <li><strong>Crosswinds</strong>: Calculated for runway 05/23 using wind direction and speed. Strong crosswinds (+15-25 points) make landing difficult for smaller regional jets</li>
              <li><strong>Temperature + Precipitation</strong>: Freezing temps with precipitation (+15 points) create icing conditions</li>
              <li><strong>High winds</strong>: Overall wind speed &gt;25 knots adds risk even without crosswind component</li>
            </ul>
            <div style={{ padding: '12px', background: 'rgba(100, 116, 139, 0.1)', borderRadius: '6px', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              weather_score = visibility_penalty + crosswind_penalty +<br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;icing_penalty + wind_penalty
            </div>
          </div>

          <div style={{ marginBottom: '0' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
              3. Historical Pattern Matching
            </h4>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              We query our database of {historyRange?.total_flights || '1,300+'} past flights to find similar conditions (same visibility range, similar winds, same temperature conditions). If we find 20+ matching flights, we use their actual cancellation rate as an adjustment factor. This is the most valuable part - real outcomes under real conditions at PUW.
            </p>
            <div style={{ padding: '12px', background: 'rgba(100, 116, 139, 0.1)', borderRadius: '6px', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              historical_adjustment =<br />
              &nbsp;&nbsp;actual_cancellation_rate(similar_conditions) - baseline
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">Final Score & Risk Levels</div>
        <div className="card-body">
          <div style={{ padding: '12px', background: 'rgba(100, 116, 139, 0.1)', borderRadius: '6px', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            final_score = min(baseline + weather_score + historical_adjustment, 99)
          </div>
          <p style={{ margin: '0 0 16px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
            The final score is capped at 99% because nothing is certain. We then translate this into plain language:
          </p>
          <div style={{ marginBottom: '16px' }}>
            <span className="chance-badge low">0-40% ✓ Likely to Fly</span>
            <p className="text-secondary" style={{ marginTop: '8px', marginBottom: 0, fontSize: '0.9rem' }}>
              Weather conditions are favorable. Most flights in this range operate normally.
            </p>
          </div>
          <div style={{ marginBottom: '16px' }}>
            <span className="chance-badge medium">40-70% ⚠ Watch Closely</span>
            <p className="text-secondary" style={{ marginTop: '8px', marginBottom: 0, fontSize: '0.9rem' }}>
              Conditions are borderline. Have a backup plan and monitor flight status closely.
            </p>
          </div>
          <div>
            <span className="chance-badge high">70-100% ✗ High Risk</span>
            <p className="text-secondary" style={{ marginTop: '8px', marginBottom: 0, fontSize: '0.9rem' }}>
              Adverse weather conditions. High probability of delays or cancellation - consider the Spokane option.
            </p>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">What We Track & What We Don't</div>
        <div className="card-body">
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#22c55e', fontSize: '0.95rem' }}>✓ What We Track</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.8' }}>
              <li>Real-time weather data from Open-Meteo API</li>
              <li>Flight schedules from AeroDataBox and AviationStack APIs</li>
              <li>Historical outcomes for {historyRange?.total_flights || '1,300+'} flights dating back to {historyRange?.start_date ? formatDate(historyRange.start_date) : 'mid-2024'}</li>
              <li>FAA status for connecting airports (Seattle, Boise)</li>
            </ul>
          </div>
          <div>
            <h4 style={{ margin: '0 0 8px 0', color: '#f97316', fontSize: '0.95rem' }}>✗ What We Don't Track</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.8' }}>
              <li>Mechanical issues or crew scheduling problems (these cause 37% of delays nationwide)</li>
              <li>Cascading delays from earlier flights in the day</li>
              <li>Airport equipment issues or runway conditions</li>
              <li>Unusual events (air traffic control issues, security delays, etc.)</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">How We Improve Over Time</div>
        <div className="card-body">
          <p style={{ margin: '0 0 12px 0', fontSize: '0.9rem', lineHeight: '1.6' }}>
            Every flight outcome helps us refine the predictions. When a flight completes or cancels, we record the actual outcome and compare it to our prediction. This builds up our historical database and helps identify which weather patterns most reliably predict issues at PUW.
          </p>
          <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
            The system started tracking in {historyRange?.start_date ? formatDate(historyRange.start_date) : 'mid-2024'} and has collected data for {historyRange?.days_covered || '180+'} days across {historyRange?.total_flights || '1,300+'} flights. As more data accumulates, the historical matching (part 3 above) becomes more accurate.
          </p>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem', fontStyle: 'italic' }}>
            The prediction accuracy varies by season and conditions. We're still learning what works best for the unique geography and weather patterns of the Palouse region.
          </p>
        </div>
      </div>
    </div>
  )
}
