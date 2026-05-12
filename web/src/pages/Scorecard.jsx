import { useEffect, useState, useMemo } from 'react'
import axios from 'axios'
import Spinner from '../components/Spinner'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, CartesianGrid
} from 'recharts'

function uniq(arr) { return [...new Set(arr.filter(Boolean))] }

function ScorecardTable({ title, rows, cols }) {
  if (!rows?.length) return null
  return (
    <div className="section">
      <div className="section-title">{title}</div>
      <div className="table-wrap">
        <table>
          <thead><tr>{cols.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {cols.map(c => (
                  <td key={c.key} style={c.bold ? { fontWeight: 700, color: 'var(--text)' } : {}}>
                    {r[c.key] ?? '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const batCols = [
  { key: 'batter', label: 'Batter', bold: true },
  { key: 'dismissal', label: 'Dismissal' },
  { key: 'runs', label: 'R' },
  { key: 'balls', label: 'B' },
  { key: 'fours', label: '4s' },
  { key: 'sixes', label: '6s' },
  { key: 'sr', label: 'SR' },
]
const bowlCols = [
  { key: 'bowler', label: 'Bowler', bold: true },
  { key: 'overs', label: 'O' },
  { key: 'runs', label: 'R' },
  { key: 'wickets', label: 'W' },
  { key: 'economy', label: 'Econ' },
]

const CTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 10, padding: '0.6rem 0.9rem', fontSize: '0.82rem' }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      {payload.map(p => <div key={p.name} style={{ color: p.color, fontWeight: 700 }}>{p.name}: {p.value}</div>)}
    </div>
  )
}

export default function Scorecard() {
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [season, setSeason] = useState('')
  const [teamA, setTeamA] = useState('')
  const [opponent, setOpponent] = useState('')
  const [venue, setVenue] = useState('')
  const [matchId, setMatchId] = useState('')
  const [scorecard, setScorecard] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [scLoading, setScLoading] = useState(false)
  const [anLoading, setAnLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    axios.get('/api/match-index').then(r => { setMatches(r.data.matches || []); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const seasons = useMemo(() => uniq(matches.map(m => m.season)).sort((a, b) => b - a), [matches])
  const seasonMatches = useMemo(() => matches.filter(m => !season || String(m.season) === String(season)), [matches, season])
  const teams = useMemo(() => uniq([...seasonMatches.map(m => m.team_a), ...seasonMatches.map(m => m.team_b)]).sort(), [seasonMatches])
  const teamMatches = useMemo(() => seasonMatches.filter(m => !teamA || m.team_a === teamA || m.team_b === teamA), [seasonMatches, teamA])
  const opponents = useMemo(() => uniq(teamMatches.map(m => m.team_a === teamA ? m.team_b : m.team_a)).sort(), [teamMatches, teamA])
  const filteredByOpp = useMemo(() => teamMatches.filter(m => !opponent || m.team_a === opponent || m.team_b === opponent), [teamMatches, opponent])
  const venues = useMemo(() => uniq(filteredByOpp.map(m => m.venue)).sort(), [filteredByOpp])
  const finalMatches = useMemo(() => filteredByOpp.filter(m => !venue || m.venue === venue), [filteredByOpp, venue])

  useEffect(() => { if (teams.length && !teams.includes(teamA)) { setTeamA(teams[0]); setOpponent(''); setVenue('') } }, [teams])
  useEffect(() => { if (opponents.length && !opponents.includes(opponent)) setOpponent(opponents[0]) }, [opponents])
  useEffect(() => { if (venues.length && !venues.includes(venue)) setVenue(venues[0]) }, [venues])
  useEffect(() => { if (finalMatches.length) setMatchId(String(finalMatches[0].match_id)) }, [finalMatches])

  async function loadScorecard() {
    if (!matchId) return
    setScLoading(true); setError(''); setScorecard(null); setAnalysis(null)
    try { const r = await axios.get(`/api/scorecard/${matchId}`); setScorecard(r.data) }
    catch (e) { setError(e.response?.data?.detail || 'Failed to load scorecard') }
    finally { setScLoading(false) }
  }

  async function loadAnalysis() {
    if (!matchId) return
    setAnLoading(true)
    try { const r = await axios.post(`/api/analyze-match/${matchId}`); setAnalysis(r.data) }
    catch (e) { setError(e.response?.data?.detail || 'Analysis failed') }
    finally { setAnLoading(false) }
  }

  if (loading) return <Spinner text="Loading match index…" />

  return (
    <div className="fade-in">
      <h1 className="page-title">📋 Scorecard <span>Explainer</span></h1>
      <p className="page-lead">Select a match to view the full scorecard, phase analysis and momentum tracker.</p>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="form-row">
          <div className="form-group">
            <label>Season</label>
            <select value={season} onChange={e => { setSeason(e.target.value); setTeamA(''); setOpponent(''); setVenue('') }}>
              <option value="">All seasons</option>
              {seasons.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Team</label>
            <select value={teamA} onChange={e => { setTeamA(e.target.value); setOpponent(''); setVenue('') }}>
              <option value="">Select team</option>
              {teams.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Opponent</label>
            <select value={opponent} onChange={e => { setOpponent(e.target.value); setVenue('') }} disabled={!teamA}>
              <option value="">Select opponent</option>
              {opponents.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Venue</label>
            <select value={venue} onChange={e => setVenue(e.target.value)} disabled={!opponent}>
              <option value="">All venues</option>
              {venues.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
        </div>
        {finalMatches.length > 0 && (
          <div className="form-row" style={{ alignItems: 'flex-end' }}>
            <div className="form-group" style={{ flex: 2 }}>
              <label>Match</label>
              <select value={matchId} onChange={e => setMatchId(e.target.value)}>
                {finalMatches.map(m => (
                  <option key={m.match_id} value={m.match_id}>
                    {m.date?.slice(0, 10)} | {m.team_a} vs {m.team_b} | {m.venue}
                  </option>
                ))}
              </select>
            </div>
            <button className="btn-primary" onClick={loadScorecard} disabled={scLoading || !matchId}>
              {scLoading ? 'Loading…' : '📋 Load Scorecard'}
            </button>
          </div>
        )}
        {!finalMatches.length && teamA && <div className="banner banner-warning" style={{ marginBottom: 0 }}>No matches found for these filters.</div>}
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {scLoading && <Spinner text="Loading scorecard…" />}

      {scorecard && (
        <div className="fade-in">
          {scorecard.outcome?.winner && (
            <div className="banner" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.5rem' }}>🏆</span>
              <div>
                <div style={{ fontWeight: 700, color: 'var(--gold)', fontFamily: 'Outfit', fontSize: '1.05rem' }}>
                  {scorecard.outcome.winner} won{Object.entries(scorecard.outcome.by || {}).map(([k, v]) => ` by ${v} ${k}`)}
                </div>
                {scorecard.toss?.winner && (
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                    Toss: {scorecard.toss.winner} chose to {scorecard.toss.decision}
                  </div>
                )}
              </div>
            </div>
          )}

          {scorecard.innings?.map((inn, idx) => (
            <div key={idx} className="card fade-in" style={{ marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                  <div style={{ fontFamily: 'Outfit', fontSize: '1.1rem', fontWeight: 800 }}>Innings {idx + 1} — {inn.team}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>{inn.total_runs}/{inn.total_wickets} ({inn.overs_bowled} ov)</div>
                </div>
                <div style={{ fontFamily: 'Outfit', fontSize: '2.2rem', fontWeight: 900, color: 'var(--gold)' }}>{inn.total_runs}/{inn.total_wickets}</div>
              </div>
              <ScorecardTable title="🏏 Batting" rows={inn.batting} cols={batCols} />
              <ScorecardTable title="🎳 Bowling" rows={inn.bowling} cols={bowlCols} />
            </div>
          ))}

          <div style={{ display: 'flex', justifyContent: 'center', margin: '1.5rem 0' }}>
            <button className="btn-primary" onClick={loadAnalysis} disabled={anLoading}>
              {anLoading ? '⚡ Analysing…' : '⚡ Generate Match Analysis'}
            </button>
          </div>
          {anLoading && <Spinner text="Computing analysis…" />}
        </div>
      )}

      {analysis && (
        <div className="fade-in">
          <div className="banner" style={{ textAlign: 'center', fontFamily: 'Outfit', fontWeight: 700, fontSize: '1.05rem', marginBottom: '1.5rem' }}>
            🏆 {analysis.winner} won by {analysis.margin} runs
          </div>

          <div className="card" style={{ marginBottom: '1.25rem' }}>
            <div className="section-title">📊 Phase Comparison — Runs</div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={['powerplay', 'middle', 'death'].map(ph => ({
                phase: ph.charAt(0).toUpperCase() + ph.slice(1),
                [analysis.team_a]: analysis.team_a_phases[ph]?.runs ?? 0,
                [analysis.team_b]: analysis.team_b_phases[ph]?.runs ?? 0,
              }))} barCategoryGap="30%">
                <XAxis dataKey="phase" stroke="#8b9bb4" />
                <YAxis stroke="#8b9bb4" />
                <Tooltip content={<CTip />} />
                <Legend />
                <Bar dataKey={analysis.team_a} fill="#7c3aed" radius={[6, 6, 0, 0]} />
                <Bar dataKey={analysis.team_b} fill="#ff6b35" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card" style={{ marginBottom: '1.25rem' }}>
            <div className="section-title">📈 Momentum Tracker</div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="over" type="number" domain={['dataMin', 'dataMax']} stroke="#8b9bb4" />
                <YAxis stroke="#8b9bb4" />
                <Tooltip content={<CTip />} />
                <Legend />
                <Line data={analysis.team_a_momentum} dataKey="momentum" name={analysis.team_a} stroke="#7c3aed" strokeWidth={2.5} dot={false} />
                <Line data={analysis.team_b_momentum} dataKey="momentum" name={analysis.team_b} stroke="#ff6b35" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <div className="section-title">🎯 Win Probability</div>
            <div style={{ maxWidth: 520, margin: '0 auto' }}>
              {[['team_a', '#7c3aed'], ['team_b', '#ff6b35']].map(([key, color]) => (
                <div key={key} className="prob-container">
                  <div className="prob-label"><strong>{analysis[key]}</strong><span>{analysis.win_probability[key]}%</span></div>
                  <div className="prob-track" style={{ height: 14 }}>
                    <div style={{ height: '100%', width: `${analysis.win_probability[key]}%`, background: color, borderRadius: 999, transition: 'width 0.8s' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
