import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import StatCard from '../components/StatCard'

const features = [
  {
    to: '/scorecard',
    icon: '',
    title: 'Scorecard Explainer',
    desc: 'Deep-dive into any IPL match. View batting & bowling scorecards, phase analysis, momentum charts and AI-generated commentary.',
    color: '#7c3aed',
  },
  {
    to: '/predict',
    icon: '',
    title: 'Match Outcome Predictor',
    desc: 'Our ML model predicts win probabilities based on head-to-head records, venue stats, recent form and toss impact.',
    color: '#f4d03f',
  },
  {
    to: '/players',
    icon: '',
    title: 'Player Intelligence',
    desc: 'Explore top batters & bowlers, build the Best XI, view Orange & Purple Cap leaderboards and compare squad strengths.',
    color: '#ff6b35',
  },
  {
    to: '/hand-cricket',
    icon: '',
    title: 'Hand Cricket',
    desc: 'Play the classic hand-cricket game against the computer as your favourite IPL team. Includes toss, innings break & full scorecard.',
    color: '#10b981',
  },
]

export default function Home() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    axios.get('/api/stats').then(r => setStats(r.data)).catch(() => {})
  }, [])

  return (
    <div className="fade-in">
      {/* Hero */}
      <section className="hero">
        <div className="hero-badge">IPL 2026 · Powered by AI</div>
        <h1 className="hero-title">
          Your Ultimate<br />
          <span className="gold">IPL Intelligence</span><br />
          Platform
        </h1>
        <p className="hero-sub">
          Predict match outcomes, analyse player performance, explore scorecards and
          play Hand Cricket — all in one beautiful dashboard.
        </p>
      </section>

      {/* Live stats */}
      {stats && (
        <div className="stats-row" style={{ marginBottom: '2.5rem' }}>
          <StatCard title="Total Matches" value={stats.total_matches.toLocaleString()} sub="in our database" />
          <StatCard title="IPL Teams"     value={stats.total_teams}    sub="all franchises" color="#f4d03f" />
          <StatCard title="Venues"        value={stats.total_venues}   sub="grounds tracked" color="#ff6b35" />
          <StatCard title="Seasons"       value={stats.seasons}        sub="years of data"  color="#7c3aed" />
        </div>
      )}

      {/* Feature cards */}
      <h2 style={{ fontFamily: 'Outfit', fontSize: '1.2rem', fontWeight: 700, marginBottom: '1.25rem', color: 'var(--text-muted)' }}>
        EXPLORE FEATURES
      </h2>
      <div className="grid-2" style={{ gap: '1.25rem', gridTemplateColumns: 'repeat(auto-fill,minmax(260px,1fr))' }}>
        {features.map(f => (
          <Link key={f.to} to={f.to} className="feature-card" style={{ textDecoration: 'none' }}>
            <div className="feature-icon" style={{ filter: `drop-shadow(0 0 12px ${f.color}66)` }}>{f.icon}</div>
            <div className="feature-title">{f.title}</div>
            <div className="feature-desc">{f.desc}</div>
            <div className="feature-arrow">Explore →</div>
          </Link>
        ))}
      </div>

      {/* Footer note */}
      <div style={{ marginTop: '3rem', padding: '1.25rem', background: 'var(--bg-panel)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
         <strong style={{ color: 'var(--text)' }}>How it works:</strong> The FastAPI backend exposes ML models trained on historical IPL data.
        The React frontend calls these endpoints to display predictions, scorecards and player analytics in real time.
        The Streamlit app (<code>app.py</code>) continues to work independently.
      </div>
    </div>
  )
}
