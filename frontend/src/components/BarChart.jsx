import { format } from '../format'

// One bar per output; negative values are drawn in a different colour
export default function BarChart({ rows }) {
  const max = Math.max(...rows.map((r) => Math.abs(r.value)), Number.EPSILON)
  return (
    <div className="chart">
      {rows.map((r) => (
        <div key={r.outputs[0]} className="bar-row">
          <span className="bar-label">output {r.outputs[0]}</span>
          <div className="bar-track">
            <div
              className={r.value < 0 ? 'bar negative' : 'bar'}
              style={{ width: `${(Math.abs(r.value) / max) * 100}%` }}
            />
          </div>
          <span className="bar-value">{format(r.value)}</span>
        </div>
      ))}
    </div>
  )
}
