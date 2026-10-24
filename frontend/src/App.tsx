import { useCallback, useEffect, useState } from 'react'
import {
  api,
  type BenchmarkRow,
  type Health,
  type InstanceData,
  type ResultOut,
} from './services/api'
import GateGrid from './components/GateGrid'

function MatrixTable({ title, M, sym }: { title: string; M: number[][]; sym?: boolean }) {
  const n = M.length
  const val = (i: number, j: number) => (sym && i > j ? M[j][i] : M[i][j])
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="table-scroll">
        <table className="matrix">
          <thead>
            <tr>
              <th />
              {Array.from({ length: n }, (_, j) => (
                <th key={j}>P{j + 1}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {M.map((_, i) => (
              <tr key={i}>
                <th>V{i + 1}</th>
                {M[i].map((_, j) => (
                  <td key={j} className={val(i, j) > 0 ? 'pos' : 'zero'}>
                    {val(i, j)}
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

const fmt = (v: string | undefined, digits = 2) => {
  const num = Number(v)
  return Number.isFinite(num) && v !== '' ? num.toFixed(digits) : '—'
}
const pct = (v: string | undefined) => {
  const num = Number(v)
  return Number.isFinite(num) && v !== '' ? `${(num * 100).toFixed(1)} %` : '—'
}

function Day1Results() {
  const [rows, setRows] = useState<BenchmarkRow[] | null>(null)
  useEffect(() => {
    api.comparison().then(setRows).catch(() => setRows([]))
  }, [])
  if (rows === null) return null
  return (
    <section className="card" id="resultados">
      <h2>Resultados del Día 1 (con commit, no en vivo)</h2>
      {rows.length === 0 ? (
        <p className="muted">results/comparison.csv aún no existe en esta imagen.</p>
      ) : (
        <>
          <div className="table-scroll">
            <table className="data">
              <thead>
                <tr>
                  <th>N</th>
                  <th>Método</th>
                  <th>Configuración</th>
                  <th>Mejor coste</th>
                  <th>Coste medio</th>
                  <th>% óptimo alcanzado</th>
                  <th>Tiempo medio (s)</th>
                  <th>Fracción factible</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, idx) => (
                  <tr key={idx}>
                    <td>{r.n}</td>
                    <td>{r.method}</td>
                    <td className="mono">{r.config}</td>
                    <td>{fmt(r.best_cost, 0)}</td>
                    <td>{fmt(r.mean_cost, 1)}</td>
                    <td>{pct(r.reached_optimum_rate)}</td>
                    <td>{fmt(r.mean_seconds)}</td>
                    <td>{pct(r.feasible_fraction)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">
            Comparación clásico vs Qiskit con las métricas del reto (gap vs control
            C*=340, fracción factible vs piso aleatorio, IC de Wilson). Ejecuciones
            registradas con semilla y parámetros en <code>results/</code>.
          </p>
        </>
      )}
    </section>
  )
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [n, setN] = useState(4)
  const [inst, setInst] = useState<InstanceData | null>(null)
  const [result, setResult] = useState<ResultOut | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'AeroQ Optimizer — panel'
    api.health().then(setHealth).catch((e) => setError(String(e.message ?? e)))
    if (window.location.hash === '#resultados') {
      setTimeout(() => {
        document.getElementById('resultados')?.scrollIntoView({ behavior: 'smooth' })
      }, 300)
    }
  }, [])

  useEffect(() => {
    setInst(null)
    setResult(null)
    api
      .instance(n)
      .then(setInst)
      .catch((e) => setError(String(e.message ?? e)))
  }, [n])

  const runSolver = useCallback(() => {
    setRunning(true)
    setError(null)
    api
      .classical(n)
      .then(setResult)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setRunning(false))
  }, [n])

  return (
    <main className="page">
      <header className="hero">
        <a className="back" href="/">← Portada</a>
        <h1>AeroQ Optimizer</h1>
        <p className="tagline">
          Menos minutos caminando para los pasajeros en conexión — comparación
          rigurosa entre clásico y cuántico sobre la asignación de puertas.
        </p>
        <p className="team">Equipo The Explorers · Qiskit Fall Fest 2026</p>
        {health ? (
          <span className="badge ok">
            Backend OK · qiskit {health.qiskit} · bd {health.db}
          </span>
        ) : (
          <span className="badge warn">Backend no disponible</span>
        )}
      </header>

      {error && (
        <div className="banner error" role="alert">
          {error}
        </div>
      )}

      <section className="controls card">
        <h2>Instancia</h2>
        <div className="row">
          {[3, 4, 10].map((v) => (
            <button
              key={v}
              className={v === n ? 'chip active' : 'chip'}
              onClick={() => setN(v)}
            >
              N = {v} {v === 10 ? '(completo)' : '(reducida)'}
            </button>
          ))}
          <button className="run" onClick={runSolver} disabled={running || !inst}>
            {running ? 'Ejecutando…' : `Ejecutar solver exacto (N=${n}${n === 10 ? ', ≈ 4 s' : ''})`}
          </button>
        </div>
        {inst && (
          <p className="muted">
            {inst.name} · óptimo de referencia: {inst.optimum ?? '—'}{' '}
            (verificado por búsqueda exacta)
          </p>
        )}
      </section>

      {result && (
        <section className="card">
          <h2>Resultado — {result.method}</h2>
          <div className="row stats">
            <span className={result.feasible ? 'badge ok' : 'badge warn'}>
              {result.feasible ? 'Factible' : 'No factible'}
            </span>
            <span className="badge">{result.reference_kind === 'proven_optimum' ? 'Óptimo demostrado' : 'Mejor encontrado'}</span>
            <strong className="cost">Coste total: {result.cost}</strong>
            <span>tiempo medido: {result.seconds.toFixed(3)} s</span>
            {result.gap_pct !== null && <span>gap: {result.gap_pct.toFixed(2)} %</span>}
          </div>
          <table className="assign">
            <thead>
              <tr>
                <th>Vuelo</th>
                <th>Puerta</th>
              </tr>
            </thead>
            <tbody>
              {result.assignment.map((a) => (
                <tr key={a.flight}>
                  <td>V{a.flight + 1}</td>
                  <td>P{a.gate + 1}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {inst && (
        <>
          <GateGrid inst={inst} result={result} />
          <section className="grid2">
            <MatrixTable title="Flujo de pasajeros F (simetrizado)" M={inst.F} sym />
            <MatrixTable title="Distancia entre puertas D" M={inst.D} />
          </section>
        </>
      )}

      <Day1Results />

      <footer className="footer">
        Las unidades y las conclusiones operativas son supuestos, no mediciones ·
        cada coste se recalcula con el objetivo original (cada par de vuelos una vez).
      </footer>
    </main>
  )
}
