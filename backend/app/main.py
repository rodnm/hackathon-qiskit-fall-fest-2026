"""AeroQ Optimizer API — las 6 rutas del contrato de S2 (+ histórico de runs).

Reglas de servidor (S2): tamaños limitados por esquema, QAOA con timeout de 90 s y
un lock (HTTP 429 si ya hay una ejecución), solvers bloqueantes fuera del event
loop, sin stack traces. Sin CORS: detrás del proxy de Nginx/Apache.
"""

import asyncio
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from qap.classical import solve_bruteforce, solve_sa
from qap.data import load_instance
from qap.quantum import solve_qaoa

from . import db
from .schemas import (
    ClassicalRequest,
    HealthOut,
    InstanceOut,
    QaoaRequest,
    ResultOut,
    ValidateOut,
    ValidateRequest,
)
from .service import (
    benchmark_rows,
    comparison_rows,
    instance_out,
    reference,
    result_out,
    validate_matrices,
)

QAOA_TIMEOUT_S = 90

_background: set[asyncio.Task[None]] = set()
_qaoa_lock = asyncio.Lock()


def _record(out: ResultOut, n: int) -> None:
    """Guarda la ejecución en la BD sin bloquear la respuesta ni fallarla."""
    task = asyncio.get_running_loop().create_task(
        run_in_threadpool(db.record_run, out, n)
    )
    _background.add(task)
    task.add_done_callback(_background.discard)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Precalienta referencias (24/32/340) y el layout; la BD es best-effort.
    await run_in_threadpool(lambda: [reference(n) for n in (3, 4, 10)])
    await run_in_threadpool(db.init_schema)
    yield


app = FastAPI(
    title="AeroQ Optimizer API",
    description=(
        "Asignación de puertas de embarque (QAP qap10) — The Explorers, "
        "Qiskit Fall Fest 2026."
    ),
    lifespan=lifespan,
)


@app.exception_handler(ValueError)
async def value_error_handler(_: Any, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/api/health", response_model=HealthOut)
async def health() -> HealthOut:
    db_state = await run_in_threadpool(db.check)
    return HealthOut(status="ok", qiskit=version("qiskit"), db=db_state)


@app.get("/api/instance", response_model=InstanceOut)
async def get_instance(n: int = Query(default=4, ge=2, le=10)) -> InstanceOut:
    return await run_in_threadpool(instance_out, n)


@app.post("/api/validate", response_model=ValidateOut)
async def validate(request: ValidateRequest) -> ValidateOut:
    return await run_in_threadpool(validate_matrices, request.F, request.D)


@app.post("/api/optimize/classical", response_model=ResultOut)
async def optimize_classical(request: ClassicalRequest) -> ResultOut:
    inst = await run_in_threadpool(load_instance, request.n)
    if request.method == "sa":
        result = await run_in_threadpool(solve_sa, inst, seed=request.seed)
    else:
        result = await run_in_threadpool(solve_bruteforce, inst, seed=request.seed)
    out = result_out(result, inst)
    _record(out, request.n)
    return out


@app.post("/api/optimize/qaoa", response_model=ResultOut)
async def optimize_qaoa(request: QaoaRequest) -> ResultOut:
    if _qaoa_lock.locked():
        raise HTTPException(
            status_code=429,
            detail="Ya hay una ejecución de QAOA en curso; inténtalo en unos momentos",
        )
    async with _qaoa_lock:
        inst = await run_in_threadpool(load_instance, request.n)

        def _run() -> Any:
            return solve_qaoa(
                inst,
                seed=request.seed,
                reps=request.reps,
                maxiter=request.maxiter,
                shots=request.shots,
                penalty=request.lam,
            )

        try:
            result = await asyncio.wait_for(
                run_in_threadpool(_run), timeout=QAOA_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=f"QAOA excedió el límite de {QAOA_TIMEOUT_S} s",
            ) from None
        out = result_out(result, inst)
        _record(out, request.n)
        return out


@app.get("/api/benchmark")
async def get_benchmark() -> list[dict[str, str]]:
    return await run_in_threadpool(benchmark_rows)


@app.get("/api/comparison")
async def get_comparison() -> list[dict[str, str]]:
    return await run_in_threadpool(comparison_rows)


@app.get("/api/runs")
async def get_runs(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    return await run_in_threadpool(db.recent_runs, limit)
