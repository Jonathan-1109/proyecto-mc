# DataStream Networks — Simulador de Optimización para Centros de Datos

Universidad José Antonio Páez · Facultad de Ingeniería · Escuela de Ingeniería en Computación

## Arquitectura de Módulos

El proyecto está compuesto por 3 módulos de optimización y simulación cuantitativa:

- **Módulo 1 (`enrutamiento/` o `enrutamiento_pd/`):** Enrutamiento Dinámico y Asignación de Servidores con **Programación Dinámica (PD)**:
  - *Ruta Más Corta:* Algoritmos de **Floyd-Warshall** y **Bellman por Etapas** con reconstrucción de rutas y recalculo dinámico ante enlaces congestionados o fallas de routers.
  - *Modelo de Volumen-Carga:* Problema de la **Mochila 0/1 y Bounded** mediante tabulación tabular para admisión y maximización del valor de paquetes en servidores.
- **Módulo 2 (`optimizacion/`):** Optimización No Lineal:
  - Análisis consumo/temperatura (puntos estacionarios e inflexión).
  - Ajuste dinámico de potencia de refrigeración por **Método del Gradiente**.
  - Asignación de presupuesto eléctrico mediante **Multiplicadores de Lagrange (KKT)**.
- **Módulo 3 (`simulacion/`):** Simulación estocástica en eventos discretos con **SimPy**, visualización en dashboard interactivo con **Pygame** y generación de reportes ejecutivos en PDF con **Gemini AI**.

### Estructura

```
main.py
enrutamiento/                     # MÓDULO 1: Programación Dinámica
  __init__.py
  modelos.py                     # ItemCarga, ResultadoRuta, ResultadoMochila
  enrutador.py                   # RouterNetwork, DynamicRouter (Floyd-Warshall / Bellman)
  mochila.py                     # KnapsackServerOptimizer (0/1 y Bounded)
  modulo1.py                     # Controlador unificado y benchmarks
enrutamiento_pd/                 # Alias de compatibilidad
  __init__.py
optimizacion/                    # MÓDULO 2: Optimización No Lineal
  __init__.py
  optimizacion.py
simulacion/                      # MÓDULO 3: SimPy + Pygame + ReportLab + Gemini
  defaults.py
  validadores.py
  modelos.py
  puente_matematico.py           # Conexión directa con Módulos 1 y 2
  motor.py
  panel.py
  cliente_ia.py
  informe_pdf.py
  ejecutor.py
data/topology.json
reports/
```

### Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

En Python 3.14+ se usa `pygame-ce` (mismo `import pygame`).

### Configurar Gemini

1. Crea una API key en https://aistudio.google.com/apikey  
2. Copia `.env.example` a `.env` y pega la clave:

```bash
cp .env.example .env
# edita .env:
# GEMINI_API_KEY=tu_clave
# GEMINI_MODEL=gemini-2.0-flash   # opcional
```

Sin clave (o con `--sin-ia`) se usa un análisis local heurístico.

### Uso y Ejecución

#### Probar Módulo 1 (Programación Dinámica):
```bash
python main.py --modulo1
# O ejecutarlo directamente como módulo independiente:
python enrutamiento/modulo1.py
```

#### Probar Módulo 2 (Optimización No Lineal):
```bash
python optimizacion/optimizacion.py
```

#### Ejecutar Simulación Completa (Módulo 3):
```bash
python main.py
python main.py --sin-ventana --duracion 60
python main.py --topologia data/topology.json --tasa-llegada 3.0
python main.py --mostrar-defaults
```

Controles del panel: `SPACE` pausa · `ESC` / `Q` salir.

