"""Pruebas de humo de los endpoints (criterio de terminado en S8 del plan)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["qiskit"]


def test_instance_n4() -> None:
    res = client.get("/api/instance", params={"n": 4})
    assert res.status_code == 200
    body = res.json()
    assert body["n"] == 4
    assert body["optimum"] == 32
    n = 4
    # F triangular superior, D simétrica con diagonal cero
    assert all(body["F"][i][j] == 0 for i in range(n) for j in range(i))
    assert all(
        body["D"][i][j] == body["D"][j][i] for i in range(n) for j in range(i)
    )
    assert all(body["D"][i][i] == 0 for i in range(n))
    assert len(body["layout"]) == 4


def test_classical_n4_proven_optimum() -> None:
    res = client.post(
        "/api/optimize/classical", json={"n": 4, "method": "bruteforce", "seed": 0}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["cost"] == 32
    assert body["feasible"] is True
    assert body["reference_kind"] == "proven_optimum"
    assert body["gap_pct"] == 0.0
    assert sorted(body["perm"]) == [0, 1, 2, 3]


def test_sa_not_implemented_is_501() -> None:
    res = client.post(
        "/api/optimize/classical", json={"n": 3, "method": "sa", "seed": 0}
    )
    assert res.status_code == 501


def test_qaoa_rejects_n5() -> None:
    res = client.post("/api/optimize/qaoa", json={"n": 5, "seed": 0})
    assert res.status_code == 422  # QAOA limitado a N <= 4


def test_validate_rejects_asymmetric_D() -> None:
    res = client.post(
        "/api/validate",
        json={"F": [[0, 1], [1, 0]], "D": [[0, 2], [5, 0]]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert any("D" in e for e in body["errors"])


@pytest.mark.slow
def test_classical_n10_control_340() -> None:
    res = client.post(
        "/api/optimize/classical", json={"n": 10, "method": "bruteforce", "seed": 0}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["cost"] == 340
    assert body["gap_pct"] == 0.0
