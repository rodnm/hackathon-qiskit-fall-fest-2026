---
name: ibm-quantum-compute
description: Prepara y explica ejecuciones de Qiskit en IBM Quantum Compute Service, incluidas autenticación segura, selección de backend, primitivas, ISA y límites del hardware. Actívala para IBM Quantum o Qiskit Runtime.
---

# Skill: IBM Quantum Compute Service

## Propósito

Guiar el uso responsable del cliente `qiskit-ibm-runtime` y del servicio administrado de cómputo cuántico de IBM. En documentación y productos actuales, el servicio administrado se denomina **IBM Quantum Compute Service**; IBM Qiskit Runtime también puede referirse al entorno de ejecución del QPU. No mezcles esos componentes.

## Cuándo usarla

- El usuario quiere ejecutar un circuito en un QPU de IBM.
- Necesita autenticación, selección de instancia/backend, primitivas o preparación ISA.
- Debe comparar ejecución local y remota, interpretar colas, ruido o resultados.

## Flujo operativo

1. **Verifica acceso y entorno.** Consulta la documentación vigente para el método de acceso, plan, instancia y cliente. El nombre del paquete cliente es `qiskit-ibm-runtime`. No supongas que una cuenta tiene acceso a un QPU o cuota disponibles.
2. **Protege credenciales.** Usa los mecanismos oficiales de autenticación y almacenamiento local seguro. No solicites ni imprimas tokens, no los incluyas en código, notebooks, logs, capturas, repositorios ni variables versionadas. Si una credencial aparece expuesta, aconseja revocarla y regenerarla.
3. **Elige el backend deliberadamente.** Consulta recursos disponibles y sus propiedades actuales; valida el objetivo del usuario, el tamaño del circuito, compatibilidad y límites de ejecución. Nunca inventes nombres de backend ni prometas disponibilidad o tiempo de cola.
4. **Desarrolla primero fuera del QPU.** Comprueba el circuito con primitivas locales o simulador. Separa errores de algoritmo de efectos de ruido y del entorno remoto.
5. **Transpila al ISA del destino.** Usa el backend como objetivo al generar un pass manager, transpila el circuito, transpila o adapta también los observables cuando aplique, y revisa layout, conectividad, profundidad y puertas de dos qubits. IBM requiere que los circuitos enviados al backend respeten su ISA.
6. **Selecciona la primitiva adecuada.** Usa `SamplerV2` para muestras medidas y `EstimatorV2` para valores esperados. IBM documenta también `Executor` en beta: úsalo solo si el problema necesita su control adicional, la cuenta lo permite y la documentación actual lo confirma.
7. **Ejecuta con alcance acotado.** Envía un trabajo pequeño primero. Usa modo job para una ejecución aislada; considera session para iteraciones relacionadas y batch para colecciones de trabajos cuando sean adecuados y estén disponibles en la cuenta.
8. **Registra y explica.** Conserva identificador de trabajo, backend, parámetros relevantes, shots/precisión, fecha y resultados no sensibles. Distingue mediciones observadas de una garantía determinista y describe la variabilidad del hardware.

## Patrones de API

Las primitivas actuales son V2. Al mostrar código, sigue los imports, argumentos PUB, opciones y estructura de resultados de la documentación instalada. Como referencia, el patrón conceptual es:

```python
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

service = QiskitRuntimeService()
backend = service.backend("<backend_disponible_en_la_cuenta>")
sampler = SamplerV2(mode=backend)
job = sampler.run([circuit], shots=1024)
result = job.result()
```

El marcador de backend no es un nombre válido; reemplázalo únicamente después de consultar los recursos disponibles. Para `EstimatorV2`, aporta un circuito, observables y, si aplica, valores de parámetros según la interfaz actual. No copies código de `backend.run`, primitivas V1 o ejemplos antiguos sin verificar migración y compatibilidad.

## Reglas y límites

- No afirmes que el servicio ejecuta un algoritmo íntegramente en el QPU: optimización clásica, preparación y postprocesamiento pueden ocurrir en el cliente.
- No prometas ventaja cuántica, tolerancia a fallos ni resultados exactos por usar un QPU.
- No actives mitigación, twirling, precisión o shots sin explicar costo, efecto y compatibilidad; verifica las opciones vigentes.
- No asumas que las opciones son iguales entre `SamplerV2`, `EstimatorV2`, `Executor` o versiones del cliente.
- Si no hay credenciales, cuota o conectividad, deja una ruta de simulación local reproducible y anota qué parte queda pendiente de validar en hardware.

## Referencias oficiales

- [IBM Quantum primitives: Estimator, Sampler y Executor](https://quantum.cloud.ibm.com/docs/en/guides/qiskit-runtime-primitives)
- [Instalar el cliente IBM Quantum Compute](https://quantum.cloud.ibm.com/docs/en/guides/install-qiskit-runtime)
- [Guía de transpilación](https://quantum.cloud.ibm.com/docs/en/guides/transpile)
- [Changelog del servicio y cambios de nomenclatura](https://quantum.cloud.ibm.com/docs/en/guides/changelog-quantum-compute-service)
