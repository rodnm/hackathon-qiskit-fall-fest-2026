# GateFlow Quantum — Recomendaciones técnicas y arquitectura del MVP

> **Proyecto de hackathon:** asignación de vuelos de conexión a puertas de embarque mediante optimización clásica y una demostración de optimización cuántica.
>
> **Equipo:** The Explorers  
> **Objetivo:** construir una demostración reproducible, comprensible y desplegable en Docker, sin afirmar una ventaja cuántica que no se haya demostrado.

## 1. Resumen ejecutivo

El reto consiste en asignar diez vuelos a diez puertas de embarque. Los vuelos que comparten muchos pasajeros en conexión deberían ubicarse en puertas cercanas para reducir la distancia total recorrida.

El problema se modela como un **Quadratic Assignment Problem (QAP)**. La recomendación para el MVP es implementar:

1. Un solucionador clásico para la instancia completa de **10 vuelos × 10 puertas**.
2. Una formulación QUBO y una ejecución de **QAOA con Qiskit Aer** para una instancia reducida, por ejemplo, **4 vuelos × 4 puertas**.
3. Una interfaz web que permita visualizar las matrices, ejecutar ambos enfoques y comparar sus resultados.
4. Una aplicación empaquetada en Docker Compose para desplegarla en un servidor.

**Criterio de honestidad técnica:** la instancia reducida demuestra el flujo cuántico, pero no prueba que QAOA sea más rápido ni mejor que el método clásico en el problema completo.

## 2. Formulación matemática

### 2.1 Datos

- \(F_{ik}\): cantidad o peso de pasajeros que conectan entre los vuelos \(i\) y \(k\).
- \(D_{jl}\): distancia entre las puertas \(j\) y \(l\).
- \(x_{ij}\): variable binaria que vale 1 si el vuelo \(i\) se asigna a la puerta \(j\), y 0 en caso contrario.

### 2.2 Función objetivo

Minimizar la distancia total ponderada de los pasajeros en conexión:

\[
\min \sum_i \sum_k \sum_j \sum_l F_{ik}D_{jl}x_{ij}x_{kl}
\]

### 2.3 Restricciones de asignación

Cada vuelo recibe exactamente una puerta:

\[
\sum_j x_{ij}=1 \quad \forall i
\]

Cada puerta se asigna a exactamente un vuelo:

\[
\sum_i x_{ij}=1 \quad \forall j
\]

\[
x_{ij}\in\{0,1\}
\]

Antes de optimizar, validar dimensiones, valores numéricos, simetría cuando corresponda, unidades y consistencia de las matrices.

## 3. Arquitectura recomendada

```text
┌───────────────────────────────────────────────┐
│             Frontend React + Vite             │
│ Matrices F/D · Configuración · Resultados      │
└──────────────────────┬────────────────────────┘
                       │ HTTP / JSON
┌──────────────────────▼────────────────────────┐
│                Backend FastAPI                │
│ Validación · Objetivo · API · Métricas         │
├──────────────────────┬────────────────────────┤
│ Solucionador clásico │ Módulo cuántico         │
│ SciPy / búsqueda     │ Qiskit Optimization     │
│ local / heurística   │ QAOA + Qiskit Aer       │
└──────────────────────┴────────────────────────┘
                       │
               Docker Compose
```

### Stack sugerido

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Frontend | React + Vite + TypeScript | Interfaz y visualización |
| Gráficos | Recharts (opcional) | Comparación de resultados |
| Backend | Python + FastAPI + Pydantic | API y validación |
| Cálculo clásico | NumPy + SciPy y/o búsqueda local | Resolver 10×10 |
| Optimización cuántica | Qiskit Optimization | Modelado del problema |
| Algoritmo cuántico | QAOA | Demostración de optimización aproximada |
| Simulador | Qiskit Aer | Simulación en CPU para instancia pequeña |
| Despliegue | Docker Compose | Ejecución reproducible |

No se recomienda incorporar una base de datos, Redis, Celery ni microservicios adicionales para el MVP salvo que exista una necesidad concreta.

## 4. Estrategia de resolución

### 4.1 Instancia completa: 10×10

Usar el solucionador clásico para obtener una solución de referencia en el tiempo disponible.

Opciones:

- Búsqueda local con intercambios de asignaciones.
- Recocido simulado.
- Búsqueda multiarranque para reducir la dependencia de una única solución inicial.
- Enumeración optimizada, si se comprueba que cabe en el presupuesto de tiempo.

Existen \(10! = 3\,628\,800\) permutaciones posibles. Es una cantidad finita y potencialmente abordable con una implementación optimizada, pero no conviene depender de una enumeración ingenua durante una hackathon. Medir siempre el tiempo real.

### 4.2 Instancia cuántica reducida: 4×4

Formular la instancia como QUBO, incorporando las restricciones de asignación mediante penalizaciones. Ejecutar QAOA en Qiskit Aer y comparar con el óptimo clásico de **la misma instancia 4×4**.

La formulación one-hot utiliza \(n^2\) variables binarias:

| Tamaño | Variables binarias | Evaluación práctica |
|---|---:|---|
| 4×4 | 16 | Buen punto de partida para simulación |
| 5×5 | 25 | Puede consumir bastante memoria/tiempo según método y configuración |
| 10×10 | 100 | La simulación exacta tipo statevector resulta impráctica en hardware convencional |

El coste de una simulación statevector crece exponencialmente con el número de qubits. La viabilidad real depende del método de simulación, profundidad del circuito, memoria disponible y parámetros de QAOA.

### 4.3 Cómo comparar correctamente

Mostrar por separado:

- Valor de la función objetivo original.
- Tiempo de ejecución medido.
- Si la asignación cumple todas las restricciones.
- Mejor solución factible encontrada.
- Frecuencia o proporción de muestras factibles en QAOA, si está disponible.
- Brecha respecto al óptimo clásico en la instancia reducida.

**Importante:** la energía QUBO puede incluir penalizaciones. Para comparar resultados, volver a calcular la función objetivo original sobre cada asignación y verificar su factibilidad. No presentar la energía penalizada como si fuera directamente el coste de distancia.

No afirmar “ventaja cuántica”, “supremacía cuántica” ni aceleración si no existe evidencia experimental apropiada.

## 5. Diseño funcional del MVP

### Pantalla principal

1. **Datos del problema**
   - Matriz de flujo \(F\).
   - Matriz de distancias \(D\).
   - Datos de ejemplo precargados.
   - Validación de dimensiones y valores.

2. **Configuración**
   - Tamaño de la instancia.
   - Solucionador clásico o QAOA.
   - Parámetros básicos de QAOA, con valores predeterminados seguros.

3. **Resultados**
   - Tabla vuelo → puerta asignada.
   - Coste total de distancia ponderada.
   - Tiempo de ejecución.
   - Estado de factibilidad.
   - Comparación clásico/cuántica para la misma instancia.
   - Distribución de muestras QAOA, si puede obtenerse de forma fiable.

4. **Transparencia**
   - Indicar claramente el tamaño de la instancia.
   - Identificar si el resultado es óptimo conocido o mejor solución encontrada.
   - Mostrar errores de validación y de ejecución sin ocultarlos.

### Endpoints sugeridos

| Método | Endpoint | Función |
|---|---|---|
| GET | `/api/health` | Verificar disponibilidad |
| POST | `/api/validate` | Validar matrices y restricciones |
| POST | `/api/optimize/classical` | Resolver la instancia clásica |
| POST | `/api/optimize/qaoa` | Ejecutar QAOA para instancias compatibles |

Usar modelos Pydantic para validar entradas y salidas. Limitar el tamaño de la instancia cuántica en el servidor para evitar ejecuciones que excedan los recursos.

## 6. Estructura sugerida del repositorio

```text
gateflow-quantum/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
│           └── api.ts
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py
        ├── schemas.py
        ├── objective.py
        ├── classical_solver.py
        ├── quantum_solver.py
        └── sample_data.py
```

La estructura puede ajustarse al código real. No crear archivos vacíos o módulos innecesarios solo para cumplir con el árbol.

## 7. Docker y despliegue

Para desarrollo y despliegue, usar Docker Compose con dos servicios:

- `frontend`: compila React/Vite y sirve los archivos estáticos mediante Nginx.
- `backend`: ejecuta FastAPI y los solucionadores.

El frontend debe invocar la API mediante una URL configurable y el backend debe permitir únicamente los orígenes CORS necesarios.

Si el requisito operativo exige estrictamente **un solo contenedor**, se puede servir el frontend compilado desde FastAPI. Para desarrollo y mantenimiento, dos servicios en un mismo `docker-compose.yml` suelen ser más claros, aunque el despliegue sigue siendo una sola aplicación.

Buenas prácticas:

- Fijar versiones compatibles de las dependencias.
- Ejecutar el proceso como usuario no root cuando sea viable.
- Añadir health checks y límites razonables de recursos.
- No incluir claves API ni secretos en el repositorio.
- Documentar cómo construir, iniciar y detener la aplicación.
- Probar el despliegue desde un entorno limpio antes de la presentación.

## 8. Uso eficiente de las herramientas de IA

Concentrar el trabajo en una herramienta principal de programación y usar una segunda para revisión crítica. Evitar cambiar constantemente de proveedor o modelo durante las seis horas.

Flujo sugerido:

1. **Planificación:** pedir a un modelo que revise el alcance y proponga interfaces entre módulos.
2. **Implementación:** utilizar la herramienta de programación principal para generar y modificar el código.
3. **Revisión:** usar otro modelo para buscar errores matemáticos, fallos de factibilidad, problemas de Docker y afirmaciones exageradas.
4. **Validación humana:** ejecutar las pruebas reales, revisar las salidas y comprobar que el demo funciona.

No pegar claves, credenciales, datos sensibles ni secretos en los prompts. Confirmar que cualquier código generado se ejecuta y se entiende antes de incorporarlo.

## 9. Plan de trabajo para una hackathon de seis horas

| Hora | Actividad | Entregable |
|---|---|---|
| 10:00–10:20 | Comprender el reto y definir el alcance | Objetivo y criterios de éxito |
| 10:20–10:40 | Diseñar módulos y contratos de API | Interfaces acordadas |
| 10:40–12:15 | Desarrollo en paralelo | Backend clásico, frontend y prueba QAOA |
| 12:15–12:30 | Integración parcial | Primer flujo ejecutable |
| 12:30–13:00 | Almuerzo | Pausa |
| 13:00–14:00 | Integrar y validar | Flujo de punta a punta |
| 14:00–14:40 | Congelar funcionalidades y reunir evidencia | Versión candidata |
| 14:40–15:20 | Preparar presentación | Historia y resultados |
| 15:20–15:40 | Ensayar la demostración | Demo ensayada |
| 15:40–16:00 | Margen para fallos y entrega | Entrega final |

### Distribución de responsabilidades sugerida

- **Líder / arquitectura:** delimitar el MVP, coordinar contratos, integrar y preparar la narrativa.
- **Investigación y datos:** preparar matrices, definir métricas, validar el coste y construir la referencia clásica.
- **Desarrollo de algoritmo:** formular QUBO, implementar QAOA y verificar restricciones.
- **Integración, pruebas y seguridad:** Docker, pruebas de API, integración, documentación y respaldo de la demo.

Las responsabilidades deben adaptarse a las fortalezas reales de cada integrante. Mantener una única persona responsable de la integración final.

## 10. Pruebas mínimas antes de presentar

- [ ] Las matrices tienen dimensiones compatibles.
- [ ] Los datos inválidos se rechazan con mensajes claros.
- [ ] Toda solución presentada asigna exactamente una puerta por vuelo.
- [ ] Ninguna puerta se asigna a más de un vuelo.
- [ ] El coste se calcula de nuevo con la función objetivo original.
- [ ] El solucionador clásico funciona en la instancia 10×10 de demostración.
- [ ] QAOA se ejecuta en una instancia reducida y sus resultados se registran.
- [ ] La comparación cuántica y clásica usa exactamente los mismos datos reducidos.
- [ ] Se miden los tiempos, en vez de inventarlos o estimarlos para la presentación.
- [ ] Docker Compose arranca desde un estado limpio.
- [ ] Existe un conjunto de datos de ejemplo reproducible.
- [ ] Hay capturas o resultados de respaldo por si falla la conexión o el simulador durante la demo.

## 11. Guion de presentación

1. **Problema:** las asignaciones de puertas afectan las distancias recorridas por pasajeros en conexión.
2. **Modelo:** el QAP representa los flujos entre vuelos y las distancias entre puertas.
3. **Solución clásica:** resolver la instancia completa de 10×10 y mostrar la asignación obtenida.
4. **Demostración cuántica:** ejecutar QAOA en una instancia reducida y compararla con el óptimo clásico de ese mismo caso.
5. **Resultados:** mostrar coste, factibilidad y tiempo medidos.
6. **Limitaciones y siguiente paso:** estudiar instancias mayores, mejores formulaciones, parámetros y hardware cuántico disponible.

La fortaleza de la demostración es mostrar un flujo reproducible y una comparación justa, no prometer una ventaja cuántica que el experimento no acredita.

## 12. Fuentes oficiales

- **Qiskit Aer:** https://qiskit.github.io/qiskit-aer/
- **Tutorial de QAOA:** https://qiskit.qotlabs.org/docs/tutorials/quantum-approximate-optimization-algorithm
- **Qiskit Optimization:** https://qiskit-community.github.io/qiskit-optimization/
- **FastAPI:** https://fastapi.tiangolo.com/
- **React:** https://react.dev/
- **Vite:** https://vite.dev/
- **Docker Compose:** https://docs.docker.com/compose/

Consulta la documentación vigente antes de fijar versiones, ya que las APIs y dependencias pueden cambiar.

---

## Definición de “listo” para el MVP

El MVP se considera listo cuando un usuario puede cargar o seleccionar matrices, ejecutar el solucionador clásico para 10×10, ejecutar QAOA para una instancia reducida, ver asignaciones factibles y costes recalculados, comparar los resultados con sus tiempos medidos y levantar todo el sistema mediante Docker Compose siguiendo el README.
