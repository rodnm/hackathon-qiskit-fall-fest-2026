# %% [markdown]
# # EDA of the qap10 instance (Track A: flights -> gates)
#
# Run: `uv run python notebooks/01_data_eda.py` (also opens as a notebook in VS Code: `# %%` cells).
# Writes figures to `docs/figures/` and tables to `docs/eda/`.
# Flights are labelled V1..V10 and gates P1..P10 in figures and tables (the code uses 0..9).

# %% setup
import itertools
import sys
from itertools import chain, islice
from math import factorial
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.ticker import FuncFormatter
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import pdist
from scipy.stats import spearmanr

from qap.data import load_instance
from qap.types import cost, costs

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
FIG, TAB = ROOT / "docs" / "figures", ROOT / "docs" / "eda"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
# Okabe-Ito (colorblind-safe). Slots used: blue, vermillion, bluish green (validated all-pairs, contrast >= 3:1).
BLUE, VERMILLION, GREEN = "#0072B2", "#D55E00", "#009E73"
# Sequential ramp: tint -> Okabe-Ito sky blue -> Okabe-Ito blue -> dark navy (one hue, light to dark).
SEQ = LinearSegmentedColormap.from_list("seq_okabe_blue", ["#dcecf7", "#56B4E9", "#0072B2", "#00395c"])
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
})
SRC = "Fuente: qap10 (MIPLIB), matrices F y D recuperadas del MPS. Unidades supuestas, no mediciones."


def save(fig, name):
    if fig.get_layout_engine() is None:
        fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.text(0.01, 0.008, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=160)
    plt.close(fig)


def pct(x, d=1):
    return f"{100 * x:.{d}f} %".replace(".", ",")


inst = load_instance(10)
n, F, D, Fs = inst.n, inst.F, inst.D, inst.F_sym
iu = np.triu_indices(n, 1)
V, P = [f"V{i + 1}" for i in range(n)], [f"P{j + 1}" for j in range(n)]
coords = np.array([(j % 4, j // 4) for j in range(n)])
assert np.array_equal(D, np.abs(coords[:, None, 0] - coords[None, :, 0]) + np.abs(coords[:, None, 1] - coords[None, :, 1]))
flows, dpairs = F[iu], D[iu]
total = int(flows.sum())

# %% tables: overview, value counts
f_counts = pd.Series(flows).value_counts().sort_index().rename("pares")
d_counts = pd.Series(dpairs).value_counts().sort_index().rename("pares")
overview = pd.Series({
    "vuelos": n, "puertas": n, "pares de vuelos": len(flows),
    "pares con flujo > 0": int((flows > 0).sum()), "densidad": round((flows > 0).mean(), 3),
    "flujo total": total, "flujo mínimo > 0": int(flows[flows > 0].min()), "flujo máximo": int(flows.max()),
    "mediana de flujo (pares > 0)": float(np.median(flows[flows > 0])),
    "mcd de los flujos": int(np.gcd.reduce(flows[flows > 0])),
    "distancias distintas (puertas)": sorted(set(dpairs.tolist())),
    "distancia media (pares de puertas)": round(dpairs.mean(), 3), "distancia máxima": int(D.max()),
    "D simétrica": bool(np.array_equal(D, D.T)), "D = Manhattan en cuadrícula de 4 columnas": True,
}, name="valor")
overview.to_csv(TAB / "overview.csv", header=True)
f_counts.to_csv(TAB / "flow_value_counts.csv")
d_counts.to_csv(TAB / "distance_value_counts.csv")

strength, degree = Fs.sum(1), (Fs > 0).sum(1)
flights = pd.DataFrame({
    "vuelo": V, "grado": degree, "pasajeros_en_conexion": strength.astype(int),
    "participacion": strength / (2 * total), "mayor_flujo": Fs.max(1).astype(int),
    "socio_principal": [V[j] for j in Fs.argmax(1)],
}).sort_values("pasajeros_en_conexion", ascending=False)
flights["rank"] = range(1, n + 1)
flights.to_csv(TAB / "flights.csv", index=False)

closeness = D.sum(1)
gates = pd.DataFrame({
    "puerta": P, "fila": coords[:, 1] + 1, "columna": coords[:, 0] + 1,
    "suma_distancias": closeness, "distancia_media": closeness / (n - 1),
}).sort_values("suma_distancias")
gates["rank_centralidad"] = gates["suma_distancias"].rank(method="min").astype(int)
gates.to_csv(TAB / "gates.csv", index=False)

pairs = pd.DataFrame({"par": [f"{V[i]}-{V[k]}" for i, k in zip(*iu)], "flujo": flows})
pairs = pairs[pairs.flujo > 0].sort_values("flujo", ascending=False).reset_index(drop=True)
pairs["participacion"] = pairs.flujo / total
pairs["acumulada"] = pairs.participacion.cumsum()
pairs.to_csv(TAB / "pairs.csv", index=False)

# %% exact cost landscape over all 10! permutations
NEAR = 380
allc = np.empty(factorial(n), dtype=np.int16)
pos, near, aut = 0, [], 0
D8 = D.astype(np.int8)
gen = itertools.permutations(range(n))
while True:
    chunk = np.fromiter(chain.from_iterable(islice(gen, 200_000)), dtype=np.int8)
    if chunk.size == 0:
        break
    chunk = chunk.reshape(-1, n).astype(np.int64)
    c = costs(chunk, inst)
    allc[pos:pos + len(c)] = c
    pos += len(c)
    sel = c <= NEAR
    if sel.any():
        near.append(chunk[sel])
    aut += int((D8[chunk[:, :, None], chunk[:, None, :]] == D8).all(axis=(1, 2)).sum())
near = np.concatenate(near)
opt = int(allc.min())
n_opt = int((allc == opt).sum())
opt_perms = near[costs(near, inst) == opt]
opt_perm = opt_perms[0]
levels, counts = np.unique(allc, return_counts=True)
ident = cost(np.arange(n), inst)
mean_exact = float(allc.mean())
mean_formula = total * D.sum() / (n * (n - 1))
assert abs(mean_exact - mean_formula) < 1e-6, (mean_exact, mean_formula)
landscape = pd.Series({
    "permutaciones": len(allc), "costo mínimo": opt, "permutaciones óptimas": n_opt,
    "segundo mejor costo": int(levels[1]), "permutaciones con el segundo mejor costo": int(counts[1]),
    "costo medio (exacto)": round(mean_exact, 2), "desviación estándar": round(float(allc.std()), 2),
    "mediana": float(np.median(allc)), "costo máximo": int(allc.max()),
    "costo de la asignación identidad": ident, "% de permutaciones mejores que la identidad": round(100 * (allc < ident).mean(), 3),
    "permutaciones a ≤ 1 % del óptimo": int((allc <= opt * 1.01).sum()),
    "permutaciones a ≤ 5 % del óptimo": int((allc <= opt * 1.05).sum()),
    "permutaciones a ≤ 10 % del óptimo": int((allc <= opt * 1.10).sum()),
    "permutaciones a ≤ 20 % del óptimo": int((allc <= opt * 1.20).sum()),
    "automorfismos de D (permutaciones de puertas que preservan D)": aut,
    "ahorro vs media aleatoria": round(1 - opt / mean_exact, 4),
}, name="valor")
landscape.to_csv(TAB / "landscape.csv", header=True)
pd.DataFrame({"costo": levels[:30], "permutaciones": counts[:30]}).to_csv(TAB / "lowest_cost_levels.csv", index=False)

# %% optimal assignment structure
d_opt = D[opt_perm[iu[0]], opt_perm[iu[1]]]
def share_by_d(perm_d):
    return {"1": flows[perm_d == 1].sum() / total, "2": flows[perm_d == 2].sum() / total,
            "3": flows[perm_d == 3].sum() / total, "≥4": flows[perm_d >= 4].sum() / total}


d_id = D[np.arange(n)[iu[0]], np.arange(n)[iu[1]]]
ordered = D[~np.eye(n, dtype=bool)]
rand_share = {"1": (ordered == 1).mean(), "2": (ordered == 2).mean(), "3": (ordered == 3).mean(), "≥4": (ordered >= 4).mean()}
dist_share = pd.DataFrame({"óptima": share_by_d(d_opt), "identidad": share_by_d(d_id), "aleatoria (esperada)": rand_share})
dist_share.to_csv(TAB / "flow_share_by_distance.csv")
gate_of = opt_perm  # flight i -> gate gate_of[i]
mean_dist_gate = closeness / (n - 1)
rho, pval = spearmanr(strength, mean_dist_gate[gate_of])
assign = pd.DataFrame({"vuelo": V, "puerta_optima": [P[g] for g in gate_of],
                       "pasajeros_en_conexion": strength.astype(int),
                       "distancia_media_de_su_puerta": mean_dist_gate[gate_of].round(2)})
assign.to_csv(TAB / "optimal_assignment.csv", index=False)

# %% local search landscape (steepest-descent swaps from random starts)
pairs_idx = np.array(list(itertools.combinations(range(n), 2)))
a, b, r = pairs_idx[:, 0], pairs_idx[:, 1], np.arange(len(pairs_idx))


def descend(p):
    c, steps = cost(p, inst), 0
    while True:
        nb = np.repeat(p[None, :], len(pairs_idx), 0)
        nb[r, a], nb[r, b] = p[b], p[a]
        cs = costs(nb, inst)
        m = cs.argmin()
        if cs[m] >= c:
            return p, c, steps
        p, c, steps = nb[m], int(cs[m]), steps + 1


rng = np.random.default_rng(0)
RUNS = 2000
res = [descend(rng.permutation(n)) for _ in range(RUNS)]
lo_costs = np.array([c for _, c, _ in res])
lo_steps = np.array([s for _, _, s in res])
distinct_lo = len({tuple(p) for p, _, _ in res})
local = pd.Series({
    "arranques": RUNS, "óptimos locales distintos": distinct_lo,
    "% que termina en el óptimo global": round(100 * (lo_costs == opt).mean(), 1),
    "% a ≤ 5 % del óptimo": round(100 * (lo_costs <= opt * 1.05).mean(), 1),
    "costo medio del óptimo local": round(lo_costs.mean(), 1), "peor óptimo local": int(lo_costs.max()),
    "pasos medios hasta converger": round(lo_steps.mean(), 1),
}, name="valor")
local.to_csv(TAB / "local_search.csv", header=True)
lo_counts = pd.Series(lo_costs).value_counts().sort_index()

# %% scaling by sub-instance size and QUBO sizes
rows = []
for m in range(2, 11):
    im = load_instance(m)
    mean_m = im.F.sum() * im.D.sum() / (m * (m - 1))
    rows.append({
        "N": m, "pares con flujo": int((im.F > 0).sum()), "flujo total": int(im.F.sum()),
        "óptimo": im.optimum, "media aleatoria": round(mean_m, 1),
        "ahorro vs aleatoria": round(1 - im.optimum / mean_m, 3),
        "qubits (N²)": m * m, "permutaciones (N!)": factorial(m),
        "fracción factible (N!/2^N²)": factorial(m) / 2 ** (m * m),
        "memoria statevector (bytes)": 16 * 2 ** (m * m),
    })
scaling = pd.DataFrame(rows)
scaling.to_csv(TAB / "scaling.csv", index=False)

prod = np.multiply.outer(flows, ordered)  # F_ik * D_jl, the 4050 quadratic coefficients of the MPS
qubo_counts = pd.Series(prod.ravel()).value_counts().sort_index().rename("terminos")
qubo_counts.to_csv(TAB / "qubo_coefficients.csv")

# %% figures
# 1. flows heatmap ordered by similarity
order = leaves_list(linkage(pdist(Fs), method="average"))
M = Fs[np.ix_(order, order)].astype(float)
fig, ax = plt.subplots(figsize=(6.8, 5.9))
ax.grid(False)
ax.set_facecolor("#efeeea")
im_ = ax.imshow(np.where(M > 0, M, np.nan), cmap=SEQ, vmin=0, vmax=Fs.max())
ax.set_xticks(range(n), [V[i] for i in order])
ax.set_yticks(range(n), [V[i] for i in order])
for i in range(n):
    for j in range(n):
        if M[i, j] > 0:
            ax.text(j, i, int(M[i, j]), ha="center", va="center", fontsize=8.5,
                    color="white" if M[i, j] >= 10 else INK)
fig.colorbar(im_, ax=ax, shrink=0.8, label="Pasajeros en conexión (unidades supuestas)")
zero_pairs = int((flows == 0).sum())
ax.set_title(f"{zero_pairs} de {len(flows)} pares no comparten pasajeros")
ax.set_xlabel("Celdas grises: pares sin pasajeros en conexión")
save(fig, "flows_heatmap.png")

# 2. flight strength
fl = flights.sort_values("pasajeros_en_conexion")
fig, ax = plt.subplots(figsize=(7.5, 4.8))
ax.barh(fl.vuelo, fl.pasajeros_en_conexion, color=BLUE, height=0.62)
for y, (s, d_) in enumerate(zip(fl.pasajeros_en_conexion, fl.grado)):
    ax.text(s + 0.8, y, f"{s}  ({d_} socios)", va="center", fontsize=8.5, color=INK2)
ax.set_xlim(0, fl.pasajeros_en_conexion.max() * 1.22)
top3 = flights.head(3)
ax.set_title(f"{', '.join(top3.vuelo)} concentran el {pct(top3.participacion.sum(), 0)} de los transbordos")
ax.set_xlabel("Pasajeros en conexión del vuelo (suma de sus flujos)")
ax.grid(axis="y", visible=False)
save(fig, "flight_strength.png")

# 3. top flows + cumulative share
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.1, 1]})
top10 = pairs.head(10).iloc[::-1]
ax1.barh(top10.par, top10.flujo, color=BLUE, height=0.62)
for y, v_ in enumerate(top10.flujo):
    ax1.text(v_ + 0.3, y, int(v_), va="center", fontsize=8.5, color=INK2)
ax1.set_xlim(0, pairs.flujo.max() * 1.15)
ax1.set_title("Los 10 mayores flujos")
ax1.set_xlabel("Pasajeros en conexión")
ax1.grid(axis="y", visible=False)
k5 = pairs.acumulada.iloc[4]
ax2.plot(range(1, len(pairs) + 1), pairs.acumulada * 100, color=BLUE, lw=2, marker="o", ms=4.5)
ax2.axhline(50, color=GRID, lw=1)
ax2.set_title(f"5 pares suman el {pct(k5, 0)} del flujo")
ax2.set_xlabel("Pares con flujo, de mayor a menor")
ax2.set_ylabel("Flujo acumulado (%)")
ax2.set_ylim(0, 102)
save(fig, "top_flows.png")

# 4. value distributions
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))
ax1.bar([str(int(v_)) for v_ in f_counts.index], f_counts.values, color=BLUE, width=0.62)
for x_, v_ in enumerate(f_counts.values):
    ax1.text(x_, v_ + 0.25, int(v_), ha="center", fontsize=8.5, color=INK2)
ax1.set_title(f"Flujos: múltiplos de 2; {zero_pairs} pares en cero")
ax1.set_xlabel("Flujo del par (pasajeros, unidades supuestas)")
ax1.set_ylabel("Número de pares de vuelos")
ax1.grid(axis="x", visible=False)
ax2.bar([str(int(v_)) for v_ in d_counts.index], d_counts.values, color=BLUE, width=0.62)
for x_, v_ in enumerate(d_counts.values):
    ax2.text(x_, v_ + 0.25, int(v_), ha="center", fontsize=8.5, color=INK2)
ax2.set_title(f"Distancias: media {dpairs.mean():.2f} pasos, máxima {int(D.max())}".replace(".", ","))
ax2.set_xlabel("Distancia entre puertas (pasos de cuadrícula)")
ax2.set_ylabel("Número de pares de puertas")
ax2.grid(axis="x", visible=False)
save(fig, "flow_distance_hist.png")

# 5. gate layout and distance matrix
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.9), gridspec_kw={"width_ratios": [1, 1.05]})
norm = Normalize(closeness.min(), closeness.max())
for j in range(n):
    x_, y_ = coords[j]
    shade = SEQ(0.15 + 0.8 * (1 - norm(closeness[j])))
    ax1.add_patch(plt.Rectangle((x_ - 0.46, y_ - 0.46), 0.92, 0.92, color=shade))
    tcol = "white" if (1 - norm(closeness[j])) > 0.45 else INK
    ax1.text(x_, y_ - 0.08, P[j], ha="center", va="center", fontsize=11, fontweight="bold", color=tcol)
    ax1.text(x_, y_ + 0.24, f"Σd = {closeness[j]}", ha="center", va="center", fontsize=8, color=tcol)
ax1.set_xlim(-0.6, 3.6)
ax1.set_ylim(2.6, -0.6)
ax1.set_aspect("equal")
ax1.axis("off")
most_central = gates.puerta.iloc[0]
ax1.set_title(f"Cuadrícula de 4 columnas; {most_central} es la más central")
Dm = ax2.imshow(D, cmap=SEQ, vmin=0, vmax=D.max())
ax2.grid(False)
ax2.set_xticks(range(n), P)
ax2.set_yticks(range(n), P)
for i in range(n):
    for j in range(n):
        ax2.text(j, i, D[i, j], ha="center", va="center", fontsize=8, color="white" if D[i, j] >= 3 else INK)
ax2.set_title("Distancia entre puertas (Manhattan)")
save(fig, "gate_grid.png")

# 6. exact cost distribution
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.7), gridspec_kw={"width_ratios": [1.25, 1]})
ax1.hist(allc, bins=np.arange(allc.min(), allc.max() + 5, 4), color=BLUE, rwidth=0.9)
ax1.set_xlabel("Costo de la asignación (distancia ponderada)")
ax1.set_ylabel("Número de asignaciones (de 3 628 800)")
ax1.yaxis.set_major_formatter(FuncFormatter(lambda v_, _: f"{int(v_):,}".replace(",", " ")))
ax1.set_ylim(0, ax1.get_ylim()[1] * 1.18)
ytop = ax1.get_ylim()[1] * 0.93
for val, lab, col, ha, dx, hh in [(opt, f"óptimo {opt}", INK, "left", 4, 1.0), (ident, f"identidad {ident}", VERMILLION, "right", -4, 0.82),
                                  (mean_exact, f"media {mean_exact:.0f}", GREEN, "left", 4, 1.0)]:
    ax1.axvline(val, color=col, lw=1.8)
    ax1.text(val + dx, ytop * hh, lab, color=INK, fontsize=9, fontweight="bold", ha=ha)
ax1.set_title(f"Solo {n_opt} de 3,6 M de asignaciones es óptima")
low = pd.DataFrame({"costo": levels[:18], "n": counts[:18]})
ax2.bar(low.costo.astype(str), low.n, color=BLUE, width=0.7)
ax2.set_yscale("log")
for x_, v_ in enumerate(low.n):
    ax2.text(x_, v_ * 1.12, int(v_), ha="center", fontsize=7.5, color=INK2)
ax2.set_xlabel("Los 18 costos más bajos")
ax2.set_ylabel("Asignaciones con ese costo (escala log)")
ax2.tick_params(axis="x", labelrotation=60, labelsize=8)
ax2.set_title("Pocas soluciones cerca del óptimo")
ax2.grid(axis="x", visible=False)
save(fig, "cost_distribution_exact.png")
save_random = None  # random_cost_hist.png: same story, sampled view kept for the slides
fig, ax = plt.subplots(figsize=(7.5, 4.4))
sample = allc[np.random.default_rng(1).integers(0, len(allc), 20000)]
ax.hist(sample, bins=np.arange(sample.min(), sample.max() + 5, 8), color=BLUE, rwidth=0.9)
ax.set_ylim(0, ax.get_ylim()[1] * 1.18)
ytop = ax.get_ylim()[1] * 0.93
for val, lab, col, ha, dx, hh in [(opt, f"óptimo {opt}", INK, "left", 5, 1.0), (ident, f"identidad {ident}", VERMILLION, "right", -5, 0.82),
                                  (sample.mean(), f"media {sample.mean():.0f}", GREEN, "left", 5, 1.0)]:
    ax.axvline(val, color=col, lw=1.8)
    ax.text(val + dx, ytop * hh, lab, color=INK, fontsize=9, fontweight="bold", ha=ha)
ax.set_xlabel("Costo de la asignación")
ax.set_ylabel("Asignaciones (muestra de 20 000)")
ax.set_title(f"El óptimo camina un {pct(1 - opt / mean_exact, 0)} menos que una asignación al azar")
save(fig, "random_cost_hist.png")

# 7. flow share by distance
fig, ax = plt.subplots(figsize=(8.2, 4.6))
cats = list(dist_share.index)
x = np.arange(len(cats))
w = 0.26
for k, (col, name) in enumerate([(BLUE, "óptima"), (VERMILLION, "identidad"), (GREEN, "aleatoria (esperada)")]):
    ax.bar(x + (k - 1) * w, dist_share[name] * 100, w * 0.92, color=col, label=name)
for xi, v_ in zip(x - w, dist_share["óptima"] * 100):
    ax.text(xi, v_ + 0.8, f"{v_:.0f} %", ha="center", fontsize=8.5, color=INK)
ax.set_xticks(x, [f"{c} paso" if c == "1" else f"{c} pasos" for c in cats])
ax.set_ylabel("Pasajeros en conexión (%)")
ax.set_xlabel("Distancia que caminan entre sus dos puertas")
ax.legend(frameon=False, ncols=3, loc="upper right")
ax.grid(axis="x", visible=False)
ax.set_title(f"La asignación óptima deja el {pct(dist_share.loc['1', 'óptima'], 0)} del flujo a 1 paso de distancia")
save(fig, "flow_by_distance.png")

# 8. optimal vs identity on the grid
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), layout="constrained")
fig.get_layout_engine().set(rect=(0, 0.07, 1, 0.93))
cnorm = Normalize(0, 60)
for ax, perm, title in [(axes[0], opt_perm, f"Asignación óptima (costo {opt})"),
                        (axes[1], np.arange(n), f"Asignación identidad (costo {ident})")]:
    cell_flight = {int(g): int(v_) for v_, g in enumerate(perm)}
    for j in range(n):
        x_, y_ = coords[j]
        ax.add_patch(plt.Rectangle((x_ - 0.42, y_ - 0.42), 0.84, 0.84, facecolor="#efeeea", edgecolor=GRID, zorder=1))
        ax.text(x_, y_ - 0.22, P[j], ha="center", va="center", fontsize=7.5, color=INK2, zorder=4)
        ax.text(x_, y_ + 0.12, V[cell_flight[j]], ha="center", va="center", fontsize=12, fontweight="bold", color=INK, zorder=4)
    for (i, k), f_ in zip(zip(*iu), flows):
        if f_ <= 0:
            continue
        g1, g2 = coords[perm[i]], coords[perm[k]]
        contrib = f_ * D[perm[i], perm[k]]
        ax.plot([g1[0], g2[0]], [g1[1], g2[1]], color=SEQ(0.18 + 0.82 * cnorm(contrib)), lw=0.6 + f_ / 20 * 4.4,
                alpha=0.85, zorder=2, solid_capstyle="round")
    ax.set_xlim(-0.6, 3.6)
    ax.set_ylim(2.6, -0.6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title)
sm = plt.cm.ScalarMappable(norm=cnorm, cmap=SEQ)
fig.colorbar(sm, ax=axes, shrink=0.7, label="Aporte al costo de la conexión (flujo × distancia)")
fig.text(0.01, 0.035, "Grosor de la línea = pasajeros del par. Color = aporte al costo total.", fontsize=8, color=INK2)
save(fig, "optimal_assignment.png")

# 9. hubs vs centrality
fig, ax = plt.subplots(figsize=(7.2, 4.8))
ax.scatter(strength, mean_dist_gate[gate_of], s=70, color=BLUE, zorder=3)
for i in range(n):
    ax.annotate(V[i], (strength[i], mean_dist_gate[gate_of][i]), textcoords="offset points", xytext=(6, 5), fontsize=8.5, color=INK2)
ax.set_xlabel("Pasajeros en conexión del vuelo")
ax.set_ylabel("Distancia media de su puerta al resto (más bajo = más central)")
verdict = "ocupan puertas más centrales" if rho < -0.3 else ("sin relación clara con la centralidad" if abs(rho) <= 0.3 else "ocupan puertas menos centrales")
ax.set_title("\n".join(["En el óptimo, los vuelos con más pasajeros", f"{verdict} (ρ = {rho:.2f})".replace(".", ",")]))
save(fig, "hubs_vs_centrality.png")

# 10. local optima
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.bar(lo_counts.index.astype(str), lo_counts.values, color=BLUE, width=0.7)
for x_, (cst, v_) in enumerate(lo_counts.items()):
    if cst == opt:
        ax.bar(str(cst), v_, color=INK, width=0.7)
        ax.text(x_ - 0.45, v_ + 10, f"óptimo global {opt}", ha="left", fontsize=8.5, fontweight="bold")
ax.set_xlabel("Costo del óptimo local alcanzado")
ax.set_ylabel(f"Arranques aleatorios (de {RUNS})")
ax.tick_params(axis="x", labelrotation=60, labelsize=8)
ax.grid(axis="x", visible=False)
ax.set_title(f"Solo el {local['% que termina en el óptimo global']:.0f} % de las búsquedas locales llega al óptimo".replace(".", ","))
save(fig, "local_optima.png")

# 11. scaling and feasibility fraction
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
ax1.plot(scaling.N, scaling["media aleatoria"], color=GREEN, lw=2, marker="o", ms=5, label="asignación aleatoria (media)")
ax1.plot(scaling.N, scaling["óptimo"], color=BLUE, lw=2, marker="o", ms=5, label="óptimo")
ax1.legend(frameon=False, loc="upper left")
ax1.set_xlabel("Tamaño N (primeros N vuelos y N puertas)")
ax1.set_ylabel("Costo")
ax1.set_title(f"Ahorro vs azar: {pct(scaling.loc[scaling.N == 4, 'ahorro vs aleatoria'].iat[0], 0)} (N=4), {pct(scaling.loc[scaling.N == 10, 'ahorro vs aleatoria'].iat[0], 0)} (N=10)")
ax2.bar(scaling.N.astype(str), scaling["fracción factible (N!/2^N²)"], color=BLUE, width=0.62)
ax2.set_yscale("log")
ax2.set_xlabel("Tamaño N (qubits = N²)")
ax2.set_ylabel("Fracción factible (escala log)")
f4 = scaling.loc[scaling.N == 4, "fracción factible (N!/2^N²)"].iat[0]
ax2.set_title(f"Con N=4, solo el {pct(f4, 3)} es factible")
ax2.grid(axis="x", visible=False)
save(fig, "scaling_feasibility.png")

# 12. QUBO coefficients
nz = qubo_counts[qubo_counts.index > 0]
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.bar([str(int(v_)) for v_ in nz.index], nz.values, color=BLUE, width=0.7)
for x_, v_ in enumerate(nz.values):
    ax.text(x_, v_ + 8, int(v_), ha="center", fontsize=8, color=INK2)
ax.set_xlabel("Coeficiente cuadrático F·D")
ax.set_ylabel("Número de términos")
ax.grid(axis="x", visible=False)
ax.set_title(f"{int(nz.sum())} términos no nulos de {prod.size}; el mayor vale {int(nz.index.max())}")
save(fig, "qubo_coefficients.png")

# %% print tables for the report
pd.set_option("display.width", 200, "display.max_columns", 30)
for name, obj in [("overview", overview), ("f_counts", f_counts), ("d_counts", d_counts), ("flights", flights),
                  ("gates", gates), ("pairs(top 10)", pairs.head(10)), ("landscape", landscape),
                  ("dist_share", dist_share.round(3)), ("assign", assign), ("local", local),
                  ("scaling", scaling), ("qubo_counts", qubo_counts)]:
    print(f"\n=== {name} ===\n{obj.to_string() if hasattr(obj, 'to_string') else obj}")
print("\nspearman rho (flight strength vs gate mean distance):", round(rho, 3), "p =", round(pval, 4))
print("optimal perms:", opt_perms.tolist())
print("lowest cost levels:", dict(zip(levels[:12].tolist(), counts[:12].tolist())))
