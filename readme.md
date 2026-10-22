# DataStream Networks — Simulador de Optimización para Centros de Datos

Universidad José Antonio Páez · Facultad de Ingeniería · Escuela de Ingeniería en Computación

## Módulo 3 (`feature/modulo-3`)

Simulación de eventos discretos (**SimPy**) + panel gráfico (**Pygame**) + informe PDF con análisis **Gemini**.

### Estructura

```
main.py
simulacion/
  defaults.py
  validadores.py
  modelos.py
  puente_matematico.py
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
source .venv/bin/activate
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

### Uso

```bash
python main.py
python main.py --sin-ventana --duracion 60
python main.py --topologia data/topology.json --tasa-llegada 3.0
python main.py --mostrar-defaults
```

Controles del panel: `SPACE` pausa · `ESC` / `Q` salir.
