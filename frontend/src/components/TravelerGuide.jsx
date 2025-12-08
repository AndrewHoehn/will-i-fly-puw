import { useState } from 'react'
import { XCircle, Info, Map, Camera, Plane, ExternalLink } from 'lucide-react'

export function TravelerGuide({ onClose }) {
  const [tab, setTab] = useState('guide') // guide, toolkit

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>✈️ Traveler's Guide</h2>
          <button className="close-btn" onClick={onClose}><XCircle size={24} /></button>
        </div>

        <div className="guide-tabs">
          <button className={`guide-tab ${tab === 'guide' ? 'active' : ''}`} onClick={() => setTab('guide')}>
            <Info size={16} /> How This Works
          </button>
          <button className={`guide-tab ${tab === 'toolkit' ? 'active' : ''}`} onClick={() => setTab('toolkit')}>
            <Map size={16} /> Toolkit & Webcams
          </button>
        </div>

        <div className="modal-body">
          {tab === 'guide' ? (
            <div className="guide-content">
              <p className="intro-text">
                Welcome to the <strong>KPUW Flight Board</strong>! Flying out of Pullman can be an adventure 🏔️.
                We built this tool to give you the <em>real</em> story on your flight's chances.
              </p>

              <div className="feature-block">
                <h3>🔮 The Crystal Ball (Risk Scores)</h3>
                <p>See those colored badges? That's our <strong>Cancellation Risk Score</strong>.</p>
                <ul>
                  <li>🟢 <strong>Low Risk</strong>: Pack your bags, you're likely good to go!</li>
                  <li>🟠 <strong>Medium Risk</strong>: Keep an eye on the weather. Maybe download a movie just in case.</li>
                  <li>🔴 <strong>High Risk</strong>: Uh oh. The weather (or history) looks gnarly. Have a backup plan!</li>
                </ul>
              </div>

              <div className="feature-block">
                <h3>🧠 How We Know</h3>
                <p>We don't just guess! We look at three things:</p>
                <ol>
                  <li><strong>The Weather:</strong> Fog, wind, and ice are the enemies. We track them all.</li>
                  <li><strong>The Calendar:</strong> Flying in December? That's tougher than July. We know that.</li>
                  <li><strong>The History Books:</strong> We check over 1,300 past flights. If flights cancelled in <em>this exact weather</em> before, we warn you.</li>
                </ol>
              </div>

              <div className="feature-block highlight">
                <h3>🤖 We Get Smarter</h3>
                <p>Every time a flight lands (or cancels), our system learns from it. We're constantly tuning our crystal ball to be more accurate for <strong>you</strong>.</p>
              </div>
            </div>
          ) : (
            <div className="toolkit-content">
              <p className="intro-text">Useful links for the savvy Pullman traveler.</p>

              <div className="resource-grid">
                <a href="https://wsdot.wa.gov/travel/aviation/airports-list/pullman-moscow-regional" target="_blank" rel="noreferrer" className="resource-card">
                  <Camera size={32} className="text-blue-400" />
                  <div>
                    <h4>Airport Webcams</h4>
                    <p>See the runway conditions live on WSDOT.</p>
                  </div>
                  <ExternalLink size={16} className="link-icon" />
                </a>

                <a href="https://www.flypuw.com/" target="_blank" rel="noreferrer" className="resource-card">
                  <Plane size={32} className="text-green-400" />
                  <div>
                    <h4>Official PUW Site</h4>
                    <p>Parking info, terminal maps, and official news.</p>
                  </div>
                  <ExternalLink size={16} className="link-icon" />
                </a>

                <a href="https://www.alaskaair.com/content/travel-info/flight-status" target="_blank" rel="noreferrer" className="resource-card">
                  <div className="icon-text">AS</div>
                  <div>
                    <h4>Alaska Airlines Status</h4>
                    <p>Official flight status and rebooking tools.</p>
                  </div>
                  <ExternalLink size={16} className="link-icon" />
                </a>
              </div>

              <div className="tip-box">
                <h4>💡 Pro Tip:</h4>
                <p>Click the <strong>Risk Score</strong> on any flight to see exactly <em>why</em> we think it might cancel. Transparency is key!</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
