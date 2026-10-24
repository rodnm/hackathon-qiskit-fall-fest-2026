import type { InstanceData, ResultOut } from '../services/api'

interface Props {
  inst: InstanceData
  result: ResultOut | null
}

const CELL = 64
const PAD = 24

/**
 * Mapa de la cuadrícula de puertas (S10): 4 columnas, distancia Manhattan.
 * Las aristas muestran los flujos entre puertas asignadas; grosor ∝ pasajeros,
 * intensidad ∝ contribución al coste (F × distancia). Top-5 contribuciones resaltadas.
 */
export default function GateGrid({ inst, result }: Props) {
  const n = inst.n
  const perm = result?.perm ?? null
  const rows = Math.ceil(n / 4)
  const width = PAD * 2 + 4 * CELL
  const height = PAD * 2 + rows * CELL

  const center = (gate: number) => {
    const c = inst.layout[gate]
    return { x: PAD + c.col * CELL + CELL / 2, y: PAD + c.row * CELL + CELL / 2 }
  }

  const edges: { i: number; k: number; f: number; d: number; c: number; top: boolean }[] = []
  if (perm) {
    const raw: { i: number; k: number; f: number; d: number; c: number }[] = []
    for (let i = 0; i < n; i++) {
      for (let k = i + 1; k < n; k++) {
        const f = inst.F[i][k]
        if (f > 0) {
          const d = inst.D[perm[i]][perm[k]]
          raw.push({ i, k, f, d, c: f * d })
        }
      }
    }
    const top = new Set(
      [...raw].sort((a, b) => b.c - a.c).slice(0, 5).map((e) => `${e.i}-${e.k}`),
    )
    raw.forEach((e) => edges.push({ ...e, top: top.has(`${e.i}-${e.k}`) }))
  }
  const maxC = Math.max(1, ...edges.map((e) => e.c))
  const maxF = Math.max(1, ...inst.F.flat())

  const flightAtGate = new Map<number, number>()
  if (perm) perm.forEach((gate, flight) => flightAtGate.set(gate, flight))

  return (
    <section className="card">
      <h2>Mapa de puertas (cuadrícula de 4 columnas — supuesto de diseño)</h2>
      <svg viewBox={`0 0 ${width} ${height}`} className="gategrid" role="img">
        {perm &&
          edges.map((e) => {
            const a = center(perm[e.i])
            const b = center(perm[e.k])
            const intensity = 0.25 + 0.75 * (e.c / maxC)
            return (
              <line
                key={`${e.i}-${e.k}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={e.top ? '#c2410c' : '#64748b'}
                strokeOpacity={e.top ? intensity : 0.35 * intensity}
                strokeWidth={1 + 5 * (e.f / maxF)}
                strokeLinecap="round"
              >
                <title>
                  {`V${e.i + 1}–V${e.k + 1}: F=${e.f}, d=${e.d}, contribución=${e.c}${e.top ? ' (top 5)' : ''}`}
                </title>
              </line>
            )
          })}
        {inst.layout.map((c) => {
          const flight = flightAtGate.get(c.gate)
          return (
            <g key={c.gate} transform={`translate(${PAD + c.col * CELL}, ${PAD + c.row * CELL})`}>
              <rect
                width={CELL - 8}
                height={CELL - 8}
                rx={10}
                className={flight !== undefined ? 'cell assigned' : 'cell'}
              />
              <text x={(CELL - 8) / 2} y={(CELL - 8) / 2 - 6} textAnchor="middle" className="gate-label">
                P{c.gate + 1}
              </text>
              <text x={(CELL - 8) / 2} y={(CELL - 8) / 2 + 12} textAnchor="middle" className="flight-label">
                {flight !== undefined ? `V${flight + 1}` : '—'}
              </text>
              <title>{`Puerta P${c.gate + 1}${flight !== undefined ? ` ← vuelo V${flight + 1}` : ''}`}</title>
            </g>
          )
        })}
      </svg>
      <p className="muted">
        {perm
          ? 'Arista = pasajeros en conexión entre esos vuelos; grosor ∝ F, intensidad ∝ F × distancia. Top-5 contribuciones en naranja.'
          : 'Ejecuta el solver para ver los flujos sobre la asignación.'}
      </p>
    </section>
  )
}
