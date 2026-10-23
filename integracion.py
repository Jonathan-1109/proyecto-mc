#!/usr/bin/env python3
"""Verificación de la unión Módulo 1 + Módulo 2 + Módulo 3."""

from __future__ import annotations

import sys
import traceback


def verificar_modulo1() -> None:
    from enrutamiento.modulo1 import Modulo1
    from enrutamiento.mochila import ItemCarga

    m1 = Modulo1()
    m1.cargar_topologia_defecto()
    ruta = m1.calcular_ruta_optima()
    assert ruta.es_factible and ruta.ruta[0] == "GW"
    impacto = m1.simular_congestion_enlace(("GW", "R1"), 0.90)
    assert "nueva_ruta" in impacto
    mochila = m1.optimizar_admision_servidor(
        20.0,
        [
            ItemCarga("A", 5, 10),
            ItemCarga("B", 8, 14),
            ItemCarga("C", 12, 18),
        ],
    )
    assert mochila.peso_total <= 20.0 + 1e-6
    print(f"[OK] Módulo 1 — ruta={ruta.resumen()['ruta']} · mochila_valor={mochila.valor_total:.1f}")


def verificar_modulo2() -> None:
    from optimizacion.optimizacion import Optimizacion

    op = Optimizacion()
    analisis = op.analisis_consumo_temperatura()
    assert analisis["puntos_estacionarios"]
    refri = op.ajuste_refrigeracion_gradiente()
    assert 0.0 <= refri["potencia_optima"] <= 1.0
    energia = op.asignacion_presupuesto_lagrange(
        presupuesto=100.0,
        demandas=[30.0, 25.0, 40.0],
        pesos=[1.5, 1.0, 0.8],
    )
    assert energia["restriccion_cumplida"]
    print(
        f"[OK] Módulo 2 — P*={refri['potencia_optima']:.3f} · "
        f"λ={energia['multiplicador_lagrange']:.4f} · "
        f"asignación={[round(x, 2) for x in energia['asignacion']]}"
    )


def verificar_puente() -> None:
    from simulacion.puente_matematico import (
        AsignadorEnergiaLagrange,
        AsignadorMochila,
        ControladorGradienteRefrigeracion,
        EnrutadorProgramacionDinamica,
        ModeloTemperatura,
    )

    enrutador = EnrutadorProgramacionDinamica(["GW", "R1", "R2", "S1", "S2"])
    ruta, costo = enrutador.ruta_mas_corta(
        "GW",
        ["S1", "S2"],
        [("GW", "R1", 8), ("R1", "S1", 12), ("GW", "R2", 10), ("R2", "S2", 7)],
    )
    assert ruta and costo < float("inf")
    sel = AsignadorMochila.seleccionar([("a", 2, 5), ("b", 3, 6), ("c", 4, 7)], 5)
    assert sel
    temp = ModeloTemperatura()
    t0, t1 = temp.temperatura(0.0), temp.temperatura(1.0)
    assert t1 > t0
    cool = ControladorGradienteRefrigeracion()
    p = cool.paso(60.0)
    assert 0.0 <= p <= 1.0
    energia = AsignadorEnergiaLagrange(100.0, 3)
    alloc, lam = energia.asignar([1.0, 2.0, 3.0])
    assert abs(alloc.sum() - 100.0) < 1e-4 and lam > 0
    print(
        f"[OK] Puente M1/M2→M3 — ruta={ruta} · mochila={sel} · "
        f"T(1)={t1:.1f} · P={p:.3f} · λ={lam:.4f}"
    )


def verificar_simulacion(duracion: float = 25.0) -> None:
    from simulacion.ejecutor import EjecutorSimulacion

    ejecutor = EjecutorSimulacion(
        {
            "duracion_sim": duracion,
            "tasa_llegada": 2.5,
            "semilla": 42,
            "sin_ventana": True,
            "ia_activa": True,
            "dir_reportes": "reports",
        }
    )
    ejecutor.ia.api_key = ""
    resultado = ejecutor.ejecutar()
    metricas = resultado["metricas"]
    assert metricas["paquetes_creados"] > 0
    assert metricas["ruta_activa"]
    assert metricas["asignacion_energia"]
    print(
        f"[OK] Módulo 3 integrado — "
        f"creados={metricas['paquetes_creados']} "
        f"completados={metricas['paquetes_completados']} "
        f"ruta={' → '.join(metricas['ruta_activa'])} "
        f"P={metricas['potencia_refrigeracion']:.3f} "
        f"λ={metricas['lambda_lagrange']:.4f} "
        f"pdf={resultado['pdf']}"
    )


def main() -> int:
    print("=" * 72)
    print("VERIFICACIÓN INTEGRADA — DataStream Networks (M1 + M2 + M3)")
    print("=" * 72)
    pasos = [
        ("Módulo 1", verificar_modulo1),
        ("Módulo 2", verificar_modulo2),
        ("Puente matemático", verificar_puente),
        ("Simulación M3", verificar_simulacion),
    ]
    fallos = 0
    for nombre, fn in pasos:
        try:
            fn()
        except Exception:
            fallos += 1
            print(f"[FAIL] {nombre}")
            traceback.print_exc()
    print("=" * 72)
    if fallos:
        print(f"Resultado: {fallos} fallo(s)")
        return 1
    print("Resultado: todos los módulos operan correctamente en conjunto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
