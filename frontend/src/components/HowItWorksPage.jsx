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
              2. Comprehensive Multi-Airport Weather Analysis
            </h4>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              We use a <strong>hybrid weather approach</strong>: <strong>NOAA Aviation Weather METAR</strong> for current conditions (actual observations from airport weather stations) and <strong>Open-Meteo</strong> for forecasts. This ensures current flights use real observed data (e.g., actual 1.5mi visibility) instead of model forecasts (which might show 24mi incorrectly).
            </p>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              We collect <strong>13 weather parameters</strong> from <strong>three airports</strong> (Pullman, Seattle, Boise). This captures conditions at your departure and arrival airports, not just PUW. For example, fog at Seattle can delay inbound flights even if Pullman weather is perfect.
            </p>
            <p style={{ margin: '0 0 8px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <strong>Complete Weather Data per Airport:</strong>
            </p>
            <ul style={{ margin: '0 0 12px 0', paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: '1.7' }}>
              <li>Visibility, Wind Speed, <strong>Wind Gusts</strong>, Wind Direction</li>
              <li>Temperature, Precipitation, Snow Depth</li>
              <li>Cloud Cover, Atmospheric Pressure, Humidity</li>
              <li>Weather Conditions (text description)</li>
            </ul>
            <p style={{ margin: '0 0 8px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <strong>Advanced Scoring (per airport):</strong>
            </p>
            <ul style={{ margin: '0 0 12px 0', paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.8' }}>
              <li><strong>Visibility</strong>: Critical &lt;0.5mi (+60 pts), Low &lt;1mi (+40 pts), Reduced &lt;3mi (+15 pts)</li>
              <li><strong>Crosswind Component</strong>: Calculated using <strong>wind gusts</strong> (prioritized) and runway headings. >25kn: +50 pts, >15kn: +30 pts</li>
              <li><strong>Snow Depth</strong>: >6" (+40 pts major contamination), >3" (+25 pts), >1" (+15 pts)</li>
              <li><strong>Active Precipitation</strong>: Freezing precip >0.3" (+30 pts), rain >0.5" (+15 pts)</li>
              <li><strong>Icing Risk</strong>: Temp &lt;32°F + Humidity >80% + Precipitation (+20 pts)</li>
              <li><strong>IFR Conditions</strong>: Cloud cover >90% + visibility &lt;5mi (+10 pts)</li>
            </ul>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <strong>Weather Weighting:</strong> PUW is always scored at 100%. For arrivals, origin weather is weighted at 70% (can't depart = no arrival). For departures, destination weather is weighted at 60% (can't land = no departure).
            </p>
            <div style={{ padding: '12px', background: 'rgba(100, 116, 139, 0.1)', borderRadius: '6px', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              puw_score = visibility + crosswind + snow_depth +<br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;precipitation + icing + ifr_conditions<br />
              <br />
              origin_score = (origin_weather_score × 0.7) // arrivals<br />
              dest_score = (dest_weather_score × 0.6)   // departures<br />
              <br />
              weather_score = puw_score + origin_score + dest_score
            </div>
          </div>

          <div style={{ marginBottom: '0' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
              3. Comprehensive Multi-Airport Historical Pattern Matching
            </h4>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              We query our database of {historyRange?.total_flights || '1,300+'} past flights to find similar <strong>comprehensive multi-airport weather patterns</strong>. This isn't just matching temperature - we're comparing wind gusts, snow depth, precipitation, and visibility at both PUW and the relevant origin/destination airport.
            </p>
            <p style={{ margin: '0 0 8px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <strong>Pattern Matching Criteria:</strong>
            </p>
            <ul style={{ margin: '0 0 12px 0', paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.8' }}>
              <li><strong>Wind Matching</strong>: Checks wind gusts (prioritized) OR sustained winds within ±5 knots</li>
              <li><strong>Snow Depth</strong>: Within ±2 inches (runway contamination similarity)</li>
              <li><strong>Precipitation</strong>: Within ±0.1 inches (active freezing precip events)</li>
              <li><strong>Visibility</strong>: Within ±0.5 miles (low-vis operations)</li>
              <li><strong>Multi-Airport Correlation</strong>: Matches conditions at PUW AND origin/destination simultaneously</li>
            </ul>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <strong>Dual Independent Signals:</strong> We look for ≥10 PUW matches and ≥5 origin/destination matches. These signals are averaged together and blended 50/50 with the weather-based score. This captures real outcomes like "What happened when both PUW and Seattle had snow on the ground?" or "When Boise had 25kn gusts AND PUW had low visibility, what was the cancellation rate?"
            </p>
            <p style={{ margin: '0 0 12px 0', color: 'var(--text-secondary)', fontSize: '0.85rem', fontStyle: 'italic', lineHeight: '1.6' }}>
              Historical weather was backfilled using Visual Crossing API ($0.23 total cost). Ongoing data collection uses the free Open-Meteo API.
            </p>
            <div style={{ padding: '12px', background: 'rgba(100, 116, 139, 0.1)', borderRadius: '6px', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              puw_historical = actual_rate(≥10 similar PUW conditions)<br />
              other_historical = actual_rate(≥5 similar origin/dest conditions)<br />
              <br />
              historical_avg = (puw_historical + other_historical) / 2<br />
              historical_adjustment = (historical_avg + current_score) / 2 - current_score
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
              <li>Real-time weather data from Open-Meteo API at <strong>three airports</strong> (PUW, SEA, BOI)</li>
              <li>10-day weather forecasts with hourly granularity for all three airports</li>
              <li>Flight schedules from AeroDataBox and AviationStack APIs</li>
              <li>Historical outcomes for {historyRange?.total_flights || '1,300+'} flights dating back to {historyRange?.start_date ? formatDate(historyRange.start_date) : 'mid-2024'}</li>
              <li>Multi-airport weather patterns stored with each historical flight</li>
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
