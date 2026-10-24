# PART 3 — Felipe: STORYTELLING (product, jury communication, submission)

**You own:** `src/app.py`, `docs/` (slides, script, storyboard, description), README "Results & story" section,
the submission itself. **You depend on:** Rodrigo's figures/`qap10_FD.npz` (T+1:30) and `results/benchmark.csv`
(T+2:15). Until then, build everything with the placeholders below so you never wait.
**Your job is also to protect the schedule:** you run the deliverables checklist and the rehearsal.

### S1. Narrative + one-pager (0:00–0:40) — `docs/story.md`
- Title/tagline: *Fewer minutes walking for transferring passengers — a rigorous quantum-vs-classical study on gate assignment.*
- Problem and why it matters (connections, missed flights, congestion — **qualitatively**, no invented statistics).
- Model in plain words: flights, gates, passengers transferring, walking distance, one gate per flight.
- Hook number (real, from our data): the optimum is **≈ 34 % less total walking than a random assignment**
  (identity = 454, random mean ≈ 512, optimum = 340) — always say "in assumed units".
- Where Qiskit enters (QUBO → Ising → QAOA; hybrid neighborhoods) and the **honest verdict**: classical solves N=10 in 4 s;
  quantum/hybrid is studied for how it behaves and scales, with its limits (qubits = N², penalties, noise).
- Required statement: units and operational conclusions are assumptions, not measurements.

### S2. Streamlit app — `src/app.py` (0:40–2:30)
Principle: **the demo must never depend on a live quantum run.** Read `data/qap10_FD.npz` and `results/benchmark.csv`;
only N ≤ 4 offers a live "Run" button (with spinner and a timeout message).
Placeholders first: fake `Result` objects with the real field names (Part 0.5) so you can build the UI today.
Tabs (`st.tabs`):
1. **Problem** — gate grid (matplotlib) with flows as edges (width ∝ passengers) for the chosen assignment; selector
   for N and for the assignment (naive / classical / hybrid / QAOA). Always show the total walking cost.
2. **Solve** — controls: N (3, 4, 10), method, λ, seed. N ≤ 4 runs live; N=10 loads cached results.
3. **Compare** — table (cost, gap %, feasible, feasible fraction, seconds) + bar charts (cost, time, feasible fraction).
4. **Scale** — time and gap vs N (3, 4, 10, then ≥ 14 on day 2); text box with "where each method stops being useful".
Use `st.cache_data` for loading files. Run: `uv run streamlit run src/app.py`. Deploy only if time permits (not required).
Also add a clear "assumptions" caption in the app.

### S3. Slide deck (PPT) — `docs/slides.pptx` (1:30–2:30)
8 slides, one idea each:
1. Title + team + tagline.
2. The problem (gates, flights, transferring passengers) — the picture from `gate_grid.png`.
3. The model: objective, one-gate-per-flight constraints, 340 reference, scale check (24/32/340).
4. Pipeline: MPS → F,D → QUBO (λ) → Ising → QAOA / hybrid → feasible assignment (a diagram).
5. Classical baseline: brute force 4 s, SA; the 34 % hook with `random_cost_hist.png`.
6. Qiskit results: N=3/4 QAOA (feasible fraction, gap), λ figure, hybrid N=10 and the ablation.
7. Scaling and limits: where it stops being useful; 14! ≈ 8.7×10¹⁰; the statevector memory table.
8. Honest conclusion + what's next + reproducibility (repo, `uv sync`, seeds). Credits.
Rule: every number on a slide comes from `results/benchmark.csv` or the verified facts in Part 0.3.

### S4. Pitch script, 2:30–3:00 min (rehearse 3×) — `docs/pitch.md`
- 0:00–0:25 Problem and hook (34 % less walking). 0:25–1:00 Model and how Qiskit enters (one sentence per step).
- 1:00–1:40 Live demo (30–40 s) on the app: pick N, show assignment, show the comparison table. Have the recorded video as fallback.
- 1:40–2:20 Results and honest limits (classical wins on speed at N=10; what QAOA/hybrid did; scaling).
- 2:20–3:00 Why this matters and next steps. All team members present at 15:00–16:40.
Q&A cheat sheet (answers agreed with Rodrigo and Diego): *Why quantum if brute force takes 4 s? What is λ and how did you
choose it? Is this a quantum advantage? Why QAOA? How do you know it's feasible/correct (24/32/340)? How reproducible is it?
What would change on real hardware (noise, depth)?*

### S5. Demo video (2:30–3:00) — `docs/demo.mp4` (or link)
60–90 s screen recording of the app following the pitch storyboard (Win+G or OBS), voice-over or captions, shows the
comparison and the final numbers. Upload somewhere the jury can open without login (Drive link, "anyone with the link").

### S6. Submission package (before 16:30, one hour before the 17:00 cutoff)
Checklist (bases §8): ☐ team name ☐ member names ☐ GitHub repo link ☐ demo (link or video) ☐ short description
(problem · solution · main features, ~120 words, draft in `docs/description.md`) ☐ PPT. Then open **every link in a private
window** to confirm the jury can access it. **Repo is currently private** → see Part 5, decision 2.

**Your definition of done:** app runs offline from committed results; slides + pitch rehearsed; video recorded; submission
sent and links verified.
