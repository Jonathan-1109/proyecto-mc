from __future__ import annotations

from typing import Any

DURACION_SIM_DEFECTO: float = 120.0
TASA_LLEGADA_DEFECTO: float = 2.5
SEMILLA_DEFECTO: int = 42
TASA_FALLA_DEFECTO: float = 0.008
TASA_RECUPERACION_DEFECTO: float = 0.20
INTERVALO_OPT_DEFECTO: float = 1.0
PRESUPUESTO_ENERGIA_DEFECTO: float = 100.0
FPS_DEFECTO: int = 30
TAMANO_VENTANA_DEFECTO: tuple[int, int] = (1280, 720)

TOPOLOGIA_DEFECTO: dict[str, Any] = {
    "nodos": [
        {"id": "GW", "tipo": "puerta", "x": 0.08, "y": 0.50, "capacidad": 0},
        {"id": "R1", "tipo": "router", "x": 0.28, "y": 0.28, "capacidad": 0},
        {"id": "R2", "tipo": "router", "x": 0.28, "y": 0.72, "capacidad": 0},
        {"id": "R3", "tipo": "router", "x": 0.52, "y": 0.50, "capacidad": 0},
        {"id": "S1", "tipo": "servidor", "x": 0.78, "y": 0.22, "capacidad": 32, "cluster": 0},
        {"id": "S2", "tipo": "servidor", "x": 0.78, "y": 0.50, "capacidad": 48, "cluster": 1},
        {"id": "S3", "tipo": "servidor", "x": 0.78, "y": 0.78, "capacidad": 40, "cluster": 2},
    ],
    "enlaces": [
        ("GW", "R1", 8.0),
        ("GW", "R2", 10.0),
        ("R1", "R3", 6.0),
        ("R2", "R3", 5.0),
        ("R1", "S1", 12.0),
        ("R3", "S1", 9.0),
        ("R3", "S2", 7.0),
        ("R2", "S3", 11.0),
        ("R3", "S3", 8.0),
        ("R1", "R2", 14.0),
    ],
}

PERFILES_PAQUETE_DEFECTO: list[dict[str, Any]] = [
    {"nombre": "control", "tamano": 2, "prioridad": 9, "media_proc": 0.4},
    {"nombre": "web", "tamano": 6, "prioridad": 5, "media_proc": 1.0},
    {"nombre": "lote", "tamano": 14, "prioridad": 2, "media_proc": 2.2},
    {"nombre": "analitica", "tamano": 10, "prioridad": 4, "media_proc": 1.6},
]

CLUSTERS_DEFECTO: list[str] = ["borde-a", "borde-b", "borde-c"]


def como_diccionario() -> dict[str, Any]:
    return {
        "duracion_sim": DURACION_SIM_DEFECTO,
        "tasa_llegada": TASA_LLEGADA_DEFECTO,
        "semilla": SEMILLA_DEFECTO,
        "tasa_falla": TASA_FALLA_DEFECTO,
        "tasa_recuperacion": TASA_RECUPERACION_DEFECTO,
        "intervalo_opt": INTERVALO_OPT_DEFECTO,
        "presupuesto_energia": PRESUPUESTO_ENERGIA_DEFECTO,
        "fps": FPS_DEFECTO,
        "tamano_ventana": TAMANO_VENTANA_DEFECTO,
        "topologia": TOPOLOGIA_DEFECTO,
        "perfiles_paquete": PERFILES_PAQUETE_DEFECTO,
        "clusters": list(CLUSTERS_DEFECTO),
    }
