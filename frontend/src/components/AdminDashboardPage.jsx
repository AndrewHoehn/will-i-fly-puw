import { useState, useEffect } from 'react'
import { Database, Download, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'

export function AdminDashboardPage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/admin/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load admin stats:', err)
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const downloadDatabase = async () => {
    try {
      // Fetch all data in chunks
      let allFlights = []
      let offset = 0
      const limit = 1000

      while (true) {
        const response = await fetch(`/api/admin/database?limit=${limit}&offset=${offset}`)
        const data = await response.json()

        allFlights = allFlights.concat(data.flights)

        if (data.flights.length < limit) {
          break // No more data
        }

        offset += limit
      }

      // Create JSON file
      const json = JSON.stringify(allFlights, null, 2)
      const blob = new Blob([json], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kpuw-database-${new Date().toISOString().split('T')[0]}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to download database:', err)
      alert('Failed to download database: ' + err.message)
    }
  }

  if (loading) {
    return (
      <div className="page-content">
        <h2>⚙️ Admin Dashboard</h2>
        <p>Loading statistics...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-content">
        <h2>⚙️ Admin Dashboard</h2>
        <p style={{ color: 'var(--error)' }}>Error: {error}</p>
      </div>
    )
  }

  const dbStats = stats.database_stats
  const weatherStats = stats.weather_conditions

  return (
    <div className="page-content">
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ marginTop: 0, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={28} />
          Admin Dashboard
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Hidden admin panel • Database health & performance metrics
        </p>
      </div>

      {/* Quick Actions */}
      <div style={{ marginBottom: '24px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <button
          onClick={downloadDatabase}
          style={{
            padding: '12px 20px',
            background: 'var(--primary)',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontWeight: '500'
          }}
        >
          <Download size={18} />
          Download Full Database (JSON)
        </button>
        <button
          onClick={() => window.location.hash = '#database'}
          style={{
            padding: '12px 20px',
            background: 'var(--card-bg)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '0.95rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Database size={18} />
          View Database Table
        </button>
      </div>

      {/* Stats Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '16px',
        marginBottom: '24px'
      }}>
        {/* Total Flights */}
        <div style={{
          background: 'var(--card-bg)',
          padding: '20px',
          borderRadius: '12px',
          border: '1px solid var(--border-color)'
        }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Total Historical Flights
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--primary)' }}>
            {dbStats.total_flights.toLocaleString()}
          </div>
        </div>

        {/* Weather Completeness */}
        <div style={{
          background: 'var(--card-bg)',
          padding: '20px',
          borderRadius: '12px',
          border: '1px solid var(--border-color)'
        }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Multi-Airport Weather Completeness
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: dbStats.completion_percentage >= 90 ? '#22c55e' : '#f59e0b' }}>
              {dbStats.completion_percentage}%
            </div>
            {dbStats.completion_percentage >= 90 ? (
              <CheckCircle size={20} color="#22c55e" />
            ) : (
              <AlertCircle size={20} color="#f59e0b" />
            )}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {dbStats.complete_weather_data.toLocaleString()} complete, {dbStats.missing_weather_data.toLocaleString()} missing
          </div>
        </div>

        {/* Cancellation Rate */}
        <div style={{
          background: 'var(--card-bg)',
          padding: '20px',
          borderRadius: '12px',
          border: '1px solid var(--border-color)'
        }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Historical Cancellation Rate
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ef4444' }}>
            {dbStats.cancellation_rate}%
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {dbStats.cancelled_flights} cancelled, {dbStats.completed_flights} completed
          </div>
        </div>

        {/* Date Range */}
        <div style={{
          background: 'var(--card-bg)',
          padding: '20px',
          borderRadius: '12px',
          border: '1px solid var(--border-color)'
        }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Data Coverage
          </div>
          <div style={{ fontSize: '1rem', fontWeight: '500', color: 'var(--text-primary)' }}>
            {dbStats.date_range.earliest ? new Date(dbStats.date_range.earliest).toLocaleDateString() : 'N/A'}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>to</div>
          <div style={{ fontSize: '1rem', fontWeight: '500', color: 'var(--text-primary)' }}>
            {dbStats.date_range.latest ? new Date(dbStats.date_range.latest).toLocaleDateString() : 'N/A'}
          </div>
        </div>
      </div>

      {/* Weather Conditions Analysis */}
      <div style={{
        background: 'var(--card-bg)',
        padding: '24px',
        borderRadius: '12px',
        border: '1px solid var(--border-color)',
        marginBottom: '24px'
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <TrendingUp size={20} />
          Historical Weather Conditions (flights with multi-airport data)
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          {/* PUW Weather */}
          <div>
            <div style={{ fontWeight: '600', marginBottom: '8px', color: 'var(--primary)' }}>
              KPUW Weather
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Low visibility (&lt;1mi): <strong>{weatherStats.puw.low_visibility}</strong> flights
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              High winds (&gt;30kn): <strong>{weatherStats.puw.high_winds}</strong> flights
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Freezing temps (&lt;32°F): <strong>{weatherStats.puw.freezing_temps}</strong> flights
            </div>
          </div>

          {/* Origin Airports */}
          <div>
            <div style={{ fontWeight: '600', marginBottom: '8px', color: '#3b82f6' }}>
              Origin Airports (SEA/BOI)
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Low visibility (&lt;1mi): <strong>{weatherStats.origin_airports.low_visibility}</strong> flights
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              High winds (&gt;30kn): <strong>{weatherStats.origin_airports.high_winds}</strong> flights
            </div>
          </div>

          {/* Destination Airports */}
          <div>
            <div style={{ fontWeight: '600', marginBottom: '8px', color: '#f97316' }}>
              Destination Airports (SEA/BOI)
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Low visibility (&lt;1mi): <strong>{weatherStats.destination_airports.low_visibility}</strong> flights
            </div>
          </div>
        </div>
      </div>

      {/* Routes Breakdown */}
      <div style={{
        background: 'var(--card-bg)',
        padding: '24px',
        borderRadius: '12px',
        border: '1px solid var(--border-color)'
      }}>
        <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Flight Routes</h3>
        <div style={{ display: 'grid', gap: '8px' }}>
          {stats.routes.map((route, idx) => (
            <div
              key={idx}
              style={{
                padding: '12px',
                background: 'var(--bg)',
                borderRadius: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ fontFamily: 'monospace', fontSize: '0.95rem' }}>
                {route.origin || 'Unknown'} → {route.destination || 'Unknown'}
              </div>
              <div style={{ fontWeight: '600', color: 'var(--primary)' }}>
                {route.flights.toLocaleString()} flights
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Note */}
      <div style={{
        marginTop: '24px',
        padding: '16px',
        background: 'var(--card-bg)',
        borderRadius: '8px',
        fontSize: '0.85rem',
        color: 'var(--text-secondary)',
        borderLeft: '4px solid var(--primary)'
      }}>
        <strong>💡 Tip:</strong> If weather completeness is below 100%, run the backfill script:
        <code style={{
          display: 'block',
          marginTop: '8px',
          padding: '8px',
          background: 'var(--bg)',
          borderRadius: '4px',
          fontFamily: 'monospace',
          fontSize: '0.85rem'
        }}>
          python backend/backfill_historical_weather.py --skip-until "YYYY-MM-DD"
        </code>
      </div>
    </div>
  )
}
