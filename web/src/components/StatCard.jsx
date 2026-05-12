export default function StatCard({ title, value, sub, color }) {
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <div className="card-value" style={color ? { color } : {}}>{value}</div>
      {sub && <div className="card-sub">{sub}</div>}
    </div>
  )
}
