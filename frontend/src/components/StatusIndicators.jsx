import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { formatAirport } from '../utils/helpers'

export function FAAStatus({ airport, status }) {
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

export function DataFreshnessIndicator({ freshness }) {
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
