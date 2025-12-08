import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:8000/api')

export function MonthlyStatsPage() {
  const [stats, setStats] = useState([])
  const [btsStats, setBtsStats] = useState([])
  const [delayBreakdown, setDelayBreakdown] = useState(null)
  const [dataRange, setDataRange] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('seasonal') // 'seasonal', 'tracker', or 'bts'

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch both datasets in parallel
        const [trackerResponse, btsResponse] = await Promise.all([
          axios.get(`${API_URL}/monthly-stats`),
          axios.get(`${API_URL}/bts-monthly-stats`)
        ])

        setStats(trackerResponse.data.monthly_stats || [])
        setBtsStats(btsResponse.data.bts_stats || [])
        setDelayBreakdown(btsResponse.data.overall_delay_breakdown || null)
        setDataRange(btsResponse.data.data_range || null)
      } catch (err) {
        console.error('Failed to fetch monthly stats:', err)
        setError('Failed to load monthly statistics')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="page-content">
        <h2>Monthly Statistics</h2>
        <div className="loading">Loading historical data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-content">
        <h2>Monthly Statistics</h2>
        <div className="error-message">{error}</div>
      </div>
    )
  }

  // Don't show "no data" message if we have BTS data but no tracker data yet
  // if (stats.length === 0) {
  //   return (
  //     <div className="page-content">
  //       <h2>Monthly Statistics</h2>
  //       <p style={{ color: 'var(--text-secondary)' }}>
  //         No historical data available yet. Statistics will appear as flight data is collected over time.
  //       </p>
  //     </div>
  //   )
  // }

  // Format month for display (e.g., "2024-12" -> "December 2024")
  const formatMonth = (monthStr) => {
    const [year, month] = monthStr.split('-')
    const date = new Date(year, month - 1)
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  }

  // Calculate seasonal averages from BTS data
  const calculateSeasonalAverages = (btsData) => {
    const seasonalData = {
      'January': [], 'February': [], 'March': [], 'April': [],
      'May': [], 'June': [], 'July': [], 'August': [],
      'September': [], 'October': [], 'November': [], 'December': []
    }

    btsData.forEach(stat => {
      const [year, month] = stat.month_str.split('-')
      const monthName = new Date(year, month - 1).toLocaleDateString('en-US', { month: 'long' })
      seasonalData[monthName].push(stat)
    })

    return Object.entries(seasonalData).map(([month, data]) => {
      if (data.length === 0) return { month, avgCancellationRate: 0, avgDelayRate: 0, totalFlights: 0, cancelled: 0, delayed: 0, years: 0 }

      const avgCancellationRate = data.reduce((sum, s) => sum + s.cancellation_rate, 0) / data.length
      const avgDelayRate = data.reduce((sum, s) => sum + s.delay_rate, 0) / data.length
      const totalFlights = data.reduce((sum, s) => sum + s.arr_flights, 0)
      const cancelled = data.reduce((sum, s) => sum + s.arr_cancelled, 0)
      const delayed = data.reduce((sum, s) => sum + s.arr_del15, 0)

      return {
        month,
        avgCancellationRate: avgCancellationRate.toFixed(1),
        avgDelayRate: avgDelayRate.toFixed(1),
        totalFlights: Math.round(totalFlights),
        cancelled: Math.round(cancelled),
        delayed: Math.round(delayed),
        years: data.length
      }
    })
  }

  const seasonalAverages = calculateSeasonalAverages(btsStats)

  return (
    <div className="page-content">
      <div style={{ marginBottom: '24px' }}>
        <h2>Historical Patterns & Seasonal Trends</h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.6' }}>
          Understanding historical patterns at Pullman-Moscow Regional Airport. This data helps provide context for predictions, but remember: <strong>most flights operate normally</strong>, especially outside winter months.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="tabs" style={{ display: 'flex', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border-default)', paddingBottom: '0' }}>
        <div
          className={`tab ${activeTab === 'seasonal' ? 'active' : ''}`}
          onClick={() => setActiveTab('seasonal')}
        >
          Seasonal Averages
        </div>
        <div
          className={`tab ${activeTab === 'tracker' ? 'active' : ''}`}
          onClick={() => setActiveTab('tracker')}
        >
          Tracker Database
        </div>
        <div
          className={`tab ${activeTab === 'bts' ? 'active' : ''}`}
          onClick={() => setActiveTab('bts')}
        >
          All BTS Data (2020-2025)
        </div>
      </div>

      {/* Seasonal Averages Tab */}
      {activeTab === 'seasonal' && (
        <>
          <div style={{ marginBottom: '20px', padding: '16px', background: 'rgba(34, 197, 94, 0.1)', borderRadius: '8px', border: '1px solid rgba(34, 197, 94, 0.3)' }}>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '1rem', color: '#22c55e', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>✓</span> <span>The Good News</span>
            </h3>
            <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
              Based on 5 years of BTS data, <strong>PUW flights are generally reliable</strong>. The overall average cancellation rate is around 2-3%. Most issues happen December-February due to winter weather conditions specific to the Palouse region.
            </p>
          </div>

          <div className="flight-table-container">
            <table className="flight-table monthly-stats-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Avg Cancellation Rate</th>
                  <th>Avg Delay Rate</th>
                  <th>Total Flights (5 yrs)</th>
                  <th>Season</th>
                </tr>
              </thead>
              <tbody>
                {seasonalAverages.map((stat) => {
                  const rate = parseFloat(stat.avgCancellationRate)
                  let rateClass = 'rate-low'
                  let season = '☀️ Low Risk'
                  if (rate > 5) {
                    rateClass = 'rate-high'
                    season = '❄️ Winter Risk'
                  } else if (rate > 2) {
                    rateClass = 'rate-medium'
                    season = '⚠️ Moderate'
                  }

                  return (
                    <tr key={stat.month} className="monthly-stat-row">
                      <td className="month-cell">
                        <strong>{stat.month}</strong>
                      </td>
                      <td className="rate-cell">
                        <span className={`rate-badge ${rateClass}`}>
                          {stat.avgCancellationRate}%
                        </span>
                      </td>
                      <td className="stat-detail">{stat.avgDelayRate}%</td>
                      <td className="stat-value">{stat.totalFlights}</td>
                      <td className="stat-detail" style={{ fontSize: '0.85rem' }}>
                        {season}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '24px', padding: '16px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid #334155' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: 'var(--text-primary)' }}>
              What This Means for Travelers
            </h3>
            <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.8' }}>
              <li><strong>Spring/Summer/Fall</strong> (Mar-Nov): Very reliable, cancellation rates typically under 1-2%</li>
              <li><strong>December-February</strong>: Higher cancellation rates (4-6%) due to winter weather - low visibility and crosswinds are the main culprits</li>
              <li><strong>The Spokane Option</strong>: If you're traveling in winter and flexibility matters, consider booking through Spokane (GEG) - it's a 90-minute drive and has more flight options</li>
              <li><strong>Most flights still go</strong>: Even in the worst winter months, 94-96% of flights operate normally</li>
              <li>Data averaged across {btsStats.length > 0 ? '5 years (2020-2025)' : 'multiple years'} of Bureau of Transportation Statistics records</li>
            </ul>
          </div>
        </>
      )}

      {/* Tracker Database Tab */}
      {activeTab === 'tracker' && (
        <>
          {stats.length === 0 ? (
            <div style={{ padding: '20px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid #334155', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
                No tracker data available yet. Statistics will appear as flight data is collected over time.
              </p>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: '20px', padding: '16px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                <h3 style={{ margin: '0 0 8px 0', fontSize: '1rem', color: '#3b82f6', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>📊</span> <span>Our Collected Flight Data</span>
                </h3>
                <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
                  This data comes from flights we've actively tracked and monitored since starting this project. It represents actual flight outcomes we've recorded in our database, helping improve prediction accuracy over time.
                </p>
              </div>

              <div className="flight-table-container">
                <table className="flight-table monthly-stats-table">
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th>Total Flights</th>
                      <th>Cancelled</th>
                      <th>Cancellation Rate</th>
                      <th>Avg Visibility</th>
                      <th>Avg Wind</th>
                      <th>Avg Temp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.filter(stat => stat.month).map((stat) => {
                      const rate = stat.cancellation_rate || 0
                      let rateClass = 'rate-low'
                      if (rate > 10) rateClass = 'rate-high'
                      else if (rate > 5) rateClass = 'rate-medium'

                      return (
                        <tr key={stat.month} className="monthly-stat-row">
                          <td className="month-cell">
                            <strong>{formatMonth(stat.month)}</strong>
                          </td>
                          <td className="stat-value">{stat.total_flights || 0}</td>
                          <td className="stat-value">{stat.cancelled || 0}</td>
                          <td className="rate-cell">
                            <span className={`rate-badge ${rateClass}`}>
                              {(stat.cancellation_rate || 0).toFixed(1)}%
                            </span>
                          </td>
                          <td className="stat-detail">{stat.avg_visibility ? `${stat.avg_visibility.toFixed(1)} mi` : 'N/A'}</td>
                          <td className="stat-detail">{stat.avg_wind ? `${stat.avg_wind.toFixed(0)} kt` : 'N/A'}</td>
                          <td className="stat-detail">{stat.avg_temp ? `${stat.avg_temp.toFixed(0)}°F` : 'N/A'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: '24px', padding: '16px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid #334155' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: 'var(--text-primary)' }}>
                  About This Tracker Data
                </h3>
                <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.8' }}>
                  <li>Based on {stats.reduce((sum, s) => sum + (s.total_flights || 0), 0)} flights actively tracked since {stats.length > 0 && stats[stats.length - 1].month ? formatMonth(stats[stats.length - 1].month) : 'launch'}</li>
                  <li>Data collected from real-time monitoring of PUW flights with weather conditions at departure/arrival times</li>
                  <li>Includes detailed weather metrics: visibility, wind speed, temperature, and precipitation</li>
                  <li>This data supplements the 5-year BTS historical data to improve prediction accuracy for current conditions</li>
                  <li>As more flights are tracked, pattern matching becomes more accurate for similar weather scenarios</li>
                </ul>
              </div>
            </>
          )}
        </>
      )}

      {/* BTS Data Tab */}
      {activeTab === 'bts' && (
        <>
          {/* Delay Cause Breakdown */}
          {delayBreakdown && (
            <div style={{ marginBottom: '24px', padding: '20px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid #334155' }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: 'var(--text-primary)' }}>
                Overall Delay Causes (2020-2025)
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                <div style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Carrier Issues</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ef4444' }}>{delayBreakdown.carrier}%</div>
                </div>
                <div style={{ padding: '12px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '6px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Weather</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#3b82f6' }}>{delayBreakdown.weather}%</div>
                </div>
                <div style={{ padding: '12px', background: 'rgba(249, 115, 22, 0.1)', borderRadius: '6px', border: '1px solid rgba(249, 115, 22, 0.3)' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>NAS (Air Traffic)</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f97316' }}>{delayBreakdown.nas}%</div>
                </div>
                <div style={{ padding: '12px', background: 'rgba(168, 85, 247, 0.1)', borderRadius: '6px', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Late Aircraft</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#a855f7' }}>{delayBreakdown.late_aircraft}%</div>
                </div>
              </div>
            </div>
          )}

          {/* BTS Monthly Stats Table */}
          <div className="flight-table-container">
            <table className="flight-table monthly-stats-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Total Flights</th>
                  <th>Cancelled</th>
                  <th>Cancellation Rate</th>
                  <th>Delayed (15+ min)</th>
                  <th>Delay Rate</th>
                </tr>
              </thead>
              <tbody>
                {btsStats.map((stat) => {
                  const rate = stat.cancellation_rate
                  let rateClass = 'rate-low'
                  if (rate > 10) rateClass = 'rate-high'
                  else if (rate > 5) rateClass = 'rate-medium'

                  return (
                    <tr key={stat.month_str} className="monthly-stat-row">
                      <td className="month-cell">
                        <strong>{formatMonth(stat.month_str)}</strong>
                      </td>
                      <td className="stat-value">{Math.round(stat.arr_flights)}</td>
                      <td className="stat-value">{Math.round(stat.arr_cancelled)}</td>
                      <td className="rate-cell">
                        <span className={`rate-badge ${rateClass}`}>
                          {stat.cancellation_rate}%
                        </span>
                      </td>
                      <td className="stat-value">{Math.round(stat.arr_del15)}</td>
                      <td className="stat-detail">{stat.delay_rate.toFixed(1)}%</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '24px', padding: '16px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid #334155' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: 'var(--text-primary)' }}>
              About BTS Historical Data for Pullman Airport
            </h3>
            <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
              <li>Official Bureau of Transportation Statistics (BTS) data for Pullman-Moscow Regional Airport (KPUW)</li>
              <li>Covers {dataRange ? `${dataRange.total_months} months` : 'historical period'} from {dataRange?.start} to {dataRange?.end}, providing long-term Pullman airport delay and cancellation trends</li>
              <li>Includes all Horizon Air (QX) flights operating at Moscow-Pullman Regional Airport</li>
              <li>Pullman airport delay causes: Carrier (airline mechanical/crew issues), Weather (visibility, wind, precipitation), NAS (air traffic control system), Late Aircraft (inbound flight delays)</li>
              <li>This historical data helps establish seasonal baselines for Pullman airport cancellation predictions</li>
              <li>Source: <a href="https://www.transtats.bts.gov/" target="_blank" rel="noreferrer" style={{ color: '#3b82f6' }}>transtats.bts.gov</a></li>
            </ul>
          </div>
        </>
      )}
    </div>
  )
}
