import { useState, useEffect } from 'react'
import axios from 'axios'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plane,

  AlertTriangle,
  Wind,
  CloudRain,
  CloudSnow,
  Cloud,
  Clock,
  CheckCircle,
  XCircle,
  HelpCircle,
  ExternalLink,
  Map,
  Camera,
  Info
} from 'lucide-react'
import './App.css'
import { HowItWorksPage } from './components/HowItWorksPage'
import { ResourcesPage } from './components/ResourcesPage'
import { MonthlyStatsPage } from './components/MonthlyStatsPage'
import { formatWeatherPlain, formatAirportFull, formatChanceLevel } from './utils/helpers'

const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:8000/api')

function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [activeView, setActiveView] = useState('flights') // flights, how-it-works, resources
  const [flightTab, setFlightTab] = useState('future') // future, history (for flights view)
  const [filterDirection, setFilterDirection] = useState('all') // all, arrival, departure
  const [filterAirport, setFilterAirport] = useState('all') // all, SEA, BOI
  const [selectedRiskFlight, setSelectedRiskFlight] = useState(null)

  // Handle URL hash-based routing for deep linking
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1) // Remove #
      if (['flights', 'monthly-stats', 'how-it-works', 'resources'].includes(hash)) {
        setActiveView(hash)
      }
    }

    // Set initial view from URL
    handleHashChange()

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  // Update URL hash when activeView changes
  const navigateToView = (view) => {
    setActiveView(view)
    window.location.hash = view
  }

  // Update document title based on active view
  useEffect(() => {
    const titles = {
      'flights': 'Will I Fly PUW - Pullman Flight Tracker & Cancellation Predictions',
      'monthly-stats': 'Monthly Statistics - Pullman Airport Flight Delays & Cancellations',
      'how-it-works': 'How It Works - Pullman Airport Weather Prediction System',
      'resources': 'Resources - Pullman Moscow Regional Airport Flight Information'
    }
    document.title = titles[activeView] || titles['flights']
  }, [activeView])

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API_URL}/dashboard`)
      setData(res.data)
    } catch (err) {
      console.error("Failed to fetch data", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // Poll every minute
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="loading">Loading Flight Data...</div>

  // Filter Logic
  const getFilteredFlights = (flights) => {
    if (!flights) return []
    return flights.filter(f => {
      // Direction Filter
      if (filterDirection !== 'all') {
        if (filterDirection === 'arrival' && f.type !== 'arrival') return false
        if (filterDirection === 'departure' && f.type !== 'departure') return false
      }
      // Airport Filter
      if (filterAirport !== 'all') {
        const route = f.type === 'arrival' ? f.origin : f.destination
        // Check if route contains the filter string (e.g. SEA in KSEA)
        if (!route.includes(filterAirport)) return false
      }
      return true
    })
  }

  const displayedFlights = flightTab === 'future'
    ? getFilteredFlights(data?.future)
    : getFilteredFlights(data?.historical)

  // Format last updated timestamp
  const formatLastUpdated = (timestamp) => {
    if (!timestamp) return 'Never'
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} min ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hr ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
  }

  return (
    <div className="app-container">
      <header>
        <div className="header-left">
          <h1>
            <Plane /> Will I Fly PUW
          </h1>
        </div>

      </header>

      <div className="app-content">
        {/* Main Navigation Tabs */}
        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeView === 'flights' ? 'active' : ''}`}
            onClick={() => navigateToView('flights')}
          >
            Flights
          </button>
          <button
            className={`nav-tab ${activeView === 'monthly-stats' ? 'active' : ''}`}
            onClick={() => navigateToView('monthly-stats')}
          >
            Monthly Stats
          </button>
          <button
            className={`nav-tab ${activeView === 'how-it-works' ? 'active' : ''}`}
            onClick={() => navigateToView('how-it-works')}
          >
            How It Works
          </button>
          <button
            className={`nav-tab ${activeView === 'resources' ? 'active' : ''}`}
            onClick={() => navigateToView('resources')}
          >
            Resources
          </button>
        </nav>

        {/* Conditional View Rendering */}
        {activeView === 'how-it-works' ? (
          <HowItWorksPage historyRange={data?.history_range} />
        ) : activeView === 'resources' ? (
          <ResourcesPage />
        ) : activeView === 'monthly-stats' ? (
          <MonthlyStatsPage />
        ) : (
          <>
            {/* Flights View */}
            {/* Summary Stats & Weather */}
            <div className="stats-grid">
              {data?.stats && <SummaryStats stats={data.stats} />}
            </div>

            {data?.weather_forecast && (
              <div style={{ marginBottom: '16px' }}>
                <WeatherWidget forecast={data.weather_forecast} />
              </div>
            )}

            {/* FAA Status for Connection Airports */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '8px',
                fontSize: '0.85rem',
                color: 'var(--text-secondary)'
              }}>
                <Info size={14} />
                <span>FAA status for connecting airports (SEA, BOI) - updated every 30 minutes</span>
              </div>
              <div className="faa-ticker" style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                padding: '12px 16px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-md)'
              }}>
                <FAAStatus airport="SEA" status={data?.faa_status?.SEA} />
                <FAAStatus airport="BOI" status={data?.faa_status?.BOI} />
              </div>
            </div>

            {/* Filters */}
            <div className="filters">
              <div className="filter-group">
                <button
                  className={`filter-btn ${filterDirection === 'all' ? 'active' : ''}`}
                  onClick={() => setFilterDirection('all')}
                >All</button>
                <button
                  className={`filter-btn ${filterDirection === 'arrival' ? 'active' : ''}`}
                  onClick={() => setFilterDirection('arrival')}
                >Arrivals</button>
                <button
                  className={`filter-btn ${filterDirection === 'departure' ? 'active' : ''}`}
                  onClick={() => setFilterDirection('departure')}
                >Departures</button>
              </div>
              <div className="filter-divider" style={{ width: '1px', height: '24px', background: 'var(--border-default)' }}></div>
              <div className="filter-group">
                <button
                  className={`filter-btn ${filterAirport === 'all' ? 'active' : ''}`}
                  onClick={() => setFilterAirport('all')}
                >All Airports</button>
                <button
                  className={`filter-btn ${filterAirport === 'SEA' ? 'active' : ''}`}
                  onClick={() => setFilterAirport('SEA')}
                >Seattle</button>
                <button
                  className={`filter-btn ${filterAirport === 'BOI' ? 'active' : ''}`}
                  onClick={() => setFilterAirport('BOI')}
                >Boise</button>
              </div>
            </div>

            {/* Flight Data Freshness Info */}
            {data?.data_freshness && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-md)',
                marginBottom: '16px',
                fontSize: '0.9rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Clock size={16} style={{ color: 'var(--text-secondary)' }} />
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: '2px' }}>
                      Flight data last updated: {formatLastUpdated(data.last_updated)}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Weather data: {data.data_freshness.weather_data_age_minutes < 1 ? 'Just now' : `${data.data_freshness.weather_data_age_minutes}m ago`}
                    </div>
                  </div>
                </div>
                {data.data_freshness.is_stale && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: '#f97316',
                    fontSize: '0.85rem'
                  }}>
                    <AlertTriangle size={14} />
                    <span>Data may be stale</span>
                  </div>
                )}
              </div>
            )}

            {/* Flight Tabs (Upcoming vs History) */}
            <div className="tabs" style={{ display: 'flex', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border-default)', paddingBottom: '0' }}>
              <div
                className={`tab ${flightTab === 'future' ? 'active' : ''}`}
                onClick={() => setFlightTab('future')}
              >
                Upcoming Flights
              </div>
              <div
                className={`tab ${flightTab === 'historical' ? 'active' : ''}`}
                onClick={() => setFlightTab('historical')}
              >
                Recent History
              </div>
            </div>

            {/* Flight List */}
            <div className="flight-list">
              <AnimatePresence mode='wait'>
                <FlightTable
                  key={flightTab}
                  flights={displayedFlights}
                  isFuture={flightTab === 'future'}
                  onRiskClick={setSelectedRiskFlight}
                />
              </AnimatePresence>
            </div>

            {/* Risk Details Modal */}
            {selectedRiskFlight && (
              <RiskDetailsModal
                flight={selectedRiskFlight}
                onClose={() => setSelectedRiskFlight(null)}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}

const WeatherWidget = ({ forecast }) => {
  if (!forecast || forecast.length === 0) return null
  return (
    <div className="weather-widget">
      {forecast.map((day, i) => (
        <div key={i} className="weather-day">
          <div className="w-day">{day.day}</div>
          <div className="w-icon">
            {day.desc.includes('Snow') ? <CloudSnow size={20} color="#60a5fa" /> :
              day.desc.includes('Rain') ? <CloudRain size={20} color="#60a5fa" /> :
                <Cloud size={20} color="#94a3b8" />}
          </div>
          <div className="w-temp">{day.temp ? Math.round(day.temp) : '--'}°</div>
        </div>
      ))}
    </div>
  )
}


const formatAirport = (code) => {
  if (!code) return ''
  // If 4 letters and starts with K, remove K (e.g. KSEA -> SEA)
  if (code.length === 4 && code.startsWith('K')) {
    return code.substring(1)
  }
  return code
}

const SummaryStats = ({ stats }) => {
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

const FAAStatus = ({ airport, status }) => {
  if (!status) return null

  let color = '#22c55e' // green
  let icon = <CheckCircle size={16} />

  if (status.status === 'Ground Stop') {
    color = '#ef4444'
    icon = <XCircle size={16} />
  } else if (status.status !== 'Normal') {
    color = '#f97316'
    icon = <AlertTriangle size={16} />
  }

  return (
    <div className="faa-item" style={{ color }}>
      <strong>{formatAirport(airport)}</strong>
      {icon}
      <span>{status.status}</span>
    </div>
  )
}

const DataFreshnessIndicator = ({ freshness }) => {
  if (!freshness) return null

  const { flight_data_age_minutes, weather_data_age_minutes, is_stale } = freshness

  const formatAge = (minutes) => {
    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    return `${hours}h ago`
  }

  const flightAge = formatAge(flight_data_age_minutes)
  const weatherAge = formatAge(weather_data_age_minutes)

  const color = is_stale ? '#f97316' : '#22c55e'
  const icon = is_stale ? <AlertTriangle size={16} /> : <CheckCircle size={16} />

  return (
    <div
      className="data-freshness"
      style={{
        marginLeft: 'auto',
        fontSize: '0.8rem',
        color: color,
        display: 'flex',
        alignItems: 'center',
        gap: '6px'
      }}
      title={`Flights: ${flightAge} | Weather: ${weatherAge}`}
    >
      {icon}
      <span>
        Data: {flightAge}
        {is_stale && ' (Stale)'}
      </span>
    </div>
  )
}

const FlightTable = ({ flights, isFuture, onRiskClick }) => {
  if (flights.length === 0) {
    return <div className="loading">No flights found.</div>
  }

  // Group by day
  const groups = flights.reduce((acc, flight) => {
    const dateObj = new Date(flight.scheduled_time)
    const dateKey = dateObj.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    })

    if (!acc[dateKey]) acc[dateKey] = []
    acc[dateKey].push(flight)
    return acc
  }, {})

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
    >
      {Object.entries(groups).map(([date, dayFlights]) => (
        <div key={date} style={{ marginBottom: '32px' }}>
          <div className="date-header">{date}</div>
          <div className="flight-table-container">
            <table className="flight-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Flight</th>
                  <th>Route</th>
                  <th>Aircraft</th>
                  <th>Status</th>
                  <th>Weather</th>
                  <th>Chance</th>
                  <th>Prediction</th>
                  {!isFuture && <th>Accuracy</th>}
                </tr>
              </thead>
              <tbody>
                {dayFlights.map((flight) => (
                  <FlightRow
                    key={flight.id}
                    flight={flight}
                    isFuture={isFuture}
                    onRiskClick={onRiskClick}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </motion.div>
  )
}

const FlightRow = ({ flight, isFuture, onRiskClick }) => {
  const isArrival = flight.type === 'arrival'

  const status = flight.status.toUpperCase()
  let statusClass = 'status-gray'

  if (['LANDED', 'ARRIVED', 'SCHEDULED', 'EXPECTED'].includes(status)) {
    statusClass = 'status-green'
  } else if (['CANCELLED', 'CANCELED'].includes(status)) {
    statusClass = 'status-red'
  } else if (['DELAYED', 'UNKNOWN'].includes(status)) {
    statusClass = 'status-orange'
  } else if (['ACTIVE', 'DEPARTED', 'EN ROUTE'].includes(status)) {
    statusClass = 'status-green'
  }

  // Determine risk border class for upcoming flights
  let riskBorderClass = ''
  if (isFuture && flight.risk_score) {
    const score = flight.risk_score.score
    if (score >= 70) riskBorderClass = 'risk-border-high'
    else if (score >= 40) riskBorderClass = 'risk-border-medium'
  }

  // Aircraft Display
  let aircraftDisplay = flight.aircraft_reg || '--'
  if (!flight.aircraft_reg || flight.aircraft_reg === 'Unknown') {
    aircraftDisplay = "TBA"
  }

  // FlightAware tracking link
  let flightIdent = flight.number.replace(/\s/g, '')
  if (flightIdent.startsWith('AS')) {
    flightIdent = flightIdent.replace('AS', 'ASA')
  } else if (flightIdent.startsWith('DL')) {
    flightIdent = flightIdent.replace('DL', 'DAL')
  } else if (flightIdent.startsWith('UA')) {
    flightIdent = flightIdent.replace('UA', 'UAL')
  }
  const trackUrl = `https://flightaware.com/live/flight/${flightIdent}`

  return (
    <tr className={`flight-row ${statusClass} ${riskBorderClass}`}>
      {/* Time */}
      <td className="time-cell">
        <div className="time-main">{flight.local_time_str}</div>
        {!isFuture && flight.actual_time && (
          <div className="time-sub">
            {new Date(flight.actual_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}
          </div>
        )}
      </td>

      {/* Flight Number */}
      <td className="flight-cell">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className="flight-number">{flight.airline} {flight.number}</span>
          <a href={trackUrl} target="_blank" rel="noreferrer" className="track-link" title="Track on FlightAware">
            <ExternalLink size={12} />
          </a>
        </div>
      </td>

      {/* Route */}
      <td className="route-cell">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {isArrival ? <Plane size={14} style={{ transform: 'rotate(90deg)' }} /> : <Plane size={14} style={{ transform: 'rotate(-45deg)' }} />}
          <span>
            {isArrival
              ? `${formatAirportFull(flight.origin)} → Pullman`
              : `Pullman → ${formatAirportFull(flight.destination)}`
            }
          </span>
        </div>
      </td>

      {/* Aircraft */}
      <td className="aircraft-cell">
        <div>{aircraftDisplay}</div>
        {flight.aircraft_model && (
          <div className="aircraft-model">{flight.aircraft_model}</div>
        )}
      </td>

      {/* Status */}
      <td className="status-cell">
        <span className={`status-badge ${statusClass}`}>
          {flight.status}
        </span>
      </td>

      {/* Weather */}
      <td className="weather-cell">
        {flight.weather ? (
          <div className="weather-summary">
            {formatWeatherPlain(flight.weather)}
          </div>
        ) : (
          <span style={{ color: '#64748b' }}>--</span>
        )}
      </td>

      {/* Cancellation Chance % */}
      <td className="chance-pct-cell" onClick={() => flight.risk_score && onRiskClick(flight)} style={{ cursor: flight.risk_score ? 'pointer' : 'default' }} title={flight.risk_score ? "Click for details" : ""}>
        {flight.risk_score ? (
          <span className="chance-pct">{Math.round(flight.risk_score.score)}%</span>
        ) : (
          <span style={{ color: '#64748b' }}>--</span>
        )}
      </td>

      {/* Prediction Level */}
      <td className="prediction-cell">
        {flight.risk_score ? (
          <span className={`prediction-badge ${flight.risk_score.risk_level.toLowerCase()}`}>
            {formatChanceLevel(flight.risk_score.score).text}
          </span>
        ) : (
          <span style={{ color: '#64748b' }}>--</span>
        )}
      </td>

      {/* Accuracy (Historical only) */}
      {!isFuture && (
        <td className="accuracy-cell">
          {flight.prediction_grade && (
            <span className={`grade-badge-compact ${flight.prediction_grade.toLowerCase().replace(/\s/g, '-')}`}>
              {flight.prediction_grade === "Nailed It" && "🎯 Correct"}
              {flight.prediction_grade === "Smooth" && "✅ Correct"}
              {flight.prediction_grade === "Miss" && "🤥 Missed"}
              {flight.prediction_grade === "False Alarm" && "😅 Missed"}
              {flight.prediction_grade === "Neutral" && "Neutral"}
            </span>
          )}
        </td>
      )}
    </tr>
  )
}

const FlightCard = ({ flight, isFuture, onRiskClick }) => {
  const status = flight.status.toUpperCase()
  let statusClass = 'badge-gray'
  let borderClass = 'status-gray'

  if (['LANDED', 'ARRIVED', 'SCHEDULED', 'EXPECTED'].includes(status)) {
    statusClass = 'badge-green'
    borderClass = 'status-green'
  } else if (['CANCELLED', 'CANCELED'].includes(status)) {
    statusClass = 'badge-red'
    borderClass = 'status-red'
  } else if (['DELAYED', 'UNKNOWN'].includes(status)) {
    statusClass = 'badge-orange'
    borderClass = 'status-orange'
  } else if (['ACTIVE', 'DEPARTED', 'EN ROUTE'].includes(status)) {
    statusClass = 'badge-green' // Active is good
    borderClass = 'status-green'
  }

  const isArrival = flight.type === 'arrival'

  // Aircraft Display Logic
  let aircraftDisplay = flight.aircraft_reg || '--'
  let aircraftClass = ''
  if (!flight.aircraft_reg || flight.aircraft_reg === 'Unknown') {
    aircraftDisplay = "To Be Assigned"
    aircraftClass = 'text-gray-500 italic'
  }

  // Tracking URL (FlightAware)
  // Format: https://flightaware.com/live/flight/ASA2054
  // We need to map IATA (AS) to ICAO (ASA)
  let flightIdent = flight.number.replace(/\s/g, '')
  if (flightIdent.startsWith('AS')) {
    flightIdent = flightIdent.replace('AS', 'ASA')
  } else if (flightIdent.startsWith('DL')) {
    flightIdent = flightIdent.replace('DL', 'DAL')
  } else if (flightIdent.startsWith('UA')) {
    flightIdent = flightIdent.replace('UA', 'UAL')
  }

  const trackUrl = `https://flightaware.com/live/flight/${flightIdent}`

  return (
    <div className={`flight-card ${borderClass}`}>
      {/* Time Column */}
      <div className="time-col">
        <div className="time-main">{flight.local_time_str}</div>
        <div className="time-sub">
          {isFuture ? "Sched" : (flight.actual_time ? "Act: " + new Date(flight.actual_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true }) : "Sched")}
        </div>
      </div>

      {/* Info Column */}
      <div className="info-col">
        <div className="flight-number-row">
          <div className="flight-number">{flight.airline} {flight.number}</div>
          <a href={trackUrl} target="_blank" rel="noreferrer" className="track-link" title="Track on FlightAware">
            <ExternalLink size={12} />
          </a>
        </div>
        <div className="route">
          {isArrival ? <Plane size={14} style={{ transform: 'rotate(90deg)' }} /> : <Plane size={14} style={{ transform: 'rotate(-45deg)' }} />}
          {isArrival ? `${formatAirportFull(flight.origin)} → Pullman` : `Pullman → ${formatAirportFull(flight.destination)}`}
        </div>
        <div className="details">
          <span className={aircraftClass}>{aircraftDisplay}</span>
          {flight.aircraft_model && <span>• {flight.aircraft_model}</span>}
        </div>
      </div>

      {/* Status Column */}
      <div className="status-col">
        <div className={`status-badge ${statusClass}`}>
          {flight.status}
        </div>

        {/* Prediction Grade Badge (Historical Only) */}
        {!isFuture && flight.prediction_grade && (
          <div className={`grade-badge ${flight.prediction_grade.toLowerCase().replace(/\s/g, '-')}`}>
            {flight.prediction_grade === "Nailed It" && (
              <>🎯 Correct <span className="grade-detail">(High chance → Cancelled)</span></>
            )}
            {flight.prediction_grade === "Smooth" && (
              <>✅ Correct <span className="grade-detail">(Low chance → Landed)</span></>
            )}
            {flight.prediction_grade === "Miss" && (
              <>🤥 Missed <span className="grade-detail">(Low chance → Cancelled)</span></>
            )}
            {flight.prediction_grade === "False Alarm" && (
              <>😅 Missed <span className="grade-detail">(High chance → Landed)</span></>
            )}
            {flight.prediction_grade === "Neutral" && "Neutral"}
          </div>
        )}

        {flight.weather && (
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {formatWeatherPlain(flight.weather)}
          </div>
        )}
        {/* Cancellation Chance */}
        {flight.risk_score && (
          <div
            className={`risk-badge ${flight.risk_score.risk_level.toLowerCase()}`}
            title="Click for details"
            onClick={() => onRiskClick(flight)}
            style={{ cursor: 'pointer', marginTop: '6px' }}
          >
            <div className={`risk-dot ${flight.risk_score.risk_level.toLowerCase()}`}></div>
            <span>
              {Math.round(flight.risk_score.score)}% chance • {formatChanceLevel(flight.risk_score.score).text}
            </span>
          </div>
        )}
      </div>

      {/* Alerts Row */}
      {(flight.inbound_alert || (flight.weather && flight.weather.is_adverse)) && (
        <div className="alert-row">
          {flight.inbound_alert && (
            <div className="alert-item alert-red">
              <AlertTriangle size={14} />
              {flight.inbound_alert}
            </div>
          )}
          {flight.weather && flight.weather.is_adverse && (
            <div className="alert-item alert-orange">
              <AlertTriangle size={14} />
              Weather Risk
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const Scorecard = ({ flights }) => {
  const [showLegend, setShowLegend] = useState(false)

  if (!flights || flights.length === 0) return null

  // Calculate Stats
  let nailed = 0
  let smooth = 0
  let miss = 0
  let falseAlarm = 0
  let totalGraded = 0

  flights.forEach(f => {
    if (f.prediction_grade) {
      totalGraded++
      if (f.prediction_grade === "Nailed It") nailed++
      else if (f.prediction_grade === "Smooth") smooth++
      else if (f.prediction_grade === "Miss") miss++
      else if (f.prediction_grade === "False Alarm") falseAlarm++
    }
  })

  if (totalGraded === 0) return null

  return (
    <div className="scorecard-container">
      <div className="scorecard-header">
        <h3>Prediction Accuracy</h3>
        <button className="legend-toggle" onClick={() => setShowLegend(!showLegend)}>
          {showLegend ? "Hide" : "Show details"}
        </button>
      </div>

      {showLegend && (
        <div className="scorecard-legend">
          <div className="legend-item">
            <span className="emoji">🎯</span> <strong>Correct:</strong> High chance prediction, flight cancelled
          </div>
          <div className="legend-item">
            <span className="emoji">✅</span> <strong>Correct:</strong> Low chance prediction, flight landed
          </div>
          <div className="legend-item">
            <span className="emoji">😅</span> <strong>Missed:</strong> High chance prediction, but flight landed
          </div>
          <div className="legend-item">
            <span className="emoji">🤥</span> <strong>Missed:</strong> Low chance prediction, but flight cancelled
          </div>
        </div>
      )}

      <div className="scorecard-grid">
        <div className="score-item">
          <div className="score-emoji">🎯</div>
          <div className="score-val">{nailed}</div>
          <div className="score-label">Correct</div>
        </div>
        <div className="score-item">
          <div className="score-emoji">✅</div>
          <div className="score-val">{smooth}</div>
          <div className="score-label">Correct</div>
        </div>
        <div className="score-item">
          <div className="score-emoji">😅</div>
          <div className="score-val">{falseAlarm}</div>
          <div className="score-label">Missed</div>
        </div>
        <div className="score-item">
          <div className="score-emoji">🤥</div>
          <div className="score-val">{miss}</div>
          <div className="score-label">Missed</div>
        </div>
      </div>
    </div>
  )
}

const RiskDetailsModal = ({ flight, onClose }) => {
  const { risk_score } = flight
  if (!risk_score) return null

  const breakdown = risk_score.breakdown || {
    seasonal_baseline: 0,
    weather_score: 0,
    history_adjustment: 0,
    final_score: risk_score.score
  }

  const detailedFactors = risk_score.detailed_factors || []

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Cancellation Chance: {flight.airline} {flight.number}</h2>
          <button className="close-btn" onClick={onClose}><XCircle size={24} /></button>
        </div>
        <div className="modal-body">
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
            <div className={`risk-badge large ${risk_score.risk_level.toLowerCase()}`} style={{ fontSize: '1.5rem', padding: '10px 20px' }}>
              {Math.round(risk_score.score)}% chance of cancellation
            </div>
          </div>
          <div style={{ textAlign: 'center', marginBottom: '20px', fontSize: '1.1rem', fontWeight: 600 }}>
            {formatChanceLevel(risk_score.score).text}
          </div>

          <div className="breakdown-table">
            <div className="breakdown-row">
              <span>Seasonal Baseline</span>
              <span>+{breakdown.seasonal_baseline}%</span>
            </div>
            <div className="breakdown-row">
              <span>Weather Factors</span>
              <span>+{breakdown.weather_score}%</span>
            </div>
            {breakdown.history_adjustment !== 0 && (
              <div className="breakdown-row highlight">
                <span>Historical Adjustment</span>
                <span>{breakdown.history_adjustment > 0 ? '+' : ''}{breakdown.history_adjustment.toFixed(1)}%</span>
              </div>
            )}
            <div className="breakdown-total">
              <span>Cancellation Chance</span>
              <span>{Math.round(risk_score.score)}%</span>
            </div>
          </div>

          <div className="factors-list">
            <h3>Contributing Factors</h3>
            {detailedFactors.length > 0 ? (
              <div className="detailed-factors">
                {detailedFactors.map((f, i) => (
                  <div key={i} className={`factor-card ${f.category.toLowerCase()}`}>
                    <div className="factor-header">
                      <span className="factor-cat">{f.category}</span>
                    </div>
                    <div className="factor-desc">{f.description}</div>
                    {f.category === 'History' && f.details && (
                      <div className="factor-stats">
                        <div className="stat-pill">
                          <span className="label">Match:</span> {f.details.match_criteria}
                        </div>
                        <div className="stat-pill">
                          <span className="label">Found:</span> {f.details.total_flights} flights
                        </div>
                        <div className="stat-pill highlight">
                          <span className="label">Result:</span> {f.details.cancellation_rate}% Cancelled
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              risk_score.factors.length > 0 ? (
                <ul>
                  {risk_score.factors.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              ) : (
                <p style={{ color: '#64748b', fontStyle: 'italic' }}>No significant risk factors detected.</p>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
