"""Esquemas Pydantic de la API (contrato de S2 en docs/plan/03-felipe-storytelling.md)."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str
    qiskit: str
    db: str


class GateCoord(BaseModel):
    gate: int
    col: int
    row: int


class InstanceOut(BaseModel):
    name: str
    n: int
    F: list[list[int]]  # triangular superior estricta (convención del paquete qap)
    D: list[list[int]]  # simétrica, diagonal cero
    optimum: int | None
    layout: list[GateCoord]  # cuadrícula de 4 columnas (supuesto de dibujo)


class ValidateRequest(BaseModel):
    F: list[list[int]]
    D: list[list[int]]


class ValidateOut(BaseModel):
    ok: bool
    errors: list[str]


class ClassicalRequest(BaseModel):
    n: int = Field(ge=2, le=10)
    method: Literal["bruteforce", "sa"] = "bruteforce"
    seed: int = 0


class QaoaRequest(BaseModel):
    # El servidor rechaza QAOA para N > 4 (regla de S2); lam -> penalty en qap.quantum
    n: int = Field(ge=2, le=4)
    lam: float | None = None
    reps: int = Field(default=1, ge=1, le=3)
    maxiter: int = Field(default=100, ge=1, le=1000)
    shots: int = Field(default=4096, ge=128, le=100_000)
    seed: int = 0


class Assignment(BaseModel):
    flight: int
    gate: int


class ResultOut(BaseModel):
    method: str
    perm: list[int] | None
    assignment: list[Assignment]
    cost: int | None  # recalculado con qap.types.cost: nunca la energía penalizada
    feasible: bool
    seconds: float
    peak_mem_mb: float
    seed: int | None
    params: dict[str, Any]
    extras: dict[str, Any]
    reference_cost: int | None
    gap_pct: float | None  # solo para resultados factibles
    reference_kind: str  # "proven_optimum" | "best_found"
