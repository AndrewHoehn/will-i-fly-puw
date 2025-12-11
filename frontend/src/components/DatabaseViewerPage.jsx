import { useState, useEffect } from 'react'

export function DatabaseViewerPage() {
  const [dbData, setDbData] = useState(null)
  const [totalRecords, setTotalRecords] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const pageSize = 100

  useEffect(() => {
    // Fetch from admin database endpoint with pagination
    const offset = page * pageSize
    fetch(`/api/admin/database?limit=${pageSize}&offset=${offset}`)
      .then(res => res.json())
      .then(data => {
        setDbData(data.flights || [])
        setTotalRecords(data.total || 0)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load database:', err)
        setLoading(false)
      })
  }, [page])

  if (loading) {
    return (
      <div className="page-content">
        <h2>🔍 Database Viewer</h2>
        <p>Loading historical flight data...</p>
      </div>
    )
  }

  if (!dbData || dbData.length === 0) {
    return (
      <div className="page-content">
        <h2>🔍 Database Viewer</h2>
        <p>No historical data available.</p>
      </div>
    )
  }

  const totalPages = Math.ceil(totalRecords / pageSize)
  const startIdx = page * pageSize
  const endIdx = Math.min(startIdx + pageSize, totalRecords)

  return (
    <div className="page-content">
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ marginTop: 0, marginBottom: '8px' }}>🔍 Database Viewer (Easter Egg!)</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Raw historical flight database • {totalRecords.toLocaleString()} total records • Page {page + 1} of {totalPages}
        </p>
        <button
          onClick={() => window.location.hash = '#admin'}
          style={{
            marginTop: '8px',
            padding: '8px 16px',
            background: 'var(--primary)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.85rem'
          }}
        >
          ← Back to Admin Dashboard
        </button>
      </div>

      {/* Pagination Controls */}
      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
        <button
          onClick={() => setPage(Math.max(0, page - 1))}
          disabled={page === 0}
          style={{
            padding: '8px 16px',
            background: page === 0 ? 'var(--card-bg)' : 'var(--primary)',
            color: page === 0 ? 'var(--text-secondary)' : 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: page === 0 ? 'not-allowed' : 'pointer'
          }}
        >
          ← Previous
        </button>
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Showing {startIdx + 1}-{endIdx} of {totalRecords.toLocaleString()}
        </span>
        <button
          onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
          disabled={page === totalPages - 1}
          style={{
            padding: '8px 16px',
            background: page === totalPages - 1 ? 'var(--card-bg)' : 'var(--primary)',
            color: page === totalPages - 1 ? 'var(--text-secondary)' : 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: page === totalPages - 1 ? 'not-allowed' : 'pointer'
          }}
        >
          Next →
        </button>
      </div>

      {/* Database Table */}
      <div style={{ overflowX: 'auto', background: 'var(--card-bg)', borderRadius: '8px', padding: '16px' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.85rem',
          fontFamily: 'monospace'
        }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>Flight #</th>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>Date</th>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>Type</th>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>Route</th>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>Status</th>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>Risk Score</th>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>PUW Weather</th>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>Origin Weather</th>
              <th style={{ padding: '8px', color: 'var(--primary)' }}>Dest Weather</th>
            </tr>
          </thead>
          <tbody>
            {dbData.map((flight, idx) => {
              const puwWeather = flight.multi_airport_weather?.KPUW
              const originWeather = flight.multi_airport_weather?.[flight.origin_airport]
              const destWeather = flight.multi_airport_weather?.[flight.dest_airport]

              const formatWeather = (w) => {
                if (!w || w.visibility_miles === null) return '—'
                return `${w.visibility_miles?.toFixed(1)}mi, ${Math.round(w.wind_speed_knots)}kn, ${Math.round(w.temperature_f)}°F`
              }

              const flightType = flight.origin_airport === 'KPUW' ? 'departure' : 'arrival'

              return (
                <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '8px', color: 'var(--text-primary)' }}>{flight.flight_number}</td>
                  <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>
                    {new Date(flight.flight_date).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '8px' }}>
                    <span style={{
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      background: flightType === 'arrival' ? '#3b82f620' : '#f9731620',
                      color: flightType === 'arrival' ? '#3b82f6' : '#f97316'
                    }}>
                      {flightType}
                    </span>
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>
                    {flight.origin_airport?.replace('K', '')} → {flight.dest_airport?.replace('K', '')}
                  </td>
                  <td style={{ padding: '8px' }}>
                    <span style={{
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      background: flight.is_cancelled ? '#ef444420' : '#22c55e20',
                      color: flight.is_cancelled ? '#ef4444' : '#22c55e'
                    }}>
                      {flight.is_cancelled ? 'Cancelled' : 'Completed'}
                    </span>
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-primary)' }}>
                    —
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {formatWeather(puwWeather)}
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {formatWeather(originWeather)}
                  </td>
                  <td style={{ padding: '8px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {formatWeather(destWeather)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Export Button */}
      <div style={{ marginTop: '20px' }}>
        <button
          onClick={async () => {
            // Download all data in chunks
            let allFlights = []
            let offset = 0
            const limit = 1000

            while (true) {
              const response = await fetch(`/api/admin/database?limit=${limit}&offset=${offset}`)
              const data = await response.json()
              allFlights = allFlights.concat(data.flights)
              if (data.flights.length < limit) break
              offset += limit
            }

            const json = JSON.stringify(allFlights, null, 2)
            const blob = new Blob([json], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `kpuw-flight-database-${new Date().toISOString().split('T')[0]}.json`
            a.click()
            URL.revokeObjectURL(url)
          }}
          style={{
            padding: '10px 20px',
            background: 'var(--primary)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.9rem'
          }}
        >
          📥 Export Full Database as JSON ({totalRecords.toLocaleString()} records)
        </button>
      </div>
    </div>
  )
}
