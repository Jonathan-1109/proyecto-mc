import sys
from pathlib import Path

# Permitir ejecución directa como script agregando la raíz del proyecto al sys.path
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from typing import Any, Sequence
import numpy as np

from enrutamiento.enrutador import DynamicRouter, RouterNetwork
from enrutamiento.mochila import ItemCarga, KnapsackServerOptimizer
from enrutamiento.modelos import ResultadoMochila, ResultadoRuta

# Configuración de salida UTF-8 para consolas Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class Modulo1:
    """Módulo 1: Enrutamiento de Datos y Asignación de Servidores (Programación Dinámica).

    Proyecto Métodos Cuantitativos · Universidad José Antonio Páez
    Simulador de Optimización para Redes de Centros de Datos (Cloud Computing)

    Integra:
    1. Determinación de la Ruta Más Corta (Floyd-Warshall / Bellman por etapas de PD)
       con recalculo dinámico ante enlaces congestionados y fallas de nodos.
    2. Modelo de Volumen-Carga (Problema de la Mochila 0/1 y Bounded por PD)
       para maximizar el valor de paquetes procesados bajo restricciones de capacidad.
    """

    def __init__(
        self,
        factor_congestion: float = 0.75,
        exponente_congestion: float = 1.0,
        escala_mochila: int = 10,
    ) -> None:
        self.red = RouterNetwork(
            factor_penalizacion_congestion=factor_congestion,
            exponente_congestion=exponente_congestion,
        )
        self.enrutador = DynamicRouter(self.red)
        self.optimizador_mochila = KnapsackServerOptimizer(escala_discretizacion=escala_mochila)

    def cargar_topologia_defecto(self) -> None:
        """Carga la topología estándar del centro de datos (Gateway, Routers R1..R3 y Servidores S1..S3)."""
        enlaces_base = [
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
        ]
        for u, v, lat in enlaces_base:
            self.red.agregar_enlace(u, v, lat, bidireccional=True)

    # -------------------------------------------------------------------------
    # Métodos de Enrutamiento (Componente 1)
    # -------------------------------------------------------------------------
    def calcular_ruta_optima(
        self,
        origen: str = "GW",
        destinos: Sequence[str] | None = None,
        no_disponibles: set[str] | None = None,
        metodo: str = "floyd_warshall",
    ) -> ResultadoRuta:
        """Calcula la ruta óptima de menor latencia hacia el clúster de servidores."""
        destinos_servidor = list(destinos) if destinos is not None else ["S1", "S2", "S3"]
        ruta, costo = self.enrutador.ruta_mas_corta(
            origen=origen,
            destinos=destinos_servidor,
            no_disponibles=no_disponibles,
            metodo=metodo,
        )
        destino_final = ruta[-1] if ruta else ""
        return ResultadoRuta(
            origen=origen,
            destino=destino_final,
            ruta=ruta,
            latencia_total=costo,
            num_saltos=max(0, len(ruta) - 1),
            es_factible=bool(ruta and np.isfinite(costo)),
            metodo="Floyd-Warshall (PD)" if metodo == "floyd_warshall" else "Bellman por Etapas (PD)",
        )

    def simular_congestion_enlace(
        self,
        enlace: tuple[str, str],
        nivel_congestion: float,
        origen: str = "GW",
        destinos: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Simula congestión en un enlace y recalcula dinámicamente la ruta con PD."""
        destinos_servidor = list(destinos) if destinos is not None else ["S1", "S2", "S3"]
        return self.enrutador.simular_cambio_congestion(
            enlace=enlace,
            nueva_congestion=nivel_congestion,
            origen=origen,
            destinos=destinos_servidor,
        )

    # -------------------------------------------------------------------------
    # Métodos de Asignación por Mochila (Componente 2)
    # -------------------------------------------------------------------------
    def optimizar_admision_servidor(
        self,
        capacidad_servidor: float,
        tareas: Sequence[ItemCarga | tuple[str, float, float] | dict[str, Any]],
        modo: str = "01",
    ) -> ResultadoMochila:
        """Aplica Programación Dinámica para maximizar el valor de paquetes admitidos en el servidor."""
        if modo == "acotada":
            return self.optimizador_mochila.resolver_acotada(capacidad_servidor, tareas)
        return self.optimizador_mochila.resolver_01(capacidad_servidor, tareas)


# =============================================================================
# Benchmarks, Demostración y Pruebas Automáticas
# =============================================================================
def ejecutar_demostracion() -> None:
    print("=" * 80)
    print("MÓDULO 1: ENRUTAMIENTO DE DATOS Y ASIGNACIÓN DE SERVIDORES (PROGRAMACIÓN DINÁMICA)")
    print("Simulador de Optimización para Redes de Centros de Datos · Métodos Cuantitativos")
    print("=" * 80)

    modulo1 = Modulo1()
    modulo1.cargar_topologia_defecto()

    # -------------------------------------------------------------------------
    # 1. Determinación de la Ruta Más Corta (Floyd-Warshall y Bellman por etapas)
    # -------------------------------------------------------------------------
    print("\n--- 1) DETERMINACIÓN DE LA RUTA MÁS CORTA POR PROGRAMACIÓN DINÁMICA ---")
    print("Principio de Bellman: D^(k)[i, j] = min( D^(k-1)[i, j], D^(k-1)[i, k] + D^(k-1)[k, j] )")

    res_fw = modulo1.calcular_ruta_optima(origen="GW", destinos=["S1", "S2", "S3"], metodo="floyd_warshall")
    print(f"Ruta óptima inicial (Floyd-Warshall): {res_fw.resumen()['ruta']}")
    print(f"Latencia total calculada: {res_fw.latencia_total:.2f} ms ({res_fw.num_saltos} saltos)")

    res_bellman = modulo1.calcular_ruta_optima(origen="GW", destinos=["S1", "S2", "S3"], metodo="bellman_etapas")
    print(f"Ruta óptima (Bellman por Etapas):   {res_bellman.resumen()['ruta']}")
    print(f"Latencia total (Bellman):           {res_bellman.latencia_total:.2f} ms")
    assert res_fw.ruta == res_bellman.ruta, "Ambos algoritmos de PD deben converger a la misma ruta óptima"

    # -------------------------------------------------------------------------
    # 2. Recalculado Dinámico de Pesos ante Congestión (Conexión con Pygame)
    # -------------------------------------------------------------------------
    print("\n--- 2) RECALCULADO DINÁMICO POR CONGESTIÓN EN ENLACES ---")
    print("Escenario: El enlace GW -> R1 experimenta congestión severa (c = 0.90).")
    impacto = modulo1.simular_congestion_enlace(enlace=("GW", "R1"), nivel_congestion=0.90)

    print(f"Enlace afectado:    {impacto['enlace_afectado'][0]} -> {impacto['enlace_afectado'][1]}")
    print(f"Ruta previa:        {' → '.join(impacto['ruta_anterior'])} (Costo: {impacto['costo_anterior']:.2f} ms)")
    print(f"Nueva ruta óptima:  {' → '.join(impacto['nueva_ruta'])} (Costo: {impacto['nuevo_costo']:.2f} ms)")
    print(f"Cambio detectado:   {impacto['ruta_cambio']} -> Alerta Pygame: [{impacto['alerta_visual']}]")

    # Escenario de falla de nodo
    print("\nEscenario adicional: Falla del Router intermedio R3 (nodo fuera de servicio).")
    res_falla = modulo1.calcular_ruta_optima(origen="GW", destinos=["S1", "S2", "S3"], no_disponibles={"R3"})
    print(f"Ruta recalculada con R3 caído: {' → '.join(res_falla.ruta)} (Latencia: {res_falla.latencia_total:.2f} ms)")

    # -------------------------------------------------------------------------
    # 3. Modelo de Volumen-Carga (Problema de la Mochila 0/1)
    # -------------------------------------------------------------------------
    print("\n--- 3) MODELO DE VOLUMEN-CARGA: MOCHILA 0/1 (PD TABULAR) ---")
    print("Ecuación de Bellman: DP[i, w] = max( DP[i-1, w], DP[i-1, w - w_i] + v_i )")

    capacidad_servidor = 28.0  # Capacidad disponible de CPU/RAM
    paquetes_llegada = [
        ItemCarga(id_item="P1-Control", peso=4.0, valor=9.0, metadatos={"tipo": "SLA-Alto"}),
        ItemCarga(id_item="P2-Web", peso=8.0, valor=14.0, metadatos={"tipo": "Web-App"}),
        ItemCarga(id_item="P3-Analitica", peso=12.0, valor=20.0, metadatos={"tipo": "Batch"}),
        ItemCarga(id_item="P4-Streaming", peso=6.0, valor=11.0, metadatos={"tipo": "Multimedia"}),
        ItemCarga(id_item="P5-BatchLote", peso=16.0, valor=22.0, metadatos={"tipo": "Background"}),
    ]

    res_mochila = modulo1.optimizar_admision_servidor(capacidad_servidor, paquetes_llegada, modo="01")
    print(f"Capacidad del servidor: {res_mochila.capacidad_servidor:.1f} unidades")
    print(f"Valor total maximizado: {res_mochila.valor_total:.2f}")
    print(f"Capacidad consumida:    {res_mochila.peso_total:.1f} / {res_mochila.capacidad_servidor:.1f} ({res_mochila.porcentaje_utilizacion:.1f}%)")
    print(f"Capacidad ociosa:       {res_mochila.capacidad_remanente:.1f} unidades")
    print("Paquetes admitidos:")
    for item in res_mochila.items_seleccionados:
        print(f"  ✓ {item.id_item:15} | Peso: {item.peso:4.1f} | Valor/Prioridad: {item.valor:4.1f}")
    print("Paquetes descartados / diferidos:")
    for item in res_mochila.items_rechazados:
        print(f"  ✗ {item.id_item:15} | Peso: {item.peso:4.1f} | Valor/Prioridad: {item.valor:4.1f}")

    print(f"\nDimensiones de la tabla DP calculada: {res_mochila.tabla_dp.shape} (N+1 x W+1)")
    print(f"Tiempo de cómputo de PD: {res_mochila.tiempo_ejecucion_ms:.4f} ms")

    # -------------------------------------------------------------------------
    # 4. Problema de la Mochila Acotada (Bounded Knapsack)
    # -------------------------------------------------------------------------
    print("\n--- 4) MODELO DE MOCHILA ACOTADA (BOUNDED KNAPSACK) ---")
    paquetes_acotados = [
        ItemCarga(id_item="Tarea-Microservicio", peso=3.0, valor=7.0, limite=4),
        ItemCarga(id_item="Tarea-ConsultaBD", peso=5.0, valor=11.0, limite=3),
        ItemCarga(id_item="Tarea-ReporteLote", peso=10.0, valor=18.0, limite=2),
    ]
    res_acotada = modulo1.optimizar_admision_servidor(capacidad_servidor=25.0, tareas=paquetes_acotados, modo="acotada")
    print(f"Capacidad del servidor: {res_acotada.capacidad_servidor:.1f} unidades")
    print(f"Valor óptimo obtenido:  {res_acotada.valor_total:.2f}")
    print(f"Carga asignada:         {res_acotada.peso_total:.1f} ({res_acotada.porcentaje_utilizacion:.1f}%)")
    print("Desglose de tareas admitidas:")
    for item in res_acotada.items_seleccionados:
        instancias = item.metadatos.get("instancias_admitidas", item.limite)
        lim_orig = item.metadatos.get("limite_original", item.limite)
        print(f"  ✓ {item.id_item:20} -> {instancias}/{lim_orig} admitidas | Carga: {item.peso:.1f} | Valor: {item.valor:.1f}")

    # -------------------------------------------------------------------------
    # 5. Validación Cuantitativa y Pruebas Automáticas
    # -------------------------------------------------------------------------
    print("\n--- 5) VALIDACIÓN AUTOMÁTICA DE RESULTADOS ---")
    # Validación Mochila: no exceder capacidad
    assert res_mochila.peso_total <= capacidad_servidor + 1e-6, "Violación de restricción de capacidad"
    assert res_acotada.peso_total <= 25.0 + 1e-6, "Violación de restricción en mochila acotada"
    # Validación Enrutamiento: Floyd-Warshall encuentra camino válido
    assert len(res_fw.ruta) >= 2, "La ruta debe contener al menos origen y destino"
    assert res_fw.ruta[0] == "GW", "El origen de la ruta debe ser el nodo Gateway"
    print("Todas las aserciones cuantitativas pasaron satisfactoriamente (100% OK).")
    print("=" * 80)


if __name__ == "__main__":
    ejecutar_demostracion()
