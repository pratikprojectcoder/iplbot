import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/',             icon: '🏠', label: 'Home' },
  { to: '/scorecard',   icon: '📋', label: 'Scorecard Explainer' },
  { to: '/predict',     icon: '🔮', label: 'Match Predictor' },
  { to: '/players',     icon: '🏏', label: 'Player Intelligence' },
  { to: '/hand-cricket',icon: '🎮', label: 'Hand Cricket' },
]

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">🏏 IPL Bot</div>
        <div className="brand-sub">AI Cricket Intelligence · IPL 2026</div>

        <div className="nav-section">Navigation</div>
        {navItems.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
          >
            <span className="nav-icon">{icon}</span>
            {label}
          </NavLink>
        ))}

        <div className="sidebar-footer">
          Powered by FastAPI + React
        </div>
      </aside>

      <main className="main fade-in">
        <Outlet />
      </main>
    </div>
  )
}
