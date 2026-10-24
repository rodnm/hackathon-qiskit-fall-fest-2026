import { useEffect } from 'react'

/** Portada del proyecto — narrativa de docs/storytelling-aeroq-optmizer-2456c349.txt.
 *  Reglas de honestidad: el caso CDG es testimonio reportado (no causalidad),
 *  las cifras del modelo son supuestos, sin afirmaciones de ventaja cuántica. */

const PERM = [2, 6, 3, 0, 8, 4, 5, 1, 7, 9] // asignación óptima de qap10 (00-shared.md)
const FLOWS: [number, number, number][] = [
  [0, 1, 10], [0, 2, 4], [1, 2, 6], [2, 3, 12], [3, 4, 3],
  [4, 5, 8], [5, 6, 5], [6, 7, 9], [7, 8, 4], [8, 9, 7],
] // ejemplo ilustrativo, no datos medidos
const MAX_F = Math.max(...FLOWS.map((f) => f[2]))

function gatePos(j: number) {
  return { x: 70 + (j % 4) * 140, y: 56 + Math.floor(j / 4) * 100 }
}

function GateFlowArt() {
  const edges = FLOWS.map(([i, k, f]) => {
    const a = gatePos(PERM[i])
    const b = gatePos(PERM[k])
    return { a, b, f, key: `${i}-${k}` }
  })
  const movers = edges.slice(0, 4)
  return (
    <svg className="gateflow" viewBox="0 0 600 320" role="img" aria-label="Flujo ilustrativo de pasajeros entre puertas asignadas">
      {edges.map((e) => (
        <line
          key={e.key}
          x1={e.a.x} y1={e.a.y} x2={e.b.x} y2={e.b.y}
          className="flow-edge"
          strokeWidth={1 + 4.5 * (e.f / MAX_F)}
          style={{ animationDelay: `${(e.f % 5) * 0.4}s` }}
        />
      ))}
      {movers.map((e, idx) => (
        <circle key={`m-${e.key}`} r={3.2} className="flow-dot" fill="#60a5fa">
          <animateMotion
            dur={`${4 + idx * 0.7}s`}
            repeatCount="indefinite"
            path={`M ${e.a.x} ${e.a.y} L ${e.b.x} ${e.b.y}`}
          />
        </circle>
      ))}
      {Array.from({ length: 10 }, (_, j) => {
        const p = gatePos(j)
        return (
          <g key={j} transform={`translate(${p.x}, ${p.y})`} className="gate-node">
            <circle r={17} />
            <text dy="4" textAnchor="middle">P{j + 1}</text>
          </g>
        )
      })}
    </svg>
  )
}

export default function Landing() {
  useEffect(() => {
    document.title = 'AeroQ Optimizer — menos metros caminando en cada conexión'
  }, [])

  return (
    <main className="landing">
      <section className="hero">
        <div className="hero-copy">
          <p className="kicker">The Explorers · Qiskit Fall Fest 2026 · Reto NTT DATA</p>
          <h1>
            Diez vuelos, diez puertas, y gente caminando entre ellas.
          </h1>
          <p className="lede">
            Cuánta distancia recorre una persona en conexión no es azar: depende de
            qué puerta recibió cada vuelo. <strong>AeroQ Optimizer</strong> modela ese
            problema (un QAP clásico, estudiado desde Mangoubi y Mathaisel, 1985) y
            explora con computación cuántica —Qiskit, QAOA— la asignación que minimiza
            los metros que camina en tránsito toda la gente que conecta.
          </p>
          <div className="chips">
            <span className="chip-stat">10 vuelos · 10 puertas</span>
            <span className="chip-stat">Óptimo verificado: 340</span>
            <span className="chip-stat">≈ 34 % menos caminata vs asignación aleatoria*</span>
          </div>
          <p className="footnote">*Unidades y conclusiones operativas: supuestos, no mediciones.</p>
          <div className="cta-row">
            <a className="cta" href="/app">Abrir AeroQ Optimizer →</a>
            <a className="cta ghost" href="/app#resultados">Ver resultados del Día 1</a>
          </div>
        </div>
        <GateFlowArt />
      </section>

      <section className="case card-dark">
        <p className="kicker">El caso que inspira el proyecto</p>
        <h2>
          París, Charles de Gaulle, 2007: Peter Cannell y Eileen Cook perdieron su
          conexión de vuelta a casa.
        </h2>
        <p>
          Venían de El Cairo con Air France y 50 minutos previstos de conexión. Su
          vuelo llegó tarde y, según relataron a la prensa, aunque hubiera llegado a
          tiempo no bastaba: el avión terminó en una posición remota y el trayecto
          exigía bus, cruce a pie de la terminal 2C, otro bus a la 2F y una larga cola.
          Air France explicó que, al demorarse el vuelo, su puerta suele reasignarse
          a otro avión.
        </p>
        <p className="case-note">
          Detrás de cada variable del modelo hay personas como ellos: <em>F<sub>ik</sub></em> son
          pasajeros que conectan entre los vuelos i y k; <em>D<sub>jl</sub></em>, los metros entre
          las puertas j y l. Minimizar Σ F·D es minimizar la caminata de quien conecta.
          Es una pieza del problema —no elimina demoras ni colas— y este proyecto lo
          estudia con honestidad: sin afirmar que salve conexiones ni que exista
          ventaja cuántica.
        </p>
        <p className="case-source">
          Testimonio reportado · Fuente:{' '}
          <a
            href="https://www.theguardian.com/business/2007/may/25/theairlineindustry.lifeandhealth"
            target="_blank"
            rel="noreferrer"
          >
            The Guardian, «Dear Anna: Our flight connection fiasco left us stranded», 25-may-2007
          </a>
        </p>
      </section>

      <footer className="landing-footer">
        <span>Equipo The Explorers — AeroQ Optimizer</span>
        <span>
          Referencia del modelo: Mangoubi &amp; Mathaisel, <em>Transportation Science</em>, 1985 ·
          Instancia: MIPLIB qap10
        </span>
      </footer>
    </main>
  )
}
