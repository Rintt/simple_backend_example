import { useEffect, useState } from 'react'
import { api, simPath, statsPath } from './api'
import { format } from './format'
import BarChart from './components/BarChart'
import CheckboxGroup from './components/CheckboxGroup'
import './App.css'

const ATTRIBUTES = ['pressure', 'velocity']
const STATS = ['min', 'max', 'average', 'median', 'p95']

export default function App() {
  const [token, setToken] = useState('')
  const [user, setUser] = useState('0')
  const [simulations, setSimulations] = useState([])
  const [simulation, setSimulation] = useState('')
  const [outputs, setOutputs] = useState([])
  const [parts, setParts] = useState([])
  const [selectedOutputs, setSelectedOutputs] = useState([])
  const [selectedParts, setSelectedParts] = useState([])
  const [attribute, setAttribute] = useState('velocity')
  const [stat, setStat] = useState('max')
  const [result, setResult] = useState(null)
  const [perOutput, setPerOutput] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Changing the token, user or simulation clears everything that depended on it;
  // the effects below then load the new data.
  function changeToken(value) {
    setToken(value)
    clearUserData()
  }

  function changeUser(value) {
    setUser(value)
    clearUserData()
  }

  function clearUserData() {
    setSimulations([])
    setError('')
    changeSimulation('')
  }

  function changeSimulation(value) {
    setSimulation(value)
    setOutputs([])
    setParts([])
    setSelectedOutputs([])
    setSelectedParts([])
    setResult(null)
    setPerOutput([])
  }

  // token + user -> simulations
  useEffect(() => {
    if (!user || !token) return
    let cancelled = false
    api(`/users/${encodeURIComponent(user)}/simulations`, token)
      .then((sims) => {
        if (cancelled) return
        setSimulations(sims)
        setSimulation(sims[0] ?? '')
      })
      .catch((e) => !cancelled && setError(e.message))
    return () => {
      cancelled = true
    }
  }, [user, token])

  // simulation -> outputs + parts
  useEffect(() => {
    if (!simulation) return
    let cancelled = false
    const base = simPath(user, simulation)
    Promise.all([api(`${base}/outputs`, token), api(`${base}/parts`, token)])
      .then(([outs, prts]) => {
        if (cancelled) return
        setOutputs(outs)
        setParts(prts)
        setSelectedOutputs(outs)
        setSelectedParts(prts.slice(0, 1))
      })
      .catch((e) => !cancelled && setError(e.message))
    return () => {
      cancelled = true
    }
  }, [user, simulation, token])

  async function compute() {
    setLoading(true)
    setError('')
    setResult(null)
    setPerOutput([])
    const params = { attribute, stat, outputs: selectedOutputs, parts: selectedParts }
    try {
      // pooled result + the same statistic for each output on its own (for the chart)
      const [total, ...each] = await Promise.all([
        api(statsPath(user, simulation, params), token),
        ...selectedOutputs.map((o) => api(statsPath(user, simulation, { ...params, outputs: [o] }), token)),
      ])
      setResult(total)
      setPerOutput(each)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h1>Diver's License statistics</h1>

      <section className="form">
        <label>
          API token
          <input
            type="password"
            value={token}
            placeholder="create one with: python -m backend.auth <user>"
            onChange={(e) => changeToken(e.target.value.trim())}
          />
        </label>

        <label>
          User
          <input value={user} onChange={(e) => changeUser(e.target.value.trim())} />
        </label>

        <label>
          Simulation
          <select value={simulation} onChange={(e) => changeSimulation(e.target.value)}>
            {simulations.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>

        <CheckboxGroup legend="Outputs" options={outputs} selected={selectedOutputs} onChange={setSelectedOutputs} />
        <CheckboxGroup legend="Parts" options={parts} selected={selectedParts} onChange={setSelectedParts} />

        <label>
          Attribute
          <select value={attribute} onChange={(e) => setAttribute(e.target.value)}>
            {ATTRIBUTES.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </label>

        <label>
          Statistic
          <select value={stat} onChange={(e) => setStat(e.target.value)}>
            {STATS.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>

        <button onClick={compute} disabled={loading || !selectedOutputs.length || !selectedParts.length}>
          {loading ? 'Computing…' : 'Compute'}
        </button>
      </section>

      {error && <p className="error">{error}</p>}

      {result && (
        <section className="result">
          <div className="value">{format(result.value)}</div>
          <p>
            {result.stat} of {result.attribute}
            {result.attribute === 'velocity' && ' (magnitude)'} over {result.parts.join(', ')}, outputs{' '}
            {result.outputs.join(', ')}
          </p>
          <p className="meta">{result.count.toLocaleString()} values</p>
          {perOutput.length > 1 && (
            <>
              <h2>{result.stat} per output</h2>
              <BarChart rows={perOutput} />
            </>
          )}
        </section>
      )}
    </main>
  )
}
