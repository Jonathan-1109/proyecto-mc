from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import uuid


class TipoNodo(str, Enum):
    PUERTA = "puerta"
    ROUTER = "router"
    SERVIDOR = "servidor"


class EstadoNodo(str, Enum):
    ACTIVO = "activo"
    CAIDO = "caido"


@dataclass
class Paquete:
    id_paquete: str
    nombre: str
    tamano: float
    prioridad: int
    media_proc: float
    creado_en: float
    ruta: list[str] = field(default_factory=list)
    salto_actual: int = 0
    servidor_asignado: str | None = None
    estado: str = "creado"
    completado_en: float | None = None

    @classmethod
    def crear(
        cls,
        nombre: str,
        tamano: float,
        prioridad: int,
        media_proc: float,
        creado_en: float,
    ) -> "Paquete":
        return cls(
            id_paquete=str(uuid.uuid4())[:8],
            nombre=nombre,
            tamano=tamano,
            prioridad=prioridad,
            media_proc=media_proc,
            creado_en=creado_en,
        )

    @property
    def progreso(self) -> float:
        if not self.ruta:
            return 0.0
        if self.salto_actual >= len(self.ruta) - 1:
            return 1.0
        return self.salto_actual / max(1, len(self.ruta) - 1)


@dataclass
class NodoRed:
    id_nodo: str
    tipo: TipoNodo
    x: float
    y: float
    capacidad: float = 0.0
    cluster: int = 0
    estado: EstadoNodo = EstadoNodo.ACTIVO
    carga: float = 0.0
    temperatura: float = 35.0
    longitud_cola: int = 0
    procesados: int = 0
    descartados: int = 0

    @property
    def utilizacion(self) -> float:
        if self.capacidad <= 0:
            return 0.0
        return min(1.0, self.carga / self.capacidad)

    def puede_aceptar(self, tamano: float) -> bool:
        return self.estado == EstadoNodo.ACTIVO and (self.carga + tamano) <= self.capacidad


@dataclass
class Enlace:
    origen: str
    destino: str
    latencia_base: float
    congestion: float = 0.0

    @property
    def latencia(self) -> float:
        return self.latencia_base * (1.0 + 0.75 * self.congestion)


@dataclass
class InstantaneaMetricas:
    tiempo_sim: float
    paquetes_creados: int = 0
    paquetes_completados: int = 0
    paquetes_descartados: int = 0
    paquetes_en_vuelo: int = 0
    latencia_promedio: float = 0.0
    ruta_activa: list[str] = field(default_factory=list)
    ruta_anterior: list[str] = field(default_factory=list)
    ruta_cambio: bool = False
    potencia_refrigeracion: float = 0.0
    historial_refrigeracion: list[tuple[float, float]] = field(default_factory=list)
    asignacion_energia: list[float] = field(default_factory=list)
    lambda_lagrange: float = 0.0
    historial_energia: list[tuple[float, list[float]]] = field(default_factory=list)
    cargas_nodo: dict[str, float] = field(default_factory=dict)
    nodos_fallidos: list[str] = field(default_factory=list)
    tiempo_reloj: float = field(default_factory=time.time)

    def a_diccionario(self) -> dict[str, Any]:
        return {
            "tiempo_sim": self.tiempo_sim,
            "paquetes_creados": self.paquetes_creados,
            "paquetes_completados": self.paquetes_completados,
            "paquetes_descartados": self.paquetes_descartados,
            "paquetes_en_vuelo": self.paquetes_en_vuelo,
            "latencia_promedio": self.latencia_promedio,
            "ruta_activa": list(self.ruta_activa),
            "ruta_anterior": list(self.ruta_anterior),
            "ruta_cambio": self.ruta_cambio,
            "potencia_refrigeracion": self.potencia_refrigeracion,
            "asignacion_energia": list(self.asignacion_energia),
            "lambda_lagrange": self.lambda_lagrange,
            "cargas_nodo": dict(self.cargas_nodo),
            "nodos_fallidos": list(self.nodos_fallidos),
        }


@dataclass
class EstadoSimulacion:
    nodos: dict[str, NodoRed]
    enlaces: list[Enlace]
    paquetes: dict[str, Paquete] = field(default_factory=dict)
    paquetes_activos: list[str] = field(default_factory=list)
    metricas: InstantaneaMetricas = field(
        default_factory=lambda: InstantaneaMetricas(tiempo_sim=0.0)
    )
    muestras_latencia: list[float] = field(default_factory=list)
    en_ejecucion: bool = True
    finalizada: bool = False
    mensaje: str = ""

    def mapa_enlaces(self) -> dict[tuple[str, str], Enlace]:
        return {(e.origen, e.destino): e for e in self.enlaces}

    def servidores(self) -> list[NodoRed]:
        return [n for n in self.nodos.values() if n.tipo == TipoNodo.SERVIDOR]

    def id_puerta(self) -> str:
        for nodo in self.nodos.values():
            if nodo.tipo == TipoNodo.PUERTA:
                return nodo.id_nodo
        raise RuntimeError("No hay nodo puerta de enlace configurado")
