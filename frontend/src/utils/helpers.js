export const formatAirport = (code) => {
  if (!code) return ''
  // If 4 letters and starts with K, remove K (e.g. KSEA -> SEA)
  if (code.length === 4 && code.startsWith('K')) {
    return code.substring(1)
  }
  return code
}

export const formatAirportFull = (code) => {
  const map = {
    'KSEA': 'Seattle',
    'SEA': 'Seattle',
    'KBOI': 'Boise',
    'BOI': 'Boise',
    'KPUW': 'Pullman',
    'PUW': 'Pullman'
  }
  return map[code] || code
}

export const formatWeatherPlain = (weather) => {
  if (!weather) return 'Weather unavailable'

  const parts = []

  // Temperature
  if (weather.temperature_f != null) {
    parts.push(`${Math.round(weather.temperature_f)}°F`)
  }

  // Visibility - Plain English with detail
  if (weather.visibility_miles != null) {
    const vis = weather.visibility_miles
    const visStr = vis.toFixed(1)
    if (vis > 5) parts.push('Clear visibility')
    else if (vis > 3) parts.push(`Good visibility (${visStr}mi)`)
    else if (vis > 1) parts.push(`Reduced visibility (${visStr}mi)`)
    else parts.push(`Low visibility (${visStr}mi)`)
  }

  // Wind - Plain English
  if (weather.wind_speed_knots != null) {
    const wind = weather.wind_speed_knots
    if (wind < 10) parts.push('Calm winds')
    else if (wind < 20) parts.push('Light winds')
    else if (wind < 30) parts.push('Moderate winds')
    else parts.push('Strong winds')
  }

  return parts.length > 0 ? parts.join(' • ') : 'Weather data unavailable'
}

export const getFilteredFlights = (flights, filterDirection, filterAirport) => {
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

export const formatChanceLevel = (score) => {
  if (score < 40) return { text: 'Likely to Fly ✓', class: 'low' }
  if (score < 70) return { text: 'Watch Closely ⚠', class: 'medium' }
  return { text: 'High Chance ✗', class: 'high' }
}
