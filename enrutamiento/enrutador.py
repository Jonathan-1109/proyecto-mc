from __future__ import annotations

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from typing import Iterable, Sequence
import time
import numpy as np

from enrutamiento.modelos import ResultadoRuta


class RouterNetwork:
    """Modelo de red de comunicaciones para centros de datos (topología, latencias y congestión).

    Mantiene la topología de routers, switches y enlaces, gestionando las latencias base
    y los factores dinámicos de congestión en tiempo real.
    """

    def __init__(
        self,
        factor_penalizacion_congestion: float = 0.75,
        exponente_congestion: float = 1.0,
    ) -> None:
        """Inicializa la red de routers.

        Args:
            factor_penalizacion_congestion: Coeficiente alpha que escala el efecto de la congestión.
            exponente_congestion: Exponente beta para efectos de congestión no lineal.
        """
        if factor_penalizacion_congestion < 0:
            raise ValueError("El factor de penalización por congestión no puede ser negativo")
        if exponente_congestion <= 0:
            raise ValueError("El exponente de congestión debe ser estrictamente positivo")

        self.alpha: float = float(factor_penalizacion_congestion)
        self.beta: float = float(exponente_congestion)
        self._nodos: set[str] = set()
        self._tipos_nodo: dict[str, str] = {}
        # (origen, destino) -> {"latencia_base": float, "congestion": float}
        self._enlaces: dict[tuple[str, str], dict[str, float]] = {}

    @property
    def nodos(self) -> list[str]:
        return sorted(self._nodos)

    @property
    def enlaces(self) -> dict[tuple[str, str], dict[str, float]]:
        return dict(self._enlaces)

    def agregar_nodo(self, id_nodo: str, tipo: str = "router") -> None:
        """Registra un nuevo nodo en la red.

        Args:
            id_nodo: Identificador alfanumérico único.
            tipo: Rol del nodo ('puerta', 'router', 'servidor').
        """
        if not id_nodo or not isinstance(id_nodo, str):
            raise ValueError("El id_nodo debe ser una cadena no vacía")
        self._nodos.add(id_nodo)
        self._tipos_nodo[id_nodo] = tipo

    def agregar_enlace(
        self,
        origen: str,
        destino: str,
        latencia_base: float,
        bidireccional: bool = True,
    ) -> None:
        """Agrega o actualiza un enlace físico o lógico entre dos nodos.

        Args:
            origen: Identificador del nodo origen.
            destino: Identificador del nodo destino.
            latencia_base: Latencia mínima en reposo (milisegundos). Debe ser >= 0.
            bidireccional: Si es True, crea también el enlace inverso con los mismos parámetros.
        """
        if latencia_base < 0:
            raise ValueError(f"La latencia base no puede ser negativa (recibido: {latencia_base})")
        if origen == destino:
            raise ValueError(f"No se permiten autoenlaces ({origen} -> {destino})")

        self.agregar_nodo(origen)
        self.agregar_nodo(destino)

        self._enlaces[(origen, destino)] = {
            "latencia_base": float(latencia_base),
            "congestion": 0.0,
        }
        if bidireccional:
            self._enlaces[(destino, origen)] = {
                "latencia_base": float(latencia_base),
                "congestion": 0.0,
            }

    def actualizar_congestion(self, origen: str, destino: str, congestion: float) -> None:
        """Modifica el nivel de congestión de un enlace específico.

        Args:
            origen: Identificador del nodo origen.
            destino: Identificador del nodo destino.
            congestion: Nivel de congestión en el rango normalizado [0.0, 1.0].
        """
        clave = (origen, destino)
        if clave not in self._enlaces:
            raise KeyError(f"El enlace {origen} -> {destino} no existe en la topología")
        self._enlaces[clave]["congestion"] = float(np.clip(congestion, 0.0, 1.0))

    def peso_enlace(self, origen: str, destino: str) -> float:
        """Calcula la latencia efectiva actual aplicando la penalización por congestión:

        w(u, v) = L_base * (1 + alpha * (congestion)^beta)
        """
        clave = (origen, destino)
        if clave not in self._enlaces:
            return float("inf")
        datos = self._enlaces[clave]
        lat_base = datos["latencia_base"]
        cong = datos["congestion"]
        return float(lat_base * (1.0 + self.alpha * (cong**self.beta)))

    def obtener_enlaces_ponderados(self) -> list[tuple[str, str, float]]:
        """Retorna la lista de todas las aristas con su peso dinámico actual."""
        return [
            (u, v, self.peso_enlace(u, v))
            for (u, v) in self._enlaces.keys()
        ]


# Alias en español
RedEnrutamiento = RouterNetwork


class DynamicRouter:
    """Enrutador de paquetes basado en Programación Dinámica (PD).

    Implementa el principio de optimalidad de Bellman a través de dos formulaciones:
    1. Algoritmo de Floyd-Warshall (Tabulación completa O(V^3) con reconstrucción de rutas).
    2. Formulación de Bellman por Etapas de Transición (Bellman-Ford O(V*E) con auditoría de etapas).

    Permite recalcular dinámicamente el camino óptimo ante enlaces congestionados
    o nodos caídos, emitiendo métricas para las alertas visuales de Pygame.
    """

    def __init__(
        self,
        red_o_nodos: RouterNetwork | Sequence[str] | None = None,
        factor_penalizacion_congestion: float = 0.75,
        exponente_congestion: float = 1.0,
    ) -> None:
        if isinstance(red_o_nodos, RouterNetwork):
            self.red = red_o_nodos
        else:
            self.red = RouterNetwork(
                factor_penalizacion_congestion=factor_penalizacion_congestion,
                exponente_congestion=exponente_congestion,
            )
            if red_o_nodos is not None:
                for nid in red_o_nodos:
                    self.red.agregar_nodo(nid)

        self._ultima_matriz_dist: np.ndarray | None = None
        self._ultima_matriz_next: np.ndarray | None = None
        self._ultimo_mapa_indices: dict[str, int] = {}
        self._historial_cambios_ruta: list[dict] = []

    # -------------------------------------------------------------------------
    # 1. Programación Dinámica: Floyd-Warshall con reconstrucción de camino
    # -------------------------------------------------------------------------
    def floyd_warshall(
        self,
        no_disponibles: set[str] | None = None,
        enlaces_externos: Iterable[tuple[str, str, float]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, int], list[str]]:
        """Aplica el algoritmo de Floyd-Warshall mediante Programación Dinámica Tabular.

        Ecuación de Recurrencia de Bellman:
            D^(k)[i, j] = min( D^(k-1)[i, j],  D^(k-1)[i, k] + D^(k-1)[k, j] )

        Reconstrucción de ruta:
            Next[i, j] almacena el siguiente salto en el camino óptimo de i a j.
            Si pasar por k es estrictamente mejor, Next[i, j] <- Next[i, k].

        Args:
            no_disponibles: Conjunto de identificadores de nodos caídos o inaccesibles.
            enlaces_externos: Opcional, lista de (u, v, latencia) para sobreescribir la red.

        Returns:
            dist: Matriz numpy (n x n) de distancias mínimas.
            siguiente: Matriz numpy (n x n) de índices del siguiente salto (-1 si no hay camino).
            indice: Diccionario id_nodo -> índice de fila/columna.
            nodos_activos: Lista de IDs de nodos considerados.
        """
        caidos = no_disponibles or set()
        nodos_activos = [n for n in self.red.nodos if n not in caidos]
        n = len(nodos_activos)
        indice = {nid: i for i, nid in enumerate(nodos_activos)}

        # Inicialización de la tabla de Programación Dinámica
        # Caso base k = 0: distancias directas
        dist = np.full((n, n), np.inf, dtype=float)
        siguiente = np.full((n, n), -1, dtype=int)

        for i in range(n):
            dist[i, i] = 0.0
            siguiente[i, i] = i

        # Poblar aristas iniciales
        if enlaces_externos is not None:
            aristas = [
                (u, v, w)
                for u, v, w in enlaces_externos
                if u in indice and v in indice and w >= 0
            ]
        else:
            aristas = [
                (u, v, self.red.peso_enlace(u, v))
                for (u, v) in self.red.enlaces.keys()
                if u in indice and v in indice
            ]

        for u, v, w in aristas:
            iu, iv = indice[u], indice[v]
            if w < dist[iu, iv]:
                dist[iu, iv] = float(w)
                siguiente[iu, iv] = iv

        # Subproblemas superpuestos de PD: evaluar cada vértice intermedio k
        for k in range(n):
            # Vectorización con NumPy para alto rendimiento sin alterar la semántica de PD
            # D^(k)[i, j] = min(D^(k-1)[i, j], D^(k-1)[i, k] + D^(k-1)[k, j])
            d_ik = dist[:, k, np.newaxis]  # columna k
            d_kj = dist[np.newaxis, k, :]  # fila k
            suma_candidata = d_ik + d_kj

            mascara_mejora = suma_candidata < dist
            # Evitar ciclos negativos o caminos inválidos por infinitos
            mascara_valida = mascara_mejora & np.isfinite(suma_candidata)

            dist[mascara_valida] = suma_candidata[mascara_valida]

            # Actualización de matriz de reconstrucción (Next)
            filas_mejoradas, columnas_mejoradas = np.where(mascara_valida)
            for i, j in zip(filas_mejoradas, columnas_mejoradas):
                siguiente[i, j] = siguiente[i, k]

        self._ultima_matriz_dist = dist
        self._ultima_matriz_next = siguiente
        self._ultimo_mapa_indices = indice
        return dist, siguiente, indice, nodos_activos

    def reconstruir_camino(
        self,
        origen: str,
        destino: str,
        siguiente: np.ndarray,
        indice: dict[str, int],
        nodos_activos: list[str],
    ) -> list[str]:
        """Reconstruye la trayectoria óptima nodo por nodo utilizando la matriz Next de PD."""
        if origen not in indice or destino not in indice:
            return []
        u = indice[origen]
        v = indice[destino]
        if siguiente[u, v] == -1:
            return []

        camino = [origen]
        visitados = {u}
        actual = u
        while actual != v:
            actual = int(siguiente[actual, v])
            if actual in visitados:
                # Detección de ciclo
                return []
            visitados.add(actual)
            camino.append(nodos_activos[actual])

        return camino

    # -------------------------------------------------------------------------
    # 2. Programación Dinámica por Etapas de Transición (Bellman-Ford)
    # -------------------------------------------------------------------------
    def bellman_etapas(
        self,
        origen: str,
        destino: str | None = None,
        no_disponibles: set[str] | None = None,
        enlaces_externos: Iterable[tuple[str, str, float]] | None = None,
    ) -> tuple[dict[str, float], dict[str, str | None], list[dict[str, Any]]]:
        """Resuelve el camino óptimo mediante PD por etapas (restricción en número de saltos).

        En cada etapa k (1 <= k <= |V|-1):
            f_k(v) = min { f_{k-1}(v),  min_{(u, v) in E} [ f_{k-1}(u) + w(u, v) ] }

        Permite auditar paso a paso cómo converge la solución óptima.
        """
        caidos = no_disponibles or set()
        nodos_activos = [n for n in self.red.nodos if n not in caidos]
        if origen not in nodos_activos:
            return {}, {}, []

        if enlaces_externos is not None:
            aristas = [
                (u, v, float(w))
                for u, v, w in enlaces_externos
                if u not in caidos and v not in caidos and w >= 0
            ]
        else:
            aristas = [
                (u, v, self.red.peso_enlace(u, v))
                for (u, v) in self.red.enlaces.keys()
                if u not in caidos and v not in caidos
            ]

        # Caso base etapa 0: costo 0 en origen, infinito en el resto
        costo: dict[str, float] = {n: float("inf") for n in nodos_activos}
        costo[origen] = 0.0
        predecesor: dict[str, str | None] = {n: None for n in nodos_activos}

        historial_etapas: list[dict[str, Any]] = []

        n = len(nodos_activos)
        for etapa in range(1, n):
            cambio = False
            costo_anterior = dict(costo)
            for u, v, w in aristas:
                if costo_anterior[u] != float("inf"):
                    candidato = costo_anterior[u] + w
                    if candidato < costo[v] - 1e-9:
                        costo[v] = candidato
                        predecesor[v] = u
                        cambio = True

            historial_etapas.append({
                "etapa": etapa,
                "costos": dict(costo),
                "hubo_cambio": cambio,
            })
            if not cambio:
                break

        return costo, predecesor, historial_etapas

    # -------------------------------------------------------------------------
    # 3. Interfaz Unificada de Enrutamiento (Compatible con SimPy y Pygame)
    # -------------------------------------------------------------------------
    def ruta_mas_corta(
        self,
        origen: str,
        destinos: Sequence[str] | str,
        enlaces_ponderados: Iterable[tuple[str, str, float]] | None = None,
        no_disponibles: set[str] | None = None,
        metodo: str = "floyd_warshall",
    ) -> tuple[list[str], float]:
        """Determina la ruta de menor latencia desde el origen hacia el mejor destino disponible.

        Args:
            origen: Identificador del nodo emisor (ej. 'GW').
            destinos: Lista o tupla de destinos posibles (ej. servidores activos ['S1', 'S2', 'S3']).
            enlaces_ponderados: Opcional, lista de enlaces dinámicos del simulador.
            no_disponibles: Conjunto de nodos con fallas.
            metodo: 'floyd_warshall' o 'bellman_etapas'.

        Returns:
            (ruta, latencia_total)
        """
        lista_destinos = [destinos] if isinstance(destinos, str) else list(destinos)
        caidos = set(no_disponibles or [])

        if origen in caidos or not lista_destinos:
            return [], float("inf")

        if metodo == "bellman_etapas":
            costos, predecesores, _ = self.bellman_etapas(
                origen=origen,
                no_disponibles=caidos,
                enlaces_externos=enlaces_ponderados,
            )
            mejor_destino = None
            mejor_costo = float("inf")
            for d in lista_destinos:
                if d in costos and costos[d] < mejor_costo:
                    mejor_costo = costos[d]
                    mejor_destino = d

            if mejor_destino is None or not np.isfinite(mejor_costo):
                return [], float("inf")

            ruta: list[str] = []
            actual: str | None = mejor_destino
            visitados = set()
            while actual is not None:
                if actual in visitados:
                    return [], float("inf")
                visitados.add(actual)
                ruta.append(actual)
                actual = predecesores.get(actual)
            ruta.reverse()
            if not ruta or ruta[0] != origen:
                return [], float("inf")
            return ruta, mejor_costo

        # Por defecto Floyd-Warshall
        dist, sig, indice, nodos_activos = self.floyd_warshall(
            no_disponibles=caidos,
            enlaces_externos=enlaces_ponderados,
        )

        if origen not in indice:
            return [], float("inf")

        idx_origen = indice[origen]
        mejor_destino = None
        mejor_costo = float("inf")

        for d in lista_destinos:
            if d in indice:
                c = float(dist[idx_origen, indice[d]])
                if c < mejor_costo:
                    mejor_costo = c
                    mejor_destino = d

        if mejor_destino is None or not np.isfinite(mejor_costo):
            return [], float("inf")

        ruta = self.reconstruir_camino(origen, mejor_destino, sig, indice, nodos_activos)
        return ruta, mejor_costo

    def calcular_resultado_ruta(
        self,
        origen: str,
        destinos: Sequence[str] | str,
        no_disponibles: set[str] | None = None,
    ) -> ResultadoRuta:
        """Retorna un objeto estructurado ResultadoRuta con métricas completas."""
        t0 = time.perf_counter()
        ruta, costo = self.ruta_mas_corta(origen, destinos, no_disponibles=no_disponibles)
        destino_final = ruta[-1] if ruta else (destinos[0] if isinstance(destinos, list) and destinos else "")
        congestiones = {
            clave: datos["congestion"]
            for clave, datos in self.red.enlaces.items()
        }
        return ResultadoRuta(
            origen=origen,
            destino=destino_final,
            ruta=ruta,
            latencia_total=costo,
            num_saltos=max(0, len(ruta) - 1),
            es_factible=bool(ruta and np.isfinite(costo)),
            congestiones_enlaces=congestiones,
            metodo="Floyd-Warshall",
        )

    def simular_cambio_congestion(
        self,
        enlace: tuple[str, str],
        nueva_congestion: float,
        origen: str,
        destinos: Sequence[str],
    ) -> dict[str, Any]:
        """Evalúa el impacto de la congestión y detecta si se requiere recalcular la ruta óptima.

        Permite emitir las alertas requeridas por el Módulo 3 y la interfaz visual de Pygame.
        """
        u, v = enlace
        # Ruta anterior
        ruta_previa, costo_previo = self.ruta_mas_corta(origen, destinos)

        # Aplicar congestión
        self.red.actualizar_congestion(u, v, nueva_congestion)

        # Recalcular ruta con PD
        nueva_ruta, nuevo_costo = self.ruta_mas_corta(origen, destinos)

        cambio_detectado = bool(ruta_previa != nueva_ruta)
        registro = {
            "enlace_afectado": enlace,
            "nueva_congestion": round(nueva_congestion, 3),
            "ruta_anterior": ruta_previa,
            "costo_anterior": round(costo_previo, 4),
            "nueva_ruta": nueva_ruta,
            "nuevo_costo": round(nuevo_costo, 4),
            "ruta_cambio": cambio_detectado,
            "incremento_latencia": round(nuevo_costo - costo_previo, 4),
            "alerta_visual": "CAMBIO_DE_RUTA_POR_CONGESTION" if cambio_detectado else "CONGESTION_ABSORBIDA",
        }
        self._historial_cambios_ruta.append(registro)
        return registro


# Alias en español
EnrutadorDinamico = DynamicRouter
