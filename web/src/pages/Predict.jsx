import { useEffect, useState } from 'react'
import axios from 'axios'
import Spinner from '../components/Spinner'
import StatCard from '../components/StatCard'
import ProbBar from '../components/ProbBar'

export default function Predict() {
  const [teams, setTeams] = useState([])
  const [venues, setVenues] = useState([])
  const [team, setTeam] = useState('')
  const [opponent, setOpponent] = useState('')
  const [venue, setVenue] = useState('')
  const [accuracy, setAccuracy] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [initLoading, setInitLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      axios.get('/api/teams'),
      axios.get('/api/venues'),
      axios.get('/api/model-accuracy'),
    ]).then(([t, v, a]) => {
      setTeams(t.data.teams)
      setVenues(v.data.venues)
      setAccuracy(a.data)
      setTeam(t.data.teams[0] || '')
      setOpponent(t.data.teams[1] || '')
      setVenue(v.data.venues[0] || '')
    }).catch(() => {}).finally(() => setInitLoading(false))
  }, [])

  const oppOptions = teams.filter(t => t !== team)

  async function predict() {
    if (!team || !opponent || !venue) return
    setLoading(true); setError(''); setResult(null)
    try {
      const r = await axios.post('/api/predict', { team, opponent, venue })
      setResult(r.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Prediction failed')
    } finally { setLoading(false) }
  }

  if (initLoading) return <Spinner text="Loading model data…" />

  const pred = result?.prediction
  const expl = result?.explanation
  const extras = result?.extras

  const pct = v => v != null ? `${(v * 100).toFixed(1)}%` : 'N/A'

  return (
    <div className="fade-in">
      <h1 className="page-title"> Match <span>Predictor</span></h1>
      <p className="page-lead">Our ML model predicts win probabilities using head-to-head records, venue stats and recent form.</p>

      {/* Accuracy strip */}
      {accuracy && (
        <div className="stats-row" style={{ marginBottom: '1.75rem' }}>
          <StatCard title="Test Matches" value={accuracy.total} sub="evaluated" />
          <StatCard title="Accuracy" value={`${accuracy.accuracy}%`} sub="overall" color="#10b981" />
          <StatCard title="Avg Confidence" value={`${accuracy.avg_confidence}%`} sub="per prediction" color="#f4d03f" />
          <StatCard title=">70% Confidence" value={`${accuracy.by_confidence['70']?.accuracy}%`} sub={`${accuracy.by_confidence['70']?.count} matches`} color="#7c3aed" />
        </div>
      )}

      {/* Predictor form */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="section-title" style={{ marginBottom: '1rem' }}> Configure Match</div>
        <div className="form-row">
          <div className="form-group">
            <label>Your Team</label>
            <select value={team} onChange={e => { setTeam(e.target.value); setResult(null) }}>
              {teams.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Opponent</label>
            <select value={opponent} onChange={e => { setOpponent(e.target.value); setResult(null) }}>
              {oppOptions.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Venue</label>
            <select value={venue} onChange={e => { setVenue(e.target.value); setResult(null) }}>
              {venues.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
        </div>
        <button className="btn-primary" onClick={predict} disabled={loading || !team || !opponent || !venue}>
          {loading ? 'Predicting…' : 'Generate Prediction'}
        </button>
      </div>

      {error && <div className="banner banner-error" style={{ marginBottom: '1rem' }}>{error}</div>}
      {loading && <Spinner text="Running ML model…" />}

      {result && (
        <div className="fade-in">
          {/* Win probability */}
          <div className="card" style={{ marginBottom: '1.25rem' }}>
            <div className="section-title"> Win Probability</div>
            <ProbBar
              teamA={pred.team} teamB={pred.opponent}
              probA={(pred.team_win_probability * 100).toFixed(1)}
              probB={(pred.opponent_win_probability * 100).toFixed(1)}
            />
            <div style={{ textAlign: 'center', marginTop: '1rem' }}>
              <span className="pill pill-gold" style={{ fontSize: '0.88rem' }}>
                 Predicted winner: {pred.team_win_probability > pred.opponent_win_probability ? pred.team : pred.opponent}
              </span>
            </div>
          </div>

          {/* Key stats grid */}
          {extras && (
            <div className="card" style={{ marginBottom: '1.25rem' }}>
              <div className="section-title"> Key Match Features</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: '0.75rem', marginTop: '0.5rem' }}>
                {[
                  { label: 'Batting First Win %', a: extras.team_batting_first_win_pct, b: extras.opp_batting_first_win_pct },
                  { label: 'Home Ground Win %', a: extras.team_home_win_pct, b: extras.opp_home_win_pct },
                  { label: 'Head-to-Head Win %', a: extras.team_h2h_win_pct, b: extras.opp_h2h_win_pct },
                  { label: 'Toss Win → Match Win %', a: extras.team_toss_win_pct, b: extras.opp_toss_win_pct },
                ].map(({ label, a, b }) => (
                  <div key={label} style={{ background: 'var(--bg-elevated)', borderRadius: 10, padding: '0.85rem 1rem', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ textAlign: 'center', flex: 1 }}>
                        <div style={{ fontFamily: 'Outfit', fontSize: '1.3rem', fontWeight: 800, color: '#7c3aed' }}>{pct(a)}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{pred.team}</div>
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontWeight: 700, padding: '0 0.5rem' }}>vs</div>
                      <div style={{ textAlign: 'center', flex: 1 }}>
                        <div style={{ fontFamily: 'Outfit', fontSize: '1.3rem', fontWeight: 800, color: '#ff6b35' }}>{pct(b)}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{pred.opponent}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Feature drivers */}
          {pred.top_features?.length > 0 && (
            <div className="card" style={{ marginBottom: '1.25rem' }}>
              <div className="section-title"> Top Feature Drivers</div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Feature</th><th>Value</th><th>Importance</th><th>Weighted Impact</th></tr>
                  </thead>
                  <tbody>
                    {pred.top_features.map((f, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600, color: 'var(--text)' }}>{f.feature}</td>
                        <td>{typeof f.value === 'number' ? f.value.toFixed(3) : f.value}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ flex: 1, height: 6, background: 'var(--bg-elevated)', borderRadius: 999, overflow: 'hidden' }}>
                              <div style={{ height: '100%', width: `${Math.min(f.importance * 500, 100)}%`, background: 'var(--gold)', borderRadius: 999 }} />
                            </div>
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{f.importance?.toFixed(3)}</span>
                          </div>
                        </td>
                        <td style={{ color: 'var(--gold-dim)', fontWeight: 700 }}>{f.weighted?.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* AI explanation */}
          {expl && (
            <div className="card">
              <div className="section-title"> AI Match Summary</div>
              {[
                { label: 'Match Summary', text: expl.match_summary },
                { label: 'Key Feature Drivers', text: expl.feature_drivers },
                { label: 'Venue Impact', text: expl.venue_impact },
                { label: 'Final Prediction', text: expl.final_explanation },
              ].map(({ label, text }) => (
                <div key={label} style={{ borderLeft: '3px solid var(--gold)', paddingLeft: '1rem', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--gold-dim)', marginBottom: '0.3rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
                  <div style={{ color: 'var(--text)', fontSize: '0.9rem', lineHeight: 1.6 }}>{text}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
