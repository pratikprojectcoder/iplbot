export default function ProbBar({ teamA, teamB, probA, probB }) {
  return (
    <div className="prob-container">
      <div className="prob-label">
        <strong>{teamA}</strong>
        <span>{probA}%</span>
      </div>
      <div className="prob-track" style={{ marginBottom: '0.75rem' }}>
        <div className="prob-fill prob-fill-a" style={{ width: `${probA}%` }} />
      </div>
      <div className="prob-label">
        <strong>{teamB}</strong>
        <span>{probB}%</span>
      </div>
      <div className="prob-track">
        <div className="prob-fill prob-fill-b" style={{ width: `${probB}%` }} />
      </div>
    </div>
  )
}
