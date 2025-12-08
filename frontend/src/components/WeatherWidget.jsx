import { CloudRain, Cloud, CloudSnow } from 'lucide-react'

export function WeatherWidget({ forecast }) {
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
