# Reglas permanentes de trabajo (regla del usuario, 2026-10-24)

1. **Skills primero**: al empezar cada tarea, revisa los skills instalados (`.claude/skills/`: hackathon-coach,
   qiskit-engineering, quantum-optimization, ibm-quantum-compute, qml-edtech, además de los agent-skills) e invoca
   los que apliquen al problema.
2. **Automode**: ejecuta los planes completos en un solo pase aprobado (estilo `agent-skills:build auto`), sin pedir
   confirmación paso a paso. Confirmar solo acciones irreversibles o externas: push, borrados, envíos externos,
   ejecuciones con coste en IBM Quantum.
3. **Subagentes**: paraleliza con subagentes en lugar de hacer búsquedas largas en el hilo principal
   (Explore para mapear código, Plan para diseñar, code-reviewer/test-engineer para calidad).

## Proyecto

AeroQ Optimizer — equipo The Explorers, Qiskit Fall Fest 2026. Reto NTT DATA: QAP `qap10` (MIPLIB), óptimo C* = 340.

- Fuente de verdad del coste y el gap: `src/qap/types.py` (C = Σ_{i<k} F_ik · D_{p(i)p(k)}; gap = 100·(C−340)/340).
- Stack: uv + Python 3.12; verificar con `uv run pytest` y `uv run ruff check .`.
