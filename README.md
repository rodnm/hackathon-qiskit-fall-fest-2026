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

## Data

The MPS file is the Adams–Johnson linearization of the QAP: each `Y` column is a product x_ij·x_kl (i < k, j ≠ l) whose
objective coefficient is F_ik·D_jl. `qap.data` factorizes those coefficients into the flow matrix F and the distance matrix D,
checking block by block that the factorization is exact (rank 1). D turns out to be the Manhattan distance on a 4-column grid
of 10 gates. Exhaustive search over the 10! assignments reproduces the control optima 24 (N=3), 32 (N=4) and 340 (N=10).

- Cost convention (single source of truth: `qap.types.cost`): C = Σ_{i<k} F_ik · D_{p(i) p(k)}, each flight pair counted once.
- Gap (challenge definition, valid solutions only): gap(%) = 100 · (C − 340) / 340.
- Units are assumptions, not measurements.

| File | Content |
|---|---|
| `data/qap10.mps.gz` | Original MIPLIB instance |
| `data/qap10_FD.npz`, `data/qap10_F.csv`, `data/qap10_D.csv` | Recovered F (upper-triangular) and D, exact optima for N = 2..10 |
| `data/processed/qap10_summary.json` | Data handoff for the models and the app: matrices, gate layout, optimal assignments for N = 2..10, gap and saving references, Qiskit sizes |
| `notebooks/01_data.ipynb` | Exploratory analysis (findings summarized in `docs/eda.md`) |
| `docs/figures/`, `docs/eda/` | Figures and CSV tables produced by the notebook |

```bash
uv run python -m qap.data                                                         # rebuild the npz/CSV from the MPS
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/01_data.ipynb  # rebuild the EDA, figures, tables and the JSON
```

## Layout

- `reto-ntt-data/` — challenge statement and participation rules
- `data/` — instance and recovered matrices (see Data)
- `src/qap/` — shared package: contracts (`types.py`), data loading (`data.py`), solvers
- `notebooks/` — analysis notebooks
- `docs/` — team plan, EDA report and figures
- `tests/` — tests
- `.claude/skills/` — AI-agent skills for the team (Claude Code loads them automatically): hackathon coach, Qiskit engineering,
  quantum optimization (QUBO/Ising/QAOA), IBM Quantum compute, QML EdTech
