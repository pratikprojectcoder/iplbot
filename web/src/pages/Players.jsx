import { useEffect, useState } from 'react'
import axios from 'axios'
import Spinner from '../components/Spinner'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const CTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 10, padding: '0.6rem 0.9rem', fontSize: '0.82rem' }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      {payload.map(p => <div key={p.name} style={{ color: p.color, fontWeight: 700 }}>{p.name}: {p.value}</div>)}
    </div>
  )
}

function DataTable({ rows, cols }) {
  if (!rows?.length) return <div style={{ color: 'var(--text-muted)', padding: '1rem', fontSize: '0.85rem' }}>No data available.</div>
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{cols.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map(c => (
                <td key={c.key} style={c.bold ? { fontWeight: 700, color: 'var(--text)' } : {}}>
                  {typeof r[c.key] === 'number' ? Number(r[c.key]).toFixed(2) : (r[c.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const TABS = ['Performance Predictions', 'Best XI Builder', 'Season Leaders', 'Squad Strength']

export default function Players() {
  const [tab, setTab] = useState(0)
  const [teams, setTeams] = useState([])
  const [venues, setVenues] = useState([])
  const [loading, setLoading] = useState(true)

  // Performance predictions
  const [ppTeam, setPpTeam] = useState('')
  const [ppOpp, setPpOpp] = useState('')
  const [ppVenue, setPpVenue] = useState('')
  const [ppResult, setPpResult] = useState(null)
  const [ppLoading, setPpLoading] = useState(false)

  // Best XI
  const [xiTeam, setXiTeam] = useState('')
  const [xiResult, setXiResult] = useState(null)
  const [xiLoading, setXiLoading] = useState(false)

  // Leaders
  const [leaders, setLeaders] = useState(null)
  const [ldLoading, setLdLoading] = useState(false)
  const [ldFetched, setLdFetched] = useState(false)

  // Squad strength
  const [sqA, setSqA] = useState('')
  const [sqB, setSqB] = useState('')
  const [sqResult, setSqResult] = useState(null)
  const [sqLoading, setSqLoading] = useState(false)

  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([axios.get('/api/teams'), axios.get('/api/venues')]).then(([t, v]) => {
      setTeams(t.data.teams)
      setVenues(v.data.venues)
      setPpTeam(t.data.teams[0] || '')
      setPpOpp(t.data.teams[1] || '')
      setXiTeam(t.data.teams[0] || '')
      setSqA(t.data.teams[0] || '')
      setSqB(t.data.teams[1] || '')
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (tab === 2 && !ldFetched) {
      setLdLoading(true)
      axios.get('/api/players/leaders').then(r => { setLeaders(r.data); setLdFetched(true) }).catch(() => {}).finally(() => setLdLoading(false))
    }
  }, [tab, ldFetched])

  async function fetchPerformance() {
    setPpLoading(true); setError(''); setPpResult(null)
    try {
      const r = await axios.post('/api/players/performance', { team: ppTeam, opponent: ppOpp, venue: ppVenue || null })
      setPpResult(r.data)
    } catch (e) { setError(e.response?.data?.detail || 'Failed') }
    finally { setPpLoading(false) }
  }

  async function fetchBestXI() {
    setXiLoading(true); setError(''); setXiResult(null)
    try { const r = await axios.post('/api/players/best-xi', { team: xiTeam }); setXiResult(r.data) }
    catch (e) { setError(e.response?.data?.detail || 'Failed') }
    finally { setXiLoading(false) }
  }

  async function fetchSquad() {
    setSqLoading(true); setError(''); setSqResult(null)
    try { const r = await axios.post('/api/players/squad-strength', { team_a: sqA, team_b: sqB }); setSqResult(r.data) }
    catch (e) { setError(e.response?.data?.detail || 'Failed') }
    finally { setSqLoading(false) }
  }

  if (loading) return <Spinner text="Loading team data…" />

  const batCols = [
    { key: 'player', label: 'Player', bold: true },
    { key: 'player_last5_runs_avg', label: 'Last 5 Avg' },
    { key: 'player_last5_strike_rate', label: 'Last 5 SR' },
    { key: 'predicted_runs', label: 'Predicted Runs' },
  ]
  const bowlCols = [
    { key: 'player', label: 'Player', bold: true },
    { key: 'player_last5_wickets', label: 'Last 5 Wkts' },
    { key: 'player_last5_economy', label: 'Last 5 Econ' },
    { key: 'predicted_wickets', label: 'Predicted Wkts' },
  ]
  const xiCols = [
    { key: 'player', label: 'Player', bold: true },
    { key: 'player_last5_runs_avg', label: 'Runs Avg' },
    { key: 'player_last5_wickets', label: 'Wickets' },
    { key: 'player_last5_economy', label: 'Economy' },
    { key: 'score', label: 'Score' },
  ]
  const ocCols = [
    { key: 'player', label: 'Player', bold: true },
    { key: 'team', label: 'Team' },
    { key: 'player_last5_runs_avg', label: 'Runs Avg' },
    { key: 'player_last5_strike_rate', label: 'SR' },
  ]
  const pcCols = [
    { key: 'player', label: 'Player', bold: true },
    { key: 'team', label: 'Team' },
    { key: 'player_last5_wickets', label: 'Wickets Avg' },
    { key: 'player_last5_economy', label: 'Economy' },
  ]

  return (
    <div className="fade-in">
      <h1 className="page-title">🏏 Player <span>Intelligence</span></h1>
      <p className="page-lead">Predict top performers, build the Best XI, track leaderboards and compare squad strengths.</p>

      <div className="tabs">
        {TABS.map((t, i) => (
          <button key={t} className={`tab${tab === i ? ' active' : ''}`} onClick={() => { setTab(i); setError('') }}>{t}</button>
        ))}
      </div>

      {error && <div className="banner banner-error" style={{ marginBottom: '1rem' }}>{error}</div>}

      {/* ── Tab 0: Performance Predictions ── */}
      {tab === 0 && (
        <div className="fade-in">
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="section-title">Configure Matchup</div>
            <div className="form-row">
              <div className="form-group">
                <label>Team</label>
                <select value={ppTeam} onChange={e => { setPpTeam(e.target.value); setPpResult(null) }}>
                  {teams.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Opponent</label>
                <select value={ppOpp} onChange={e => { setPpOpp(e.target.value); setPpResult(null) }}>
                  {teams.filter(t => t !== ppTeam).map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Venue (optional)</label>
                <select value={ppVenue} onChange={e => setPpVenue(e.target.value)}>
                  <option value="">Any venue</option>
                  {venues.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>
            <button className="btn-primary" onClick={fetchPerformance} disabled={ppLoading}>
              {ppLoading ? 'Predicting…' : '🎯 Predict Player Performance'}
            </button>
          </div>
          {ppLoading && <Spinner text="Analysing player data…" />}
          {ppResult && (
            <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div className="card">
                <div className="section-title">🏏 Top Predicted Batters — {ppResult.team}</div>
                <DataTable rows={ppResult.batters} cols={batCols} />
              </div>
              <div className="card">
                <div className="section-title">🎳 Top Predicted Bowlers — {ppResult.team}</div>
                <DataTable rows={ppResult.bowlers} cols={bowlCols} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Tab 1: Best XI ── */}
      {tab === 1 && (
        <div className="fade-in">
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="section-title">Select Team</div>
            <div className="form-row" style={{ alignItems: 'flex-end' }}>
              <div className="form-group">
                <label>Team</label>
                <select value={xiTeam} onChange={e => { setXiTeam(e.target.value); setXiResult(null) }}>
                  {teams.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <button className="btn-primary" onClick={fetchBestXI} disabled={xiLoading}>
                {xiLoading ? 'Building…' : '🏆 Build Best XI'}
              </button>
            </div>
          </div>
          {xiLoading && <Spinner text="Building Best XI…" />}
          {xiResult && (
            <div className="fade-in">
              <div className="card" style={{ marginBottom: '1.25rem' }}>
                <div className="section-title">🏆 Best XI — {xiResult.team}</div>
                <DataTable rows={xiResult.xi} cols={xiCols} />
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
                  Score = 0.5 × Runs Avg + 0.3 × Wickets − 0.2 × Economy. Top 11 selected.
                </div>
              </div>
              <div className="card">
                <div className="section-title">📊 Selection Scores</div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={[...xiResult.xi].reverse().map(p => ({ name: p.player.split(' ').pop(), score: Number(p.score?.toFixed(2)) }))} layout="vertical">
                    <XAxis type="number" stroke="#8b9bb4" />
                    <YAxis dataKey="name" type="category" stroke="#8b9bb4" width={90} tick={{ fontSize: 11 }} />
                    <Tooltip content={<CTip />} />
                    <Bar dataKey="score" fill="#7c3aed" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Tab 2: Leaders ── */}
      {tab === 2 && (
        <div className="fade-in">
          {ldLoading && <Spinner text="Computing season leaders…" />}
          {leaders && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div>
                <div className="card" style={{ marginBottom: '1.25rem' }}>
                  <div className="section-title">🟠 Orange Cap — Top Run Scorers</div>
                  <DataTable rows={leaders.orange_cap} cols={ocCols} />
                </div>
                <div className="card">
                  <div className="section-title">📊 Orange Cap Chart</div>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={[...leaders.orange_cap].reverse().map(p => ({ name: p.player.split(' ').pop(), runs: Number(p.player_last5_runs_avg?.toFixed(1)) }))} layout="vertical">
                      <XAxis type="number" stroke="#8b9bb4" />
                      <YAxis dataKey="name" type="category" stroke="#8b9bb4" width={80} tick={{ fontSize: 10 }} />
                      <Tooltip content={<CTip />} />
                      <Bar dataKey="runs" fill="#ff6b35" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div>
                <div className="card" style={{ marginBottom: '1.25rem' }}>
                  <div className="section-title">🟣 Purple Cap — Top Wicket Takers</div>
                  <DataTable rows={leaders.purple_cap} cols={pcCols} />
                </div>
                <div className="card">
                  <div className="section-title">📊 Purple Cap Chart</div>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={[...leaders.purple_cap].reverse().map(p => ({ name: p.player.split(' ').pop(), wickets: Number(p.player_last5_wickets?.toFixed(2)) }))} layout="vertical">
                      <XAxis type="number" stroke="#8b9bb4" />
                      <YAxis dataKey="name" type="category" stroke="#8b9bb4" width={80} tick={{ fontSize: 10 }} />
                      <Tooltip content={<CTip />} />
                      <Bar dataKey="wickets" fill="#7c3aed" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Tab 3: Squad Strength ── */}
      {tab === 3 && (
        <div className="fade-in">
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="section-title">Compare Two Squads</div>
            <div className="form-row" style={{ alignItems: 'flex-end' }}>
              <div className="form-group">
                <label>Team A</label>
                <select value={sqA} onChange={e => { setSqA(e.target.value); setSqResult(null) }}>
                  {teams.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Team B</label>
                <select value={sqB} onChange={e => { setSqB(e.target.value); setSqResult(null) }}>
                  {teams.filter(t => t !== sqA).map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <button className="btn-primary" onClick={fetchSquad} disabled={sqLoading}>
                {sqLoading ? 'Comparing…' : '⚖️ Compare Squads'}
              </button>
            </div>
          </div>
          {sqLoading && <Spinner text="Analysing squads…" />}
          {sqResult && (() => {
            const dA = sqResult.data[sqResult.team_a]
            const dB = sqResult.data[sqResult.team_b]
            const metrics = ['batting_strength', 'bowling_strength', 'avg_strike_rate', 'avg_economy']
            const labels  = ['Batting Strength', 'Bowling Strength', 'Avg Strike Rate', 'Avg Economy']
            return (
              <div className="fade-in">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(200px,1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                  {metrics.map((m, i) => (
                    <div key={m} className="card">
                      <div className="card-title">{labels[i]}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                        <div style={{ textAlign: 'center', flex: 1 }}>
                          <div style={{ fontFamily: 'Outfit', fontSize: '1.5rem', fontWeight: 800, color: '#7c3aed' }}>{dA[m]}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{sqResult.team_a}</div>
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontWeight: 700 }}>vs</div>
                        <div style={{ textAlign: 'center', flex: 1 }}>
                          <div style={{ fontFamily: 'Outfit', fontSize: '1.5rem', fontWeight: 800, color: '#ff6b35' }}>{dB[m]}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{sqResult.team_b}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="card">
                  <div className="section-title">📊 Squad Comparison Chart</div>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={metrics.map((m, i) => ({ metric: labels[i], [sqResult.team_a]: dA[m], [sqResult.team_b]: dB[m] }))} barCategoryGap="30%">
                      <XAxis dataKey="metric" stroke="#8b9bb4" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#8b9bb4" />
                      <Tooltip content={<CTip />} />
                      <Legend />
                      <Bar dataKey={sqResult.team_a} fill="#7c3aed" radius={[6, 6, 0, 0]} />
                      <Bar dataKey={sqResult.team_b} fill="#ff6b35" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}
