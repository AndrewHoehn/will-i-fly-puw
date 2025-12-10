import { Camera, Plane, ExternalLink, MapPin, Mail } from 'lucide-react'

export function ResourcesPage() {
  return (
    <div className="page-content">
      <h2 style={{ marginTop: 0, marginBottom: '12px', fontSize: '1.5rem' }}>Resources & Travel Tips</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.6' }}>
        Practical resources for traveling through Pullman-Moscow Regional Airport, plus tips for dealing with winter weather travel.
      </p>

      {/* Reality Check Card */}
      <div style={{ marginBottom: '20px', padding: '16px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
        <h3 style={{ margin: '0 0 8px 0', fontSize: '1rem', color: '#3b82f6', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>ℹ️</span> <span>The Reality: PUW is Pretty Reliable</span>
        </h3>
        <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
          Let's be honest: <strong>most flights operate normally</strong>, even in winter. The overall cancellation rate is around 2-3%, and the vast majority of those happen December-February. If you're traveling outside winter months, you probably don't need to worry much. This tracker is most useful for winter travel planning.
        </p>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">Monitor Live Conditions</div>
        <div className="card-body">
          <a
            href="https://wsdot.wa.gov/travel/aviation/airports-list/pullman-moscow-regional"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px',
              marginBottom: '8px',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              textDecoration: 'none',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-tertiary)'
              e.currentTarget.style.borderColor = 'var(--blue)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--bg-secondary)'
              e.currentTarget.style.borderColor = 'var(--border-default)'
            }}
          >
            <Camera size={24} className="text-blue-400" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, marginBottom: '4px' }}>PUW Airport Webcam</div>
              <div className="text-secondary" style={{ fontSize: '0.875rem' }}>
                See actual runway visibility and weather conditions in real-time
              </div>
            </div>
            <ExternalLink size={16} className="text-secondary" />
          </a>

          <a
            href="https://www.flypuw.com/"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              textDecoration: 'none',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-tertiary)'
              e.currentTarget.style.borderColor = 'var(--blue)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--bg-secondary)'
              e.currentTarget.style.borderColor = 'var(--border-default)'
            }}
          >
            <Plane size={24} className="text-green-400" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, marginBottom: '4px' }}>Official PUW Airport Site</div>
              <div className="text-secondary" style={{ fontSize: '0.875rem' }}>
                Parking, terminal info, and official airport announcements
              </div>
            </div>
            <ExternalLink size={16} className="text-secondary" />
          </a>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">Flight Status & Booking</div>
        <div className="card-body">
          <a
            href="https://www.alaskaair.com/content/travel-info/flight-status"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              textDecoration: 'none',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-tertiary)'
              e.currentTarget.style.borderColor = 'var(--blue)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--bg-secondary)'
              e.currentTarget.style.borderColor = 'var(--border-default)'
            }}
          >
            <div
              style={{
                width: '24px',
                height: '24px',
                background: 'var(--blue)',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.75rem'
              }}
            >
              AS
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, marginBottom: '4px' }}>Alaska Airlines Flight Status</div>
              <div className="text-secondary" style={{ fontSize: '0.875rem' }}>
                Real-time flight status, delays, and rebooking options
              </div>
            </div>
            <ExternalLink size={16} className="text-secondary" />
          </a>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '16px' }}>
        <div className="card-header">The Spokane Alternative</div>
        <div className="card-body">
          <p style={{ margin: '0 0 16px 0', fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
            <strong>Be ready to drive to Spokane</strong> if you're traveling in winter and can't afford delays. Spokane International Airport (GEG) is 90 minutes north and has significantly more flight options, making it more resilient to weather issues.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '16px' }}>
            <div style={{ padding: '12px', background: 'rgba(100, 116, 139, 0.1)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Drive Time</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>90 min</div>
            </div>
            <div style={{ padding: '12px', background: 'rgba(100, 116, 139, 0.1)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Distance</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>80 miles</div>
            </div>
          </div>

          <a
            href="https://www.spokaneairports.net/"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              background: 'var(--blue)',
              color: 'white',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '0.9rem',
              fontWeight: 500,
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#2563eb'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--blue)'
            }}
          >
            <MapPin size={16} />
            <span>Spokane Airport (GEG)</span>
            <ExternalLink size={14} />
          </a>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Winter Travel Tips</div>
        <div className="card-body">
          <ul className="text-secondary" style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8' }}>
            <li style={{ marginBottom: '12px' }}>
              <strong>Sign up for flight alerts</strong>: Alaska Airlines text/email notifications will tell you about delays or cancellations before you leave for the airport
            </li>
            <li style={{ marginBottom: '12px' }}>
              <strong>December-February are the tricky months</strong>: Low visibility and crosswinds cause most cancellations.
            </li>
            <li style={{ marginBottom: '12px' }}>
              <strong>Have a Plan B</strong>: Keep Spokane (GEG) as a backup option for critical trips. Book flexible tickets if possible.
            </li>
            <li style={{ marginBottom: '12px' }}>
              <strong>Know your rebooking options</strong>: If your flight cancels, Alaska Airlines can often rebook you through Spokane same-day
            </li>
          </ul>
        </div>
      </div>

      <div className="card" style={{ marginTop: '16px' }}>
        <div className="card-header">Questions or Feedback?</div>
        <div className="card-body">
          <p style={{ margin: '0 0 16px 0', fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
            Have suggestions for improving the tracker? Found an issue? Want to report prediction accuracy? We'd love to hear from you.
          </p>
          <a
            href="mailto:info@williflypuw.com"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              background: 'var(--blue)',
              color: 'white',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '0.95rem',
              fontWeight: 500,
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#2563eb'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--blue)'
            }}
          >
            <Mail size={18} />
            <span>info@williflypuw.com</span>
          </a>
          <div style={{ marginTop: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Or contribute on{' '}
            <a
              href="https://github.com/AndrewHoehn/will-i-fly-puw"
              target="_blank"
              rel="noreferrer"
              style={{ color: 'var(--blue)', textDecoration: 'none' }}
            >
              GitHub
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
