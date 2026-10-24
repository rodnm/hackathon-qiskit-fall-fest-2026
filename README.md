# QAP10 — Quantum Assignment Hackathon (Qiskit Fall Fest 2026)

NTT DATA challenge: solve the MIPLIB `qap10` quadratic assignment instance (10 items, 10 locations,
reference optimum C* = 340) with a classical baseline and a Qiskit-based (quantum/hybrid) approach,
then compare cost, feasibility and time. Challenge docs live in `reto-ntt-data/`.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # creates .venv and installs locked dependencies (Python 3.12)
uv run python -c "import qiskit; print(qiskit.__version__)"
uv run pytest                # run tests
uv run ruff check .          # lint
uv run streamlit run src/app.py   # comparison app (once implemented)
uv run jupyter lab           # notebooks
```

Add dependencies with `uv add <pkg>` (or `uv add --dev <pkg>`) and commit `pyproject.toml` + `uv.lock`.

## Layout

- `reto-ntt-data/` — challenge statement and participation rules
- `data/` — `qap10.mps.gz` (source: https://miplib.zib.de/instance_details_qap10.html)
- `src/` — project code
- `notebooks/` — experiments
- `tests/` — tests
