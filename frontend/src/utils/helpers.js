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

  // Wind - Show gusts if available, otherwise sustained
  if (weather.wind_gust_knots != null && weather.wind_gust_knots > weather.wind_speed_knots) {
    const gust = weather.wind_gust_knots
    if (gust < 15) parts.push('Light gusts')
    else if (gust < 25) parts.push(`Moderate gusts (${Math.round(gust)}kn)`)
    else parts.push(`Strong gusts (${Math.round(gust)}kn)`)
  } else if (weather.wind_speed_knots != null) {
    const wind = weather.wind_speed_knots
    if (wind < 10) parts.push('Calm winds')
    else if (wind < 20) parts.push('Light winds')
    else if (wind < 30) parts.push('Moderate winds')
    else parts.push('Strong winds')
  }

  // Snow depth
  if (weather.snow_depth_in != null && weather.snow_depth_in > 0) {
    parts.push(`${weather.snow_depth_in.toFixed(1)}" snow`)
  }

  // Active precipitation
  if (weather.precipitation_in != null && weather.precipitation_in > 0.05) {
    if (weather.temperature_f != null && weather.temperature_f < 32) {
      parts.push(`Snowing`)
    } else {
      parts.push(`Raining`)
    }
  }

  // Conditions (if notable)
  if (weather.conditions && ['Fog', 'Thunderstorm', 'Ice', 'Freezing'].some(word => weather.conditions.includes(word))) {
    parts.push(weather.conditions)
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

export const formatMultiAirportWeather = (flight) => {
  const { multi_airport_weather, type, origin, destination } = flight

  if (!multi_airport_weather) {
    return null // Fall back to single weather display
  }

  // Get PUW weather (always show)
  const puwWeather = multi_airport_weather['KPUW']

  // Get the other relevant airport based on flight type
  const otherCode = type === 'arrival' ? origin : destination
  const otherWeather = multi_airport_weather[otherCode]

  // Helper to format compact weather
  const formatCompact = (weather) => {
    if (!weather) return '–'
    const parts = []

    // Temperature
    if (weather.temperature_f != null) {
      parts.push(`${Math.round(weather.temperature_f)}°`)
    }

    // Visibility (always show)
    if (weather.visibility_miles != null) {
      const vis = weather.visibility_miles
      // Show more precision for low visibility
      if (vis < 3) {
        parts.push(`${vis.toFixed(1)}mi`)
      } else {
        parts.push(`${Math.round(vis)}mi`)
      }
    }

    // Wind - prefer gusts over sustained
    if (weather.wind_gust_knots != null && weather.wind_gust_knots > weather.wind_speed_knots) {
      parts.push(`G${Math.round(weather.wind_gust_knots)}kn`)
    } else if (weather.wind_speed_knots != null) {
      parts.push(`${Math.round(weather.wind_speed_knots)}kn`)
    }

    // Snow depth (compact)
    if (weather.snow_depth_in != null && weather.snow_depth_in > 0) {
      parts.push(`${weather.snow_depth_in.toFixed(1)}"❄`)
    }

    // Active precipitation (icon only for compact display)
    if (weather.precipitation_in != null && weather.precipitation_in > 0.05) {
      if (weather.temperature_f != null && weather.temperature_f < 32) {
        parts.push('🌨')
      } else {
        parts.push('🌧')
      }
    }

    return parts.length > 0 ? parts.join(' · ') : '✓'
  }

  // Helper to check if weather is concerning
  const isConcerning = (weather) => {
    if (!weather) return false
    // Check gusts preferentially, then sustained winds
    const effectiveWind = weather.wind_gust_knots || weather.wind_speed_knots
    return (weather.visibility_miles && weather.visibility_miles < 3) ||
           (effectiveWind && effectiveWind > 25) ||
           (weather.snow_depth_in && weather.snow_depth_in > 3) ||
           (weather.precipitation_in && weather.precipitation_in > 0.2)
  }

  const puwDisplay = formatCompact(puwWeather)
  const puwConcerning = isConcerning(puwWeather)

  const otherDisplay = formatCompact(otherWeather)
  const otherConcerning = isConcerning(otherWeather)
  const otherLabel = formatAirport(otherCode)

  return {
    puw: { display: puwDisplay, concerning: puwConcerning },
    other: { display: otherDisplay, concerning: otherConcerning, label: otherLabel }
  }
}
