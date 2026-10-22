from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np


class EnrutadorProgramacionDinamica:
    def __init__(self, ids_nodo: Sequence[str]):
        self.ids_nodo = list(ids_nodo)

    def ruta_mas_corta(
        self,
        origen: str,
        destinos: Sequence[str],
        enlaces_ponderados: Iterable[tuple[str, str, float]],
        no_disponibles: set[str] | None = None,
    ) -> tuple[list[str], float]:
        caidos = no_disponibles or set()
        if origen in caidos:
            return [], float("inf")

        nodos = [n for n in self.ids_nodo if n not in caidos]
        indice = {n: i for i, n in enumerate(nodos)}
        if origen not in indice:
            return [], float("inf")

        n = len(nodos)
        dist = np.full(n, np.inf)
        prev = np.full(n, -1, dtype=int)
        dist[indice[origen]] = 0.0

        aristas = [
            (u, v, w)
            for u, v, w in enlaces_ponderados
            if u in indice and v in indice and w >= 0
        ]

        for _ in range(n - 1):
            actualizado = False
            for u, v, w in aristas:
                iu, iv = indice[u], indice[v]
                candidato = dist[iu] + w
                if candidato < dist[iv]:
                    dist[iv] = candidato
                    prev[iv] = iu
                    actualizado = True
            if not actualizado:
                break

        mejor_destino = None
        mejor_costo = float("inf")
        for t in destinos:
            if t in indice and dist[indice[t]] < mejor_costo:
                mejor_costo = float(dist[indice[t]])
                mejor_destino = t

        if mejor_destino is None or not np.isfinite(mejor_costo):
            return [], float("inf")

        idxs: list[int] = []
        actual = indice[mejor_destino]
        while actual != -1:
            idxs.append(actual)
            actual = int(prev[actual])
        idxs.reverse()
        ruta = [nodos[i] for i in idxs]
        if not ruta or ruta[0] != origen:
            return [], float("inf")
        return ruta, mejor_costo


class AsignadorMochila:
    @staticmethod
    def seleccionar(
        items: Sequence[tuple[str, float, float]],
        capacidad: float,
    ) -> list[str]:
        if capacidad <= 0 or not items:
            return []

        escala = 10
        cap = int(capacidad * escala)
        n = len(items)
        pesos = [max(1, int(w * escala)) for _, w, _ in items]
        valores = [float(v) for _, _, v in items]

        dp = np.zeros((n + 1, cap + 1), dtype=float)
        for i in range(1, n + 1):
            wi, vi = pesos[i - 1], valores[i - 1]
            for c in range(cap + 1):
                dp[i, c] = dp[i - 1, c]
                if wi <= c:
                    dp[i, c] = max(dp[i, c], dp[i - 1, c - wi] + vi)

        seleccionados: list[str] = []
        c = cap
        for i in range(n, 0, -1):
            if dp[i, c] != dp[i - 1, c]:
                seleccionados.append(items[i - 1][0])
                c -= pesos[i - 1]
        seleccionados.reverse()
        return seleccionados


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
