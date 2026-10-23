# DataStream Networks — Simulador de Optimización para Centros de Datos

Universidad José Antonio Páez · Facultad de Ingeniería · Escuela de Ingeniería en Computación

## Arquitectura

| Módulo | Carpeta | Rol |
|--------|---------|-----|
| 1 | `enrutamiento/` | Ruta más corta (PD) + mochila volumen-carga |
| 2 | `optimizacion/` | Temperatura, gradiente de refrigeración, Lagrange |
| 3 | `simulacion/` | SimPy + Pygame + Gemini/PDF |

La unión vive en `simulacion/puente_matematico.py`: el motor de simulación llama a M1/M2 en tiempo real.

### Estructura

```
main.py
integracion.py                   # verificación M1+M2+M3
enrutamiento/                    # Módulo 1
optimizacion/                    # Módulo 2
simulacion/                      # Módulo 3 (+ puente)
data/topology.json
reports/
```

### Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # GEMINI_API_KEY=...
```

### Uso

```bash
# Verificar unión completa
python main.py --verificar
# o: python integracion.py

# Demos por módulo
python main.py --modulo1
python main.py --modulo2

# Simulación integrada (dashboard)
python main.py

# Simulación sin ventana + PDF
python main.py --sin-ventana --duracion 60
```

Controles del panel: `SPACE` pausa · `ESC` / `Q` salir.
