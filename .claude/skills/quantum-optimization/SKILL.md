---
name: quantum-optimization
description: Formula, implementa y compara problemas de rutas, conexiones y asignación con enfoques clásicos, QUBO, Ising y QAOA en Qiskit Optimization. Actívala para optimización cuántica o híbrida.
---

# Skill: Optimización cuántica e híbrida

## Propósito

Convertir problemas reales de optimización en modelos explícitos, verificar sus restricciones y comparar métodos clásicos y cuánticos sin exagerar lo que demuestra un prototipo. Es especialmente relevante para el reto de Algoritmos y Aplicaciones del Qiskit Fall Fest 2026.

## Cuándo usarla

- El usuario busca optimizar rutas, conexiones, selección de recursos o asignaciones.
- Necesita formular un `QuadraticProgram`, convertirlo a QUBO/Ising o explorar QAOA.
- Requiere visualizar y comparar soluciones factibles de distintas estrategias.

## Procedimiento

1. **Formaliza el problema.** Especifica entradas, unidades, variables y dominios, objetivo (minimizar/maximizar), restricciones, datos faltantes y qué significa una solución factible.
2. **Construye primero una referencia clásica.** Para instancias pequeñas usa enumeración/exacto cuando sea viable; para tamaños mayores usa una heurística o solver clásico adecuado. Registra el mismo objetivo y límites para cada comparación.
3. **Modela en `QuadraticProgram`.** Mantén los nombres y el orden de variables documentados. Añade objetivo y restricciones directamente si la representación lo permite.
4. **Evalúa compatibilidad con el enfoque cuántico.** QAOA usa una formulación compatible con el mapeo a un Hamiltoniano de coste, habitualmente a través de QUBO/Ising. Convierte solo las restricciones que puedan representarse correctamente y explica la transformación.
5. **Revisa penalizaciones.** Si conviertes restricciones a penalidades, justifica sus coeficientes y prueba que las soluciones preferidas no violen las restricciones originales. Una penalización inadecuada puede cambiar el óptimo o producir soluciones inválidas.
6. **Implementa una ejecución pequeña.** Comienza en simulación/primitivas locales; fija semillas cuando sea posible. Si se usa hardware, aplica la skill `ibm-quantum-compute` para autenticar, transpirar y validar el destino.
7. **Decodifica y vuelve a validar.** Convierte los bits a decisiones del problema, comprueba cada restricción original y recalcula el costo desde los datos de entrada. No confíes solo en el valor de energía o en que el conversor devolvió una solución.
8. **Compara de forma justa.** Reporta factibilidad, valor objetivo, brecha frente a la mejor referencia conocida, tiempo o recursos usados, número de variables, shots y variabilidad. Usa las mismas instancias y criterio de parada.
9. **Visualiza.** Muestra problema, ruta/conexiones elegidas, restricciones incumplidas si existen, costo y comparación clásica/cuántica. Incluye un resumen legible y detalles técnicos accesibles.

## Guía de modelado para rutas y conexiones

Para una ruta de costo mínimo, define explícitamente si hay origen/destino, si se permiten ciclos, si todos los puntos deben visitarse y qué restricciones de capacidad/tiempo aplican. Una variable binaria `x[i,j]` puede indicar si se usa la arista de `i` a `j`, y un objetivo típico es minimizar `sum(c[i,j] * x[i,j])`. Las restricciones de grado pueden imponer entradas y salidas, pero en un problema de visita de múltiples ciudades **no eliminan por sí solas los subciclos**. Añade una formulación que trate subtours o limita el alcance del prototipo y dilo.

No supongas que todo problema de rutas equivale a TSP. Si la necesidad es hallar un único camino mínimo con pesos no negativos, un algoritmo clásico de grafos puede ser la referencia más simple y apropiada. Explica por qué se eligió QUBO/QAOA frente a esa alternativa.

## Métricas que deben aparecer

- Costo real de la solución decodificada.
- Factibilidad frente a cada restricción original.
- Mejor solución clásica de referencia y brecha, si se conoce.
- Parámetros de QAOA (por ejemplo, profundidad `p`), shots, semillas y backend/simulador.
- Variación entre corridas si las muestras cambian.
- Tiempo y límites del experimento, con una distinción explícita entre simulación y QPU.

## Límites

- QAOA es un método híbrido aproximado; no garantiza el óptimo global.
- Una solución con menor energía del modelo transformado puede ser inviable si la formulación o las penalizaciones son incorrectas.
- No declares ventaja cuántica por obtener una solución, por dibujar un circuito o por comparar contra un baseline débil.
- Comprueba la API del paquete instalado. En versiones actuales de Qiskit Optimization algunos algoritmos se importan desde `qiskit_optimization.minimum_eigensolvers`; evita rutas de importación históricas sin verificar.

## Referencias oficiales

- [Qiskit Optimization](https://qiskit-community.github.io/qiskit-optimization/)
- [Qiskit Optimization: algoritmos y `QuadraticProgram`](https://qiskit-community.github.io/qiskit-optimization/tutorials/index.html)
- [QAOA y el problema Max-Cut en IBM Quantum Learning](https://learning.quantum.ibm.com/tutorial/quantum-approximate-optimization-algorithm)
- [Qiskit Optimization: notas de versión](https://qiskit-community.github.io/qiskit-optimization/release_notes.html)
