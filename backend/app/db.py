"""Persistencia opcional de ejecuciones en PostgreSQL (servicio `db` del compose).

Todas las operaciones son best-effort: si la base no está disponible la API sigue
funcionando y /api/health lo reporta como db="unavailable".
"""

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id          serial PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now(),
    method      text        NOT NULL,
    n           int         NOT NULL,
    seed        bigint,
    cost        bigint,
    feasible    boolean     NOT NULL,
    gap_pct     double precision,
    seconds     double precision NOT NULL
)
"""


def _dsn() -> str:
    return psycopg.conninfo.make_conninfo(
        host=os.getenv("AEROQ_DB_HOST", "db"),
        port=int(os.getenv("AEROQ_DB_PORT", "5432")),
        user=os.getenv("AEROQ_DB_USER", "aeroq"),
        password=os.getenv("AEROQ_DB_PASSWORD", "aeroq_dev"),
        dbname=os.getenv("AEROQ_DB_NAME", "aeroq"),
        connect_timeout=3,
    )


def check() -> str:
    if not os.getenv("AEROQ_DB_HOST"):
        return "unavailable"
    try:
        with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
            conn.execute("SELECT 1")
        return "ok"
    except psycopg.Error:
        return "unavailable"


def init_schema() -> None:
    if not os.getenv("AEROQ_DB_HOST"):
        return
    try:
        with psycopg.connect(_dsn()) as conn:
            conn.execute(_DDL)
            conn.commit()
    except psycopg.Error:
        pass  # best-effort: la app funciona sin histórico


def record_run(out: Any, n: int) -> None:
    try:
        with psycopg.connect(_dsn()) as conn:
            conn.execute(
                "INSERT INTO runs (method, n, seed, cost, feasible, gap_pct, seconds) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    out.method,
                    n,
                    out.seed,
                    out.cost,
                    out.feasible,
                    out.gap_pct,
                    out.seconds,
                ),
            )
            conn.commit()
    except psycopg.Error:
        pass


def recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    if not os.getenv("AEROQ_DB_HOST"):
        return []
    try:
        with psycopg.connect(_dsn(), row_factory=dict_row) as conn:
            rows = conn.execute(
                "SELECT id, created_at, method, n, seed, cost, feasible, gap_pct, seconds "
                "FROM runs ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
        for row in rows:
            row["created_at"] = row["created_at"].isoformat()
        return rows
    except psycopg.Error:
        return []
