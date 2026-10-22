from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class ItemCarga:
    """Representa una tarea o paquete de datos entrante que compite por recursos del servidor.

    Atributos:
        id_item: Identificador único del paquete/tarea.
        peso: Requerimiento de recursos (volumen CPU / memoria RAM). Debe ser > 0.
        valor: Beneficio, prioridad o valor de negocio obtenido al procesar la tarea. Debe ser >= 0.
        limite: Para el problema de mochila acotada (Bounded Knapsack), número máximo de instancias disponibles.
        metadatos: Información contextual opcional (ej. tipo de servicio, cliente, SLA).
    """

    id_item: str
    peso: float
    valor: float
    limite: int = 1
    metadatos: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.peso <= 0:
            raise ValueError(f"El peso del ítem '{self.id_item}' debe ser estrictamente positivo (recibido: {self.peso})")
        if self.valor < 0:
            raise ValueError(f"El valor del ítem '{self.id_item}' no puede ser negativo (recibido: {self.valor})")
        if self.limite < 1:
            raise ValueError(f"El límite de instancias para '{self.id_item}' debe ser al menos 1 (recibido: {self.limite})")


# Alias en inglés sugerido en los requerimientos
KnapsackItem = ItemCarga


@dataclass
class ResultadoMochila:
    """Resultado detallado de la optimización del problema de la mochila por Programación Dinámica."""

    items_seleccionados: list[ItemCarga]
    items_rechazados: list[ItemCarga]
    valor_total: float
    peso_total: float
    capacidad_servidor: float
    capacidad_remanente: float
    porcentaje_utilizacion: float
    tabla_dp: np.ndarray
    metodo: str
    tiempo_ejecucion_ms: float = 0.0

    def resumen(self) -> dict[str, Any]:
        return {
            "metodo": self.metodo,
            "capacidad_servidor": self.capacidad_servidor,
            "peso_total": round(self.peso_total, 4),
            "capacidad_remanente": round(self.capacidad_remanente, 4),
            "valor_total": round(self.valor_total, 4),
            "porcentaje_utilizacion": f"{self.porcentaje_utilizacion:.2f}%",
            "seleccionados": [item.id_item for item in self.items_seleccionados],
            "rechazados": [item.id_item for item in self.items_rechazados],
            "dimensiones_tabla_dp": list(self.tabla_dp.shape),
        }


# Alias en inglés
KnapsackResult = ResultadoMochila


@dataclass
class ResultadoRuta:
    """Resultado del cálculo de ruta óptima mediante Programación Dinámica."""

    origen: str
    destino: str
    ruta: list[str]
    latencia_total: float
    num_saltos: int
    es_factible: bool
    congestiones_enlaces: dict[tuple[str, str], float] = field(default_factory=dict)
    etapas_bellman: list[dict[str, Any]] = field(default_factory=list)
    metodo: str = "Floyd-Warshall"

    def resumen(self) -> dict[str, Any]:
        return {
            "origen": self.origen,
            "destino": self.destino,
            "ruta": " → ".join(self.ruta) if self.ruta else "Sin ruta",
            "latencia_total": round(self.latencia_total, 4) if self.es_factible else float("inf"),
            "num_saltos": self.num_saltos,
            "es_factible": self.es_factible,
            "metodo": self.metodo,
        }


# Alias en inglés
RouteResult = ResultadoRuta
