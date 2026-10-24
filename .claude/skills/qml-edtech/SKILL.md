---
name: qml-edtech
description: Diseña experiencias didácticas interactivas para enseñar estadística, machine learning y sus conexiones con QML usando Qiskit Machine Learning. Actívala para retos educativos o prototipos de aprendizaje cuántico.
---

# Skill: QML y EdTech interactivo

## Propósito

Diseñar experiencias que enseñen un concepto estadístico o de machine learning y permitan experimentar con un equivalente o extensión cuántica. La interacción debe crear ganas de volver por el progreso y el descubrimiento, sin ocultar limitaciones ni presentar QML como superior por defecto.

## Cuándo usarla

- El usuario crea un juego, simulador, app o herramienta educativa de computación cuántica.
- Se quiere conectar distribuciones, SVM, Monte Carlo, redes neuronales o descenso de gradiente con QML.
- Debe diseñarse una metodología y una demo atractiva para el reto EdTech del Qiskit Fall Fest 2026.

## Procedimiento de diseño

1. **Elige un único objetivo de aprendizaje.** Exprésalo como una acción comprobable, por ejemplo: “el usuario compara cómo cambia la frontera de decisión al sustituir el kernel”.
2. **Define audiencia y conocimientos previos.** Aclara edad aproximada, familiaridad con probabilidad/código y modo de uso. No declares una edad mínima sin pruebas con usuarios y revisión de accesibilidad.
3. **Parte de una versión clásica intuitiva.** Permite que el usuario vea datos, controles, resultado y explicación antes de introducir la parte cuántica.
4. **Mapea con precisión.** Describe qué pieza clásica se reemplaza o modifica: embedding/feature map, kernel cuántico, QNN, circuito de muestreo u otro componente. Distingue analogía didáctica de equivalencia matemática.
5. **Crea un ciclo breve de interacción.** Una secuencia útil es: elegir una configuración → ejecutar → observar resultado → recibir explicación/retroalimentación → probar un reto ligeramente distinto.
6. **Haz visible el aprendizaje.** Incluye predicciones del usuario, visualización de estados/distribuciones o errores, pistas progresivas y una recapitulación que nombre el concepto aprendido.
7. **Implementa una demo fiable.** Usa datos pequeños y deterministas, precalcula resultados si hay restricciones de cómputo, y ofrece una ruta de simulación local. No dependas de acceso a QPU en vivo para que el núcleo pedagógico funcione.
8. **Valida el diseño.** Prueba con personas representativas; observa si pueden completar la tarea y explicar qué cambió. Mide finalización, comprensión y retorno voluntario; no equipares clics o tiempo de pantalla con aprendizaje.
9. **Documenta evaluación y accesibilidad.** Incluye instrucciones claras, alternativas a color, texto para elementos visuales, navegación por teclado cuando corresponda y un modo de ayuda.

## Componentes QML disponibles

- **Kernel cuántico:** Qiskit Machine Learning ofrece `FidelityQuantumKernel`, que puede emplearse con `QSVC`/`QSVR` o métodos clásicos compatibles. Enseña qué mide la matriz del kernel y permite compararla con un kernel clásico.
- **Red neuronal cuántica:** `EstimatorQNN` produce valores esperados a partir de un circuito parametrizado y observables; `SamplerQNN` usa salidas muestreadas. Para clasificación/regresión hay interfaces de alto nivel como `VQC` y `VQR`.
- **Integración con PyTorch:** `TorchConnector` permite integrar QNNs en modelos de PyTorch cuando el caso la justifica.

Verifica compatibilidad de paquetes y ejemplos en la versión instalada antes de generar imports o APIs. No es necesario usar hardware real para enseñar el concepto.

## Patrón de comparación pedagógica

Para cada modo clásico/cuántico, presenta:

1. el mismo conjunto de datos o una comparación claramente justificada;
2. qué operación realiza cada método;
3. salida visible (distribución, kernel, frontera, pérdida o predicción);
4. qué parámetros puede cambiar el usuario;
5. una medición simple de rendimiento y sus límites.

No atribuyas mejoras a un método cuando provienen de una diferencia de datos, presupuesto de entrenamiento o hiperparámetros. En QML, comenta cuando sea relevante el tamaño pequeño del experimento, el costo de muestreo, el entrenamiento y la ausencia de evidencia de ventaja práctica.

## Retención responsable

- Recompensa exploración, dominio y comprensión: niveles, desafíos cortos, visualización de progreso y nuevas preguntas.
- Deja que el usuario controle el ritmo; no uses pérdida artificial de progreso, rachas punitivas, notificaciones coercitivas ni azar opaco para forzar sesiones.
- Una experiencia “adictiva” para este reto debe entenderse como atractiva y voluntariamente reutilizable, sin manipular al usuario.
- Recomienda intervalos de uso basados en pruebas del prototipo, no como afirmaciones clínicas o universales.

## Entrega del agente

Describe público, objetivo de aprendizaje, flujo interactivo, mapeo clásico→cuántico, componentes Qiskit, datos, método de evaluación, límites y una demo concreta que pueda mostrarse en pocos minutos.

## Referencias oficiales

- [Qiskit Machine Learning: descripción y componentes](https://qiskit-community.github.io/qiskit-machine-learning/)
- [Tutoriales de Qiskit Machine Learning](https://qiskit-community.github.io/qiskit-machine-learning/tutorials/index.html)
- [Guía de instalación de Qiskit Machine Learning](https://qiskit-community.github.io/qiskit-machine-learning/getting_started.html)
