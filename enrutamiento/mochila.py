from __future__ import annotations

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from typing import Any, Sequence
import time
import numpy as np

from enrutamiento.modelos import ItemCarga, KnapsackItem, ResultadoMochila


class KnapsackServerOptimizer:
    """Optimizador de asignación y procesamiento de cargas en servidores mediante Programación Dinámica.

    Modela el problema de admisión y despacho de paquetes o tareas en centros de datos
    como un problema de la mochila (Knapsack Problem 0/1 y Bounded/Acotada).

    Analogía cuantitativa:
        - Capacidad de la mochila (W): Capacidad disponible del servidor (CPU / RAM / Ancho de banda).
        - Objetos (Paquetes / Tareas): Cada paquete requiere un volumen de cómputo (peso w_i)
          y genera una recompensa o nivel de servicio (valor v_i, derivado de su prioridad/SLA).
    """

    def __init__(self, escala_discretizacion: int = 10) -> None:
        """Inicializa el optimizador de mochila.

        Args:
            escala_discretizacion: Factor multiplicador para convertir pesos y capacidades
                flotantes continuos en enteros discretos para la tabla de PD (ej. 10 para décimas, 100 para centésimas).
        """
        if escala_discretizacion <= 0:
            raise ValueError("La escala de discretización debe ser un entero positivo")
        self.escala = int(escala_discretizacion)

    def _normalizar_items(
        self,
        items: Sequence[ItemCarga | tuple[str, float, float] | dict[str, Any]],
    ) -> list[ItemCarga]:
        """Normaliza una colección heterogénea de ítems en objetos ItemCarga válidos."""
        resultado: list[ItemCarga] = []
        for elem in items:
            if isinstance(elem, ItemCarga):
                resultado.append(elem)
            elif isinstance(elem, tuple):
                if len(elem) == 3:
                    id_i, p_i, v_i = elem
                    resultado.append(ItemCarga(id_item=str(id_i), peso=float(p_i), valor=float(v_i)))
                elif len(elem) == 4:
                    id_i, p_i, v_i, lim = elem
                    resultado.append(
                        ItemCarga(id_item=str(id_i), peso=float(p_i), valor=float(v_i), limite=int(lim))
                    )
                else:
                    raise ValueError(f"Tupla de ítem inválida: {elem}")
            elif isinstance(elem, dict):
                id_i = str(elem.get("id", elem.get("id_item", elem.get("nombre", "item"))))
                p_i = float(elem.get("peso", elem.get("tamano", 1.0)))
                v_i = float(elem.get("valor", elem.get("prioridad", 1.0)))
                lim = int(elem.get("limite", elem.get("cantidad", 1)))
                resultado.append(ItemCarga(id_item=id_i, peso=p_i, valor=v_i, limite=lim))
            else:
                raise TypeError(f"Tipo de ítem no soportado: {type(elem)}")
        return resultado

    # -------------------------------------------------------------------------
    # 1. Problema de la Mochila 0/1 (Tabulación por Programación Dinámica)
    # -------------------------------------------------------------------------
    def resolver_01(
        self,
        capacidad: float,
        items: Sequence[ItemCarga | tuple[str, float, float] | dict[str, Any]],
    ) -> ResultadoMochila:
        """Resuelve el problema de la mochila 0/1 mediante Programación Dinámica Tabular.

        Ecuación de Recurrencia de Bellman:
            DP[i, w] =
                0                                          si i = 0 o w = 0
                DP[i-1, w]                                 si peso[i] > w
                max( DP[i-1, w], DP[i-1, w - peso[i]] + valor[i] )   si peso[i] <= w

        Args:
            capacidad: Capacidad total de recursos del servidor. Debe ser >= 0.
            items: Colección de paquetes candidatos a procesar.

        Returns:
            ResultadoMochila con selección óptima, métricas de utilización y tabla DP.
        """
        t0 = time.perf_counter()

        if capacidad < 0:
            raise ValueError(f"La capacidad del servidor no puede ser negativa (recibido: {capacidad})")

        lista_items = self._normalizar_items(items)
        if capacidad == 0 or not lista_items:
            return ResultadoMochila(
                items_seleccionados=[],
                items_rechazados=lista_items,
                valor_total=0.0,
                peso_total=0.0,
                capacidad_servidor=capacidad,
                capacidad_remanente=capacidad,
                porcentaje_utilizacion=0.0,
                tabla_dp=np.zeros((1, 1), dtype=float),
                metodo="Knapsack 0/1 (PD Tabular)",
                tiempo_ejecucion_ms=(time.perf_counter() - t0) * 1000.0,
            )

        cap_entera = int(round(capacidad * self.escala))
        n = len(lista_items)
        pesos_ent = [max(1, int(round(item.peso * self.escala))) for item in lista_items]
        valores = [float(item.valor) for item in lista_items]

        # Matriz DP de dimensiones (N + 1) x (W + 1)
        dp = np.zeros((n + 1, cap_entera + 1), dtype=float)

        # Llenado tabular ascendente (Bottom-Up)
        for i in range(1, n + 1):
            w_i = pesos_ent[i - 1]
            v_i = valores[i - 1]
            for c in range(cap_entera + 1):
                if w_i > c:
                    dp[i, c] = dp[i - 1, c]
                else:
                    dp[i, c] = max(dp[i - 1, c], dp[i - 1, c - w_i] + v_i)

        # Reconstrucción de la solución óptima (Backtracking por la tabla de decisiones)
        seleccionados: list[ItemCarga] = []
        c_actual = cap_entera
        for i in range(n, 0, -1):
            if dp[i, c_actual] != dp[i - 1, c_actual]:
                seleccionados.append(lista_items[i - 1])
                c_actual -= pesos_ent[i - 1]

        seleccionados.reverse()
        ids_seleccionados = {id(it) for it in seleccionados}
        rechazados = [it for it in lista_items if id(it) not in ids_seleccionados]

        peso_total = sum(item.peso for item in seleccionados)
        valor_total = float(dp[n, cap_entera])
        remanente = max(0.0, capacidad - peso_total)
        pct_uso = (peso_total / capacidad * 100.0) if capacidad > 0 else 0.0

        t1 = time.perf_counter()
        return ResultadoMochila(
            items_seleccionados=seleccionados,
            items_rechazados=rechazados,
            valor_total=valor_total,
            peso_total=peso_total,
            capacidad_servidor=capacidad,
            capacidad_remanente=remanente,
            porcentaje_utilizacion=pct_uso,
            tabla_dp=dp,
            metodo="Knapsack 0/1 (PD Tabular)",
            tiempo_ejecucion_ms=(t1 - t0) * 1000.0,
        )

    # -------------------------------------------------------------------------
    # 2. Problema de la Mochila Acotada (Bounded Knapsack)
    # -------------------------------------------------------------------------
    def resolver_acotada(
        self,
        capacidad: float,
        items: Sequence[ItemCarga | tuple[str, float, float, int] | dict[str, Any]],
    ) -> ResultadoMochila:
        """Resuelve el problema de la mochila acotada donde cada tarea puede repetirse hasta m_i veces.

        Aplica la técnica de transformación mediante descomposición binaria para mantener
        complejidad polinomial O(W * sum(log(m_i))), reduciendo a una instancia equivalente 0/1.
        """
        t0 = time.perf_counter()
        if capacidad < 0:
            raise ValueError(f"La capacidad del servidor no puede ser negativa: {capacidad}")

        lista_items = self._normalizar_items(items)
        items_expandidos: list[ItemCarga] = []

        # Descomposición binaria de cada tipo de tarea
        for item in lista_items:
            m = item.limite
            k = 1
            while m > 0:
                tomar = min(k, m)
                id_bloque = f"{item.id_item}#x{tomar}"
                peso_bloque = item.peso * tomar
                valor_bloque = item.valor * tomar
                items_expandidos.append(
                    ItemCarga(
                        id_item=id_bloque,
                        peso=peso_bloque,
                        valor=valor_bloque,
                        limite=1,
                        metadatos={"origen_id": item.id_item, "cantidad": tomar},
                    )
                )
                m -= tomar
                k *= 2

        # Resolver la instancia 0/1 resultante
        res_01 = self.resolver_01(capacidad, items_expandidos)

        # Consolidar paquetes originales seleccionados
        conteo_por_id: dict[str, int] = {}
        for bloque in res_01.items_seleccionados:
            orig_id = bloque.metadatos.get("origen_id", bloque.id_item)
            cant = bloque.metadatos.get("cantidad", 1)
            conteo_por_id[orig_id] = conteo_por_id.get(orig_id, 0) + cant

        mapa_originales = {item.id_item: item for item in lista_items}
        consolidados_seleccionados: list[ItemCarga] = []
        consolidados_rechazados: list[ItemCarga] = []

        for item in lista_items:
            usados = conteo_por_id.get(item.id_item, 0)
            if usados > 0:
                consolidados_seleccionados.append(
                    ItemCarga(
                        id_item=item.id_item,
                        peso=item.peso * usados,
                        valor=item.valor * usados,
                        limite=usados,
                        metadatos={"instancias_admitidas": usados, "limite_original": item.limite},
                    )
                )
            if usados < item.limite:
                consolidados_rechazados.append(
                    ItemCarga(
                        id_item=item.id_item,
                        peso=item.peso * (item.limite - usados),
                        valor=item.valor * (item.limite - usados),
                        limite=item.limite - usados,
                        metadatos={"instancias_rechazadas": item.limite - usados},
                    )
                )

        t1 = time.perf_counter()
        return ResultadoMochila(
            items_seleccionados=consolidados_seleccionados,
            items_rechazados=consolidados_rechazados,
            valor_total=res_01.valor_total,
            peso_total=res_01.peso_total,
            capacidad_servidor=capacidad,
            capacidad_remanente=res_01.capacidad_remanente,
            porcentaje_utilizacion=res_01.porcentaje_utilizacion,
            tabla_dp=res_01.tabla_dp,
            metodo="Bounded Knapsack (PD Descomposición Binaria)",
            tiempo_ejecucion_ms=(t1 - t0) * 1000.0,
        )

    # -------------------------------------------------------------------------
    # 3. Asignación Multi-Servidor en Nube (Balanceo Cuantitativo)
    # -------------------------------------------------------------------------
    def asignar_cargas_multiples_servidores(
        self,
        servidores: dict[str, float],
        cola_paquetes: Sequence[ItemCarga | tuple[str, float, float] | dict[str, Any]],
    ) -> dict[str, Any]:
        """Distribuye óptimamente una cola de tareas entre varios servidores con capacidades limitadas.

        Aplica Programación Dinámica sucesivamente por servidor ordenando por prioridad/eficiencia.

        Args:
            servidores: Diccionario {id_servidor: capacidad_disponible}.
            cola_paquetes: Lista de tareas pendientes.

        Returns:
            Diccionario con la asignación por servidor y las tareas no admitidas.
        """
        paquetes_pendientes = self._normalizar_items(cola_paquetes)
        asignaciones: dict[str, ResultadoMochila] = {}

        # Ordenar servidores por capacidad disponible descendente
        servidores_ordenados = sorted(servidores.items(), key=lambda s: s[1], reverse=True)

        for s_id, cap in servidores_ordenados:
            if not paquetes_pendientes or cap <= 0:
                asignaciones[s_id] = self.resolver_01(cap, [])
                continue

            res = self.resolver_01(cap, paquetes_pendientes)
            asignaciones[s_id] = res

            # Remover tareas asignadas
            ids_admitidos = {id(it) for it in res.items_seleccionados}
            paquetes_pendientes = [it for it in paquetes_pendientes if id(it) not in ids_admitidos]

        total_procesado = sum(res.valor_total for res in asignaciones.values())
        peso_total_proc = sum(res.peso_total for res in asignaciones.values())
        cap_total_disp = sum(servidores.values())

        return {
            "asignaciones_servidor": asignaciones,
            "paquetes_no_admitidos": paquetes_pendientes,
            "valor_global_procesado": total_procesado,
            "peso_global_procesado": peso_total_proc,
            "capacidad_global_disponible": cap_total_disp,
            "utilizacion_global": (peso_total_proc / cap_total_disp * 100.0) if cap_total_disp > 0 else 0.0,
        }

    # -------------------------------------------------------------------------
    # 4. Compatibilidad estática con el Módulo 3 (SimPy)
    # -------------------------------------------------------------------------
    @staticmethod
    def seleccionar(
        items: Sequence[tuple[str, float, float]],
        capacidad: float,
    ) -> list[str]:
        """Método estático de compatibilidad directa con AsignadorMochila de puente_matematico.py."""
        opt = KnapsackServerOptimizer(escala_discretizacion=10)
        res = opt.resolver_01(capacidad, items)
        return [item.id_item for item in res.items_seleccionados]


# Alias en español
OptimizadorMochilaServidor = KnapsackServerOptimizer
