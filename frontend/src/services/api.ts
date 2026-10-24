export interface Health {
  status: string
  qiskit: string
  db: string
}

export interface GateCoord {
  gate: number
  col: number
  row: number
}

export interface InstanceData {
  name: string
  n: number
  F: number[][]
  D: number[][]
  optimum: number | null
  layout: GateCoord[]
}

export interface Assignment {
  flight: number
  gate: number
}

export interface ResultOut {
  method: string
  perm: number[] | null
  assignment: Assignment[]
  cost: number | null
  feasible: boolean
  seconds: number
  peak_mem_mb: number
  seed: number | null
  params: Record<string, unknown>
  extras: Record<string, unknown>
  reference_cost: number | null
  gap_pct: number | null
  reference_kind: string
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') msg = body.detail
    } catch {
      /* sin cuerpo JSON */
    }
    throw new Error(msg)
  }
  return (await res.json()) as T
}

export const api = {
  health: () => fetch('/api/health').then((r) => handle<Health>(r)),
  instance: (n: number) =>
    fetch(`/api/instance?n=${n}`).then((r) => handle<InstanceData>(r)),
  classical: (n: number, seed = 0) =>
    fetch('/api/optimize/classical', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ n, method: 'bruteforce', seed }),
    }).then((r) => handle<ResultOut>(r)),
}
