from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np

from enrutamiento import DynamicRouter, KnapsackServerOptimizer
from optimizacion.optimizacion import Optimizacion


class EnrutadorProgramacionDinamica:
    """Adaptador Módulo 1 → Módulo 3 (ruta más corta por PD)."""

    def __init__(self, ids_nodo: Sequence[str]):
        self.ids_nodo = list(ids_nodo)
        self._enrutador = DynamicRouter(self.ids_nodo)

    def ruta_mas_corta(
        self,
        origen: str,
        destinos: Sequence[str],
        enlaces_ponderados: Iterable[tuple[str, str, float]],
        no_disponibles: set[str] | None = None,
    ) -> tuple[list[str], float]:
        return self._enrutador.ruta_mas_corta(
            origen=origen,
            destinos=destinos,
            enlaces_ponderados=enlaces_ponderados,
            no_disponibles=no_disponibles,
            metodo="floyd_warshall",
        )


class AsignadorMochila:
    """Adaptador Módulo 1 → Módulo 3 (mochila 0/1)."""

    @staticmethod
    def seleccionar(
        items: Sequence[tuple[str, float, float]],
        capacidad: float,
    ) -> list[str]:
        return KnapsackServerOptimizer.seleccionar(items, capacidad)


class ModeloTemperatura:
    """Adaptador Módulo 2 → Módulo 3 (T(carga) no lineal)."""

    def __init__(
        self,
        a: float = 120.0,
        b: float = 90.0,
        c: float = 18.0,
        d: float = 35.0,
        umbral_emergencia: float = 70.0,
    ):
        self.a, self.b, self.c, self.d = a, b, c, d
        self._opt = Optimizacion(umbral_emergencia=umbral_emergencia)

    def temperatura(self, ratio_carga: float) -> float:
        carga = float(np.clip(ratio_carga, 0.0, 1.5))
        return self.a * carga**3 - self.b * carga**2 + self.c * carga + self.d

    def derivada(self, ratio_carga: float) -> float:
        carga = float(ratio_carga)
        return 3 * self.a * carga**2 - 2 * self.b * carga + self.c

    def puntos_estacionarios(self) -> list[float]:
        analisis = self._opt.analisis_consumo_temperatura(
            a=self.a, b=self.b, c=self.c, d=self.d
        )
        return [float(p["carga"]) for p in analisis["puntos_estacionarios"]]

    def analisis_completo(self) -> dict:
        return self._opt.analisis_consumo_temperatura(
            a=self.a, b=self.b, c=self.c, d=self.d
        )


class ControladorGradienteRefrigeracion:
    """Adaptador Módulo 2 → Módulo 3 (gradiente de refrigeración)."""

    def __init__(
        self,
        tasa_aprendizaje: float = 0.20,
        temp_objetivo: float = 40.0,
        alfa: float = 1.0,
        beta: float = 0.35,
    ):
        self.tasa_aprendizaje = tasa_aprendizaje
        self.temp_objetivo = temp_objetivo
        self.alfa = alfa
        self.beta = beta
        self.potencia = 0.40
        self._opt = Optimizacion()

    def paso(self, temp_ambiente: float) -> float:
        calor_carga = max(5.0, float(temp_ambiente) - 25.0)
        resultado = self._opt.ajuste_refrigeracion_gradiente(
            temp_ambiente=25.0,
            calor_carga=calor_carga,
            capacidad_enfriamiento=40.0,
            temp_objetivo=self.temp_objetivo,
            potencia_inicial=self.potencia,
            tasa_aprendizaje=self.tasa_aprendizaje,
            max_iteraciones=40,
        )
        self.potencia = float(resultado["potencia_optima"])
        return self.potencia


class AsignadorEnergiaLagrange:
    """Adaptador Módulo 2 → Módulo 3 (Lagrange / presupuesto eléctrico)."""

    def __init__(self, presupuesto: float, n_clusters: int = 3):
        self.presupuesto = float(presupuesto)
        self.n_clusters = n_clusters
        self.valor_lambda = 1.0
        self.asignacion = np.full(n_clusters, presupuesto / max(n_clusters, 1))
        self._opt = Optimizacion()

    def asignar(self, demandas: Sequence[float]) -> tuple[np.ndarray, float]:
        gamma = np.asarray(demandas, dtype=float)
        if gamma.size != self.n_clusters:
            gamma = np.resize(gamma, self.n_clusters)
        gamma = np.clip(gamma, 1e-3, None)

        pesos = 0.5 + gamma / max(float(gamma.max()), 1e-6)
        resultado = self._opt.asignacion_presupuesto_lagrange(
            presupuesto=self.presupuesto,
            demandas=gamma.tolist(),
            pesos=pesos.tolist(),
        )
        alloc = np.asarray(resultado["asignacion"], dtype=float)
        if alloc.size != self.n_clusters:
            alloc = np.resize(alloc, self.n_clusters)
        self.asignacion = alloc
        self.valor_lambda = float(resultado["multiplicador_lagrange"])
        return self.asignacion, self.valor_lambda
