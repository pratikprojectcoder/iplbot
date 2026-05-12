export default function Spinner({ text = 'Loading…' }) {
  return (
    <div className="spinner-wrap">
      <div className="spinner" />
      <div className="spinner-text">{text}</div>
    </div>
  )
}
