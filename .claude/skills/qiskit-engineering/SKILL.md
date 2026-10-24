---
name: qiskit-engineering
description: Diseña, explica y revisa soluciones con Qiskit SDK: circuitos, simulación, primitivas, transpilación y resultados reproducibles. Actívala para tareas de programación cuántica general en Qiskit.
---

# Skill: Ingeniería con Qiskit

## Propósito

Ayudar a agentes de IA a construir soluciones cuánticas correctas, comprensibles y reproducibles con Qiskit. Prioriza una formulación verificable y un prototipo ejecutable sobre el uso ornamental de circuitos.

## Cuándo usarla

- El usuario necesita crear, depurar o explicar circuitos cuánticos con Qiskit.
- Hay que elegir entre simulación local, primitivas Qiskit o ejecución en un proveedor.
- Se requiere preparar circuitos para un backend o explicar resultados de medición.

## Procedimiento

1. **Define el trabajo clásico y cuántico.** Resume qué entrada recibe el sistema, qué resultado debe producir y qué componente se pretende ejecutar en un circuito.
2. **Comprueba el entorno existente.** Revisa el entorno virtual, `pyproject.toml`, `requirements.txt` y versiones instaladas antes de proponer instalaciones o cambios. No fijes versiones por conjetura; consulta la instalación oficial y conserva un conjunto compatible.
3. **Elige la abstracción mínima.** Usa `QuantumCircuit` para construir circuitos. Usa `StatevectorSampler` o `StatevectorEstimator` para prototipos ideales locales; recurre a simulación con ruido solo cuando el análisis lo requiera. Para acceso a un proveedor, usa las primitivas que este documente actualmente.
4. **Implementa un flujo pequeño de extremo a extremo.** Incluye preparación, ejecución y lectura de resultados. Mantén los datos clásicos, el circuito y el postprocesamiento separados.
5. **Adapta el circuito al destino.** Para hardware, transpila respecto del backend elegido y revisa conectividad, instrucciones admitidas, profundidad y puertas de dos qubits. No supongas que un circuito abstracto puede enviarse directamente al QPU.
6. **Explica la salida y sus límites.** Distingue una distribución de conteos de una respuesta determinista. Indica shots, semilla cuando aplique, simulador/backend, configuración relevante y fuentes de variabilidad.
7. **Compara con una referencia clásica.** Usa una referencia exacta o heurística apropiada al tamaño del problema y reporta el mismo objetivo, restricciones y condiciones para cada método.

## Selección de primitivas

- **Sampler V2:** cuando la salida requerida son muestras, bits medidos o una distribución empírica.
- **Estimator V2:** cuando la salida requerida son valores esperados de observables sobre estados preparados por circuitos.
- **Primitivas de referencia locales:** para iteración rápida e ideal; no representan automáticamente ruido ni rendimiento de hardware.
- Para otras tareas, comprueba si existe una abstracción mejor documentada en la versión instalada antes de escribir una interfaz de proveedor a mano.

## Criterios de implementación

- Emplea las interfaces actuales de Qiskit; evita tutoriales antiguos que dependan de `QuantumInstance`, `qiskit.opflow` o interfaces V1 sin verificar su estado de soporte.
- Mantén explícito el orden de bits y registros clásicos al interpretar cadenas de medición. Confirma que el decodificador use el mismo convenio que el circuito.
- No infieras ventaja cuántica solo porque el código llame a Qiskit. Describe qué parte es cuántica, qué parte es clásica y qué evidencia respalda la elección.
- No afirmes que simulación de estado vectorial es simulación de hardware ruidoso.
- Trata las semillas como ayuda para reproducir experimentos, no como garantía de resultados idénticos entre versiones, dispositivos o servicios.
- Si el usuario pide código, entrega una solución coherente con el repositorio y sus convenciones, junto con las dependencias y pasos mínimos para ejecutarla.

## Entrega que debe producir el agente

Cuando corresponda, resume: objetivo, enfoque, archivos o módulos, cómo ejecutar el flujo, qué resultado esperar, comparación clásica y limitaciones. Si falta una decisión que impide avanzar, señala la suposición adoptada con claridad.

## Referencias oficiales

- [Qiskit SDK: documentación y API](https://quantum.cloud.ibm.com/docs/en/api/qiskit)
- [Primitivas de Qiskit](https://quantum.cloud.ibm.com/docs/en/guides/primitives)
- [Introducción a la transpilación](https://quantum.cloud.ibm.com/docs/en/guides/transpile)
- [Qiskit: instalación](https://quantum.cloud.ibm.com/docs/en/guides/install-qiskit)
