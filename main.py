#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from simulacion.defaults import (
    DURACION_SIM_DEFECTO,
    FPS_DEFECTO,
    PRESUPUESTO_ENERGIA_DEFECTO,
    SEMILLA_DEFECTO,
    TASA_FALLA_DEFECTO,
    TASA_LLEGADA_DEFECTO,
    TASA_RECUPERACION_DEFECTO,
)
from simulacion.ejecutor import EjecutorSimulacion, banner_defaults, cargar_topologia
from simulacion.validadores import (
    exigir_entero,
    exigir_numero_positivo,
    exigir_probabilidad,
)


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datastream-sim",
        description=(
            "DataStream Networks — unión de Módulo 1 (PD), Módulo 2 (no lineal) "
            "y Módulo 3 (SimPy/Pygame + informes)."
        ),
    )
    parser.add_argument("--duracion", type=float, default=DURACION_SIM_DEFECTO)
    parser.add_argument("--tasa-llegada", type=float, default=TASA_LLEGADA_DEFECTO)
    parser.add_argument("--semilla", type=int, default=SEMILLA_DEFECTO)
    parser.add_argument("--tasa-falla", type=float, default=TASA_FALLA_DEFECTO)
    parser.add_argument("--tasa-recuperacion", type=float, default=TASA_RECUPERACION_DEFECTO)
    parser.add_argument("--presupuesto-energia", type=float, default=PRESUPUESTO_ENERGIA_DEFECTO)
    parser.add_argument("--fps", type=int, default=FPS_DEFECTO)
    parser.add_argument("--topologia", type=str, default=None)
    parser.add_argument("--dir-reportes", type=str, default="reports")
    parser.add_argument("--sin-ventana", action="store_true")
    parser.add_argument(
        "--sin-ia",
        action="store_true",
        help="Forzar análisis local (no llama a Gemini).",
    )
    parser.add_argument("--mostrar-defaults", action="store_true")
    parser.add_argument(
        "--modulo1",
        action="store_true",
        help="Ejecutar demostración del Módulo 1 (Programación Dinámica).",
    )
    parser.add_argument(
        "--modulo2",
        action="store_true",
        help="Ejecutar demostración del Módulo 2 (Optimización No Lineal).",
    )
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="Verificar la integración completa M1+M2+M3.",
    )
    return parser


def parsear_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        args.duracion = exigir_numero_positivo("duracion", args.duracion)
        args.tasa_llegada = exigir_numero_positivo("tasa_llegada", args.tasa_llegada)
        args.semilla = exigir_entero("semilla", args.semilla, minimo=0)
        args.tasa_falla = exigir_probabilidad("tasa_falla", args.tasa_falla)
        args.tasa_recuperacion = exigir_probabilidad(
            "tasa_recuperacion", args.tasa_recuperacion
        )
        args.presupuesto_energia = exigir_numero_positivo(
            "presupuesto_energia", args.presupuesto_energia
        )
        args.fps = exigir_entero("fps", args.fps, minimo=1)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def ejecutar_modulo2() -> None:
    from optimizacion.optimizacion import Optimizacion

    op = Optimizacion()
    print("=" * 72)
    print("MÓDULO 2: OPTIMIZACIÓN ENERGÉTICA Y RENDIMIENTO (NO LINEAL)")
    print("=" * 72)

    print("\n--- 1) Análisis del consumo (una variable) ---")
    analisis = op.analisis_consumo_temperatura()
    print(f"T(x) = {analisis['modelo']}")
    for punto in analisis["puntos_estacionarios"]:
        print(
            f"  x={punto['carga']:.4f}  T={punto['temperatura']:.2f} °C"
            f"  -> {punto['tipo']}"
        )
    if analisis["punto_critico"]:
        c = analisis["punto_critico"]
        print(f"Punto crítico térmico: carga={c['carga']:.4f}, T={c['temperatura']:.2f} °C")

    print("\n--- 2) Refrigeración por gradiente ---")
    refri = op.ajuste_refrigeracion_gradiente()
    print(f"Potencia óptima: {refri['potencia_optima']:.4f}")
    print(f"Temperatura estimada: {refri['temperatura_estimada']:.2f} °C")
    print(f"Convergido: {refri['convergido']} en {refri['iteraciones']} iteraciones")

    print("\n--- 3) Presupuesto eléctrico (Lagrange) ---")
    energia = op.asignacion_presupuesto_lagrange(
        presupuesto=100.0,
        demandas=[30.0, 25.0, 40.0],
        pesos=[1.5, 1.0, 0.8],
    )
    print(f"λ = {energia['multiplicador_lagrange']:.6f}")
    for i, valor in enumerate(energia["asignacion"], start=1):
        print(f"  Clúster {i}: {valor:.4f}")
    print(
        f"Restricción OK={energia['restriccion_cumplida']} · "
        f"KKT={energia['condiciones_kkt']}"
    )
    print("=" * 72)


def main(argv: list[str] | None = None) -> int:
    args = parsear_args(argv)
    if args.mostrar_defaults:
        print(banner_defaults())
        return 0

    if args.verificar:
        from integracion import main as verificar_main

        return verificar_main()

    if args.modulo1:
        from enrutamiento.modulo1 import ejecutar_demostracion

        ejecutar_demostracion()
        return 0

    if args.modulo2:
        ejecutar_modulo2()
        return 0

    topologia = None
    if args.topologia:
        try:
            topologia = cargar_topologia(args.topologia)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] Topología inválida: {exc}", file=sys.stderr)
            return 2

    config = {
        "duracion_sim": args.duracion,
        "tasa_llegada": args.tasa_llegada,
        "semilla": args.semilla,
        "tasa_falla": args.tasa_falla,
        "tasa_recuperacion": args.tasa_recuperacion,
        "presupuesto_energia": args.presupuesto_energia,
        "fps": args.fps,
        "sin_ventana": args.sin_ventana,
        "ia_activa": True,
        "dir_reportes": args.dir_reportes,
    }

    print("DataStream Networks — Simulación integrada (M1+M2+M3)")
    print(banner_defaults())
    print("Iniciando simulación…")

    ejecutor = EjecutorSimulacion(config, topologia)
    if args.sin_ia:
        ejecutor.ia.api_key = ""

    try:
        resultado = ejecutor.ejecutar()
    except Exception as exc:  # noqa: BLE001
        print(f"[error] Falló la simulación: {exc}", file=sys.stderr)
        return 1

    metricas = resultado["metricas"]
    print("\n=== Corrida completa ===")
    print(
        f"Creados/Completados/Descartados: {metricas['paquetes_creados']}/"
        f"{metricas['paquetes_completados']}/{metricas['paquetes_descartados']}"
    )
    print(f"Latencia media: {metricas['latencia_promedio']:.4f}")
    print(f"Ruta PD final: {' → '.join(metricas.get('ruta_activa') or [])}")
    print(
        f"Refrigeración P={metricas['potencia_refrigeracion']:.3f} · "
        f"λ={metricas['lambda_lagrange']:.4f}"
    )
    print(
        f"IA: {resultado['analisis'].get('fuente')} · "
        f"riesgo={resultado['analisis'].get('nivel_riesgo')}"
    )
    print(f"PDF: {resultado['pdf']}")
    print(f"JSON: {resultado['json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
