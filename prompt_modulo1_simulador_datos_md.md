Actúa como un desarrollador senior en Python especializado en Métodos Cuantitativos, Programación Dinámica y Optimización de Algoritmos.

Necesito desarrollar e integrar el **Módulo 1** de un proyecto universitario existente en Python para la materia Métodos Cuantitativos (Universidad José Antonio Páez). El proyecto general es un **Simulador de Optimización para Redes de Centros de Datos (Cloud Computing)**.

### Estado Actual del Proyecto:

Ya cuento con los Módulos 2 y 3 implementados:

- **Módulo 2 (Optimización No Lineal):** Análisis de consumo/temperatura (puntos estacionarios), ajuste dinámico de refrigeración (Método del Gradiente) y asignación de presupuesto eléctrico (Multiplicadores de Lagrange).
- **Módulo 3 (Simulación y Interfaz):** Simulación estocástica en `SimPy` (llegadas aleatorias, colas, fallas), API de IA para reportes PDF y visualización en dashboard interactivo con `Pygame`.

---

### Requerimientos para el Módulo 1:

Debes generar el código correspondiente al **Módulo 1: Enrutamiento de Datos y Asignación de Servidores**, aplicando los principios de **Programación Dinámica (PD)** y siguiendo estrictamente el paradigma de **Programación Orientada a Objetos (POO)**.

El módulo consta de dos componentes principales:

1. **Determinación de la Ruta Más Corta (Programación Dinámica):**
   - Implementar un algoritmo de Programación Dinámica (por ejemplo, el algoritmo de Floyd-Warshall o Dijkstra basado en subproblemas superpuestos/memoización o formulación por etapas de PD) para encontrar el camino óptimo (menor latencia) que deben seguir los paquetes de datos a través de los nodos/routers de la red.
   - Debe soportar recalculado dinámico de pesos cuando un enlace esté congestionado (para conectarse dinámicamente con las alertas visuales de Pygame del Módulo 3).

2. **Modelo de Volumen-Carga (Problema de la Mochila / Knapsack Problem 0/1 o Bounded):**
   - Aplicar la técnica de Programación Dinámica para resolver el problema de la mochila donde:
     - **Capacidad de la Mochila:** Capacidad máxima de procesamiento del servidor (volumen de CPU/RAM).
     - **Objetos (Paquetes/Tareas):** Representan cargas entrantes con requisitos de recursos (peso/volumen) y prioridades o valores asignados (beneficio).
   - Debe retornar la combinación óptima de paquetes a procesar para maximizar el valor total procesado sin exceder la capacidad del servidor.

---

### Requisitos Técnicos y Pautas de Evaluación:

1. **Estructura POO Limpia e Independiente:** Crear clases descriptivas (ejemplo: `RouterNetwork`, `DynamicRouter`, `KnapsackServerOptimizer` o similar) con alta cohesión y bajo acoplamiento para facilitar su importación en la simulación de `SimPy` y `Pygame`.
2. **Validación de Datos:** Incluir validaciones robustas para evitar errores de ejecución (tipos de datos, rangos, capacidades negativas, etc.).
3. **Datos por Defecto / Pruebas Automáticas:** Incluir una sección con datos predeterminados (benchmarks) dentro del módulo o bajo el bloque `if __name__ == '__main__':` para probar y validar su funcionamiento de forma independiente.
4. **Legibilidad y Documentación:**
   - Docstrings descriptivos en clases y métodos.
   - Comentarios explicativos sobre las ecuaciones o lógica de Programación Dinámica (tabulación/memoización).
   - Nombres de variables autoexplicativos y limpios (Clean Code).

---

### Lo que debes entregar:

1. El código Python completo para el Módulo 1 integrado dentro de los modulos ya creados
