from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np


from enrutamiento import DynamicRouter, KnapsackServerOptimizer


class EnrutadorProgramacionDinamica:
    """Enrutador de paquetes basado en Programación Dinámica (Módulo 1).

    Aplica el principio de optimalidad de Richard Bellman mediante el algoritmo
    de Floyd-Warshall con reconstrucción de rutas y recalculo dinámico ante enlaces
    congestionados y caídas de nodos.
    """

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
        """Calcula la ruta óptima de menor latencia hacia el mejor servidor disponible."""
        return self._enrutador.ruta_mas_corta(
            origen=origen,
            destinos=destinos,
            enlaces_ponderados=enlaces_ponderados,
            no_disponibles=no_disponibles,
            metodo="floyd_warshall",
        )


class AsignadorMochila:
    """Optimizador de admisión de cargas mediante el Problema de la Mochila (Módulo 1).

    Aplica Programación Dinámica Tabular para seleccionar el subconjunto óptimo
    de tareas que maximiza el beneficio total dentro de la capacidad de cómputo.
    """

    @staticmethod
    def seleccionar(
        items: Sequence[tuple[str, float, float]],
        capacidad: float,
    ) -> list[str]:
        """Selecciona el subconjunto óptimo de IDs de paquete que maximiza el valor."""
        return KnapsackServerOptimizer.seleccionar(items, capacidad)


class ModeloTemperatura:
    def __init__(self, a: float = 18.0, b: float = 12.0, c: float = 28.0, d: float = 32.0):
        self.a, self.b, self.c, self.d = a, b, c, d

    def temperatura(self, ratio_carga: float) -> float:
        carga = float(np.clip(ratio_carga, 0.0, 1.5))
        return self.a * carga**3 - self.b * carga**2 + self.c * carga + self.d

    def derivada(self, ratio_carga: float) -> float:
        carga = float(ratio_carga)
        return 3 * self.a * carga**2 - 2 * self.b * carga + self.c

    def puntos_estacionarios(self) -> list[float]:
        a, b, c = 3 * self.a, -2 * self.b, self.c
        disc = b**2 - 4 * a * c
        if disc < 0:
            return []
        r1 = (-b - np.sqrt(disc)) / (2 * a)
        r2 = (-b + np.sqrt(disc)) / (2 * a)
        return [float(r) for r in (r1, r2) if 0 <= r <= 1.5]


class ControladorGradienteRefrigeracion:
    def __init__(
        self,
        tasa_aprendizaje: float = 0.05,
        temp_objetivo: float = 42.0,
        alfa: float = 1.0,
        beta: float = 0.35,
    ):
        self.tasa_aprendizaje = tasa_aprendizaje
        self.temp_objetivo = temp_objetivo
        self.alfa = alfa
        self.beta = beta
        self.potencia = 0.40

    def _temp_efectiva(self, temp_ambiente: float, potencia: float) -> float:
        return temp_ambiente - 30.0 * (1.0 - np.exp(-2.2 * potencia))

    def paso(self, temp_ambiente: float) -> float:
        p = self.potencia
        eps = 1e-4

        def costo(potencia: float) -> float:
            t = self._temp_efectiva(temp_ambiente, potencia)
            return self.alfa * (t - self.temp_objetivo) ** 2 + self.beta * (potencia**2)

        grad = (costo(p + eps) - costo(p - eps)) / (2 * eps)
        self.potencia = float(np.clip(p - self.tasa_aprendizaje * np.tanh(grad / 50.0), 0.05, 1.0))
        return self.potencia


class AsignadorEnergiaLagrange:
    def __init__(self, presupuesto: float, n_clusters: int = 3):
        self.presupuesto = float(presupuesto)
        self.n_clusters = n_clusters
        self.valor_lambda = 1.0
        self.asignacion = np.full(n_clusters, presupuesto / n_clusters)

    def asignar(self, demandas: Sequence[float]) -> tuple[np.ndarray, float]:
        gamma = np.asarray(demandas, dtype=float)
        if gamma.size != self.n_clusters:
            gamma = np.resize(gamma, self.n_clusters)
        gamma = np.clip(gamma, 1e-3, None)

        lo, hi = 1e-6, float(gamma.max() * 10)
        lam = 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            alloc = np.maximum(gamma / mid - 1.0, 0.0)
            total = alloc.sum()
            if total > self.presupuesto:
                lo = mid
            else:
                hi = mid
            lam = mid

        alloc = np.maximum(gamma / lam - 1.0, 0.0)
        if alloc.sum() > 0:
            alloc *= self.presupuesto / alloc.sum()
        else:
            alloc = np.full(self.n_clusters, self.presupuesto / self.n_clusters)

        self.asignacion = alloc
        self.valor_lambda = float(lam)
        return alloc, self.valor_lambda
