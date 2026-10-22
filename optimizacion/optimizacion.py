from __future__ import annotations
from typing import Sequence
import numpy as np
import sympy as sp


class Optimizacion:
    """Optimización no lineal aplicada al consumo de un centro de datos.

    Tres análisis clásicos:
    1. Una variable: temperatura del servidor en función de la carga.
    2. Gradiente: potencia óptima de los ventiladores de refrigeración.
    3. Lagrange: reparto del presupuesto eléctrico entre clústeres.
    """

    def __init__(self, umbral_emergencia: float = 70.0):
        self.umbral_emergencia = float(umbral_emergencia)
        self.potencia_refrigeracion = 0.40

    def analisis_consumo_temperatura(
        self,
        a: float = 120.0,
        b: float = 90.0,
        c: float = 18.0,
        d: float = 35.0,
        carga_min: float = 0.0,
        carga_max: float = 1.2,
    ) -> dict:
        if carga_min >= carga_max:
            raise ValueError("carga_min debe ser menor que carga_max")

        x = sp.Symbol("x", real=True)
        temperatura = a * x**3 - b * x**2 + c * x + d
        primera = sp.diff(temperatura, x)
        segunda = sp.diff(temperatura, x, 2)

        puntos: list[dict] = []
        for raiz in sp.solve(sp.Eq(primera, 0), x):
            valor = complex(sp.N(raiz))
            if abs(valor.imag) > 1e-9:
                continue
            carga = valor.real
            if not (carga_min <= carga <= carga_max):
                continue
            curvatura = float(segunda.subs(x, carga))
            if curvatura > 1e-9:
                tipo = "mínimo"
            elif curvatura < -1e-9:
                tipo = "máximo"
            else:
                tipo = "punto de inflexión"
            puntos.append(
                {
                    "carga": carga,
                    "temperatura": float(temperatura.subs(x, carga)),
                    "tipo": tipo,
                    "curvatura": curvatura,
                }
            )

        # La inflexión puede no ser estacionaria: se calcula aparte.
        for raiz in sp.solve(sp.Eq(segunda, 0), x):
            valor = complex(sp.N(raiz))
            if abs(valor.imag) > 1e-9:
                continue
            carga = valor.real
            if not (carga_min <= carga <= carga_max):
                continue
            if any(abs(carga - p["carga"]) < 1e-9 for p in puntos):
                continue
            puntos.append(
                {
                    "carga": carga,
                    "temperatura": float(temperatura.subs(x, carga)),
                    "tipo": "punto de inflexión",
                    "curvatura": 0.0,
                }
            )
        puntos.sort(key=lambda p: p["carga"])

        maximos = [p for p in puntos if p["tipo"] == "máximo"]
        minimos = [p for p in puntos if p["tipo"] == "mínimo"]
        inflexiones = [p for p in puntos if p["tipo"] == "punto de inflexión"]
        punto_critico = max(maximos, key=lambda p: p["temperatura"]) if maximos else None

        # Cruce del umbral de emergencia: T(x) = umbral.
        coeficientes = np.trim_zeros(
            np.array([a, -b, c, d - self.umbral_emergencia], dtype=float), trim="f"
        )
        raices_cruce: list[float] = []
        if coeficientes.size > 1:
            for raiz in np.roots(coeficientes):
                if abs(raiz.imag) < 1e-9 and carga_min <= raiz.real <= carga_max:
                    raices_cruce.append(float(raiz.real))

        carga_emergencia = None
        for carga in sorted({carga_min, carga_max, *raices_cruce}):
            if float(temperatura.subs(x, carga)) >= self.umbral_emergencia - 1e-9:
                carga_emergencia = carga
                break

        return {
            "modelo": str(temperatura),
            "derivada": str(primera),
            "segunda_derivada": str(segunda),
            "puntos_estacionarios": puntos,
            "maximos": maximos,
            "minimos": minimos,
            "inflexiones": inflexiones,
            "punto_critico": punto_critico,
            "umbral_emergencia": self.umbral_emergencia,
            "carga_emergencia": carga_emergencia,
            "requiere_enfriamiento_emergencia": carga_emergencia is not None,
        }

    def ajuste_refrigeracion_gradiente(
        self,
        temp_ambiente: float = 25.0,
        calor_carga: float = 45.0,
        capacidad_enfriamiento: float = 40.0,
        temp_objetivo: float = 40.0,
        potencia_inicial: float | None = None,
        tasa_aprendizaje: float = 0.20,
        tolerancia: float = 1e-6,
        max_iteraciones: int = 200,
    ) -> dict:
        """Minimiza el coste energético ajustando la potencia de los ventiladores.

        T(p) = temp_ambiente + calor_carga - capacidad_enfriamiento·p
        C(p) = coef_energia·p² + coef_lineal·p + coef_termico·max(0, T(p)-T_obj)²

        El primer término es el consumo no lineal de los ventiladores y el
        tercero penaliza sobrepasar la temperatura objetivo. Se aplica
        gradiente descendente con búsqueda de línea y p acotada a [0, 1].
        """
        if capacidad_enfriamiento <= 0:
            raise ValueError("capacidad_enfriamiento debe ser positiva")
        if tasa_aprendizaje <= 0 or max_iteraciones <= 0:
            raise ValueError("tasa_aprendizaje y max_iteraciones deben ser positivos")

        coef_energia = 0.80
        coef_lineal = 0.15
        coef_termico = 0.02

        def temperatura(potencia: float) -> float:
            return temp_ambiente + calor_carga - capacidad_enfriamiento * potencia

        def costo(potencia: float) -> float:
            exceso = max(0.0, temperatura(potencia) - temp_objetivo)
            return coef_energia * potencia**2 + coef_lineal * potencia + coef_termico * exceso**2

        def gradiente(potencia: float) -> float:
            exceso = max(0.0, temperatura(potencia) - temp_objetivo)
            return (
                2 * coef_energia * potencia
                + coef_lineal
                - 2 * coef_termico * capacidad_enfriamiento * exceso
            )

        if potencia_inicial is None:
            potencia_inicial = self.potencia_refrigeracion
        potencia = float(np.clip(potencia_inicial, 0.0, 1.0))
        costo_inicial = costo(potencia)
        iteraciones = 0
        convergido = False

        for iteraciones in range(1, max_iteraciones + 1):
            grad = gradiente(potencia)
            if abs(grad) < tolerancia:
                convergido = True
                break

            paso = tasa_aprendizaje
            candidato = float(np.clip(potencia - paso * grad, 0.0, 1.0))
            while costo(candidato) > costo(potencia) and paso > 1e-12:
                paso *= 0.5
                candidato = float(np.clip(potencia - paso * grad, 0.0, 1.0))

            if abs(candidato - potencia) < tolerancia:
                potencia = candidato
                convergido = True
                break
            potencia = candidato

        potencia = float(np.clip(potencia, 0.0, 1.0))
        self.potencia_refrigeracion = potencia

        return {
            "potencia_inicial": float(np.clip(potencia_inicial, 0.0, 1.0)),
            "potencia_optima": potencia,
            "costo_inicial": costo_inicial,
            "costo_minimo": costo(potencia),
            "gradiente_final": gradiente(potencia),
            "temperatura_estimada": temperatura(potencia),
            "iteraciones": iteraciones,
            "convergido": convergido,
            "temp_objetivo": temp_objetivo,
        }

    # ------------------------------------------------------------------
    # 3. Asignación del presupuesto eléctrico: Lagrange
    # ------------------------------------------------------------------
    def asignacion_presupuesto_lagrange(
        self,
        presupuesto: float,
        demandas: Sequence[float],
        pesos: Sequence[float] | None = None,
        tolerancia: float = 1e-9,
    ) -> dict:
        """Maximiza R(e) = Σ wᵢ·ln(1 + eᵢ/dᵢ) sujeto a Σ eᵢ = presupuesto, eᵢ ≥ 0.

        Condición de Lagrange: ∂L/∂eᵢ = wᵢ/(dᵢ+eᵢ) - λ = 0, de donde
        eᵢ = wᵢ/λ - dᵢ. Sumando la restricción, λ = Σwᵢ/(B+Σdᵢ). Las
        asignaciones negativas se fijan a cero (condiciones KKT) y se
        recalcula λ con los clústeres activos.
        """
        demandas_arr = np.asarray(demandas, dtype=float)
        if demandas_arr.ndim != 1 or demandas_arr.size == 0:
            raise ValueError("demandas debe ser una lista no vacía")
        if presupuesto <= 0:
            raise ValueError("presupuesto debe ser positivo")
        if np.any(demandas_arr <= 0):
            raise ValueError("todas las demandas deben ser positivas")

        n = demandas_arr.size
        if pesos is None:
            pesos_arr = np.ones(n)
        else:
            pesos_arr = np.asarray(pesos, dtype=float)
            if pesos_arr.size != n or np.any(pesos_arr <= 0):
                raise ValueError("pesos debe tener el mismo tamaño y ser positivos")

        # Derivación simbólica (se conserva para mostrar las parciales).
        e = sp.symbols(f"e0:{n}", positive=True)
        lam = sp.Symbol("lambda", positive=True)
        rendimiento_simbolico = sum(
            pesos_arr[i] * sp.log(1 + e[i] / demandas_arr[i]) for i in range(n)
        )
        lagrangiano = rendimiento_simbolico + lam * (sum(e) - presupuesto)
        parciales = [sp.diff(lagrangiano, e[i]) for i in range(n)]

        asignacion = np.zeros(n)
        activos = list(range(n))
        lam_final = 0.0
        while True:
            w_act = pesos_arr[activos]
            d_act = demandas_arr[activos]
            lam_final = float(w_act.sum() / (presupuesto + d_act.sum()))
            propuesta = w_act / lam_final - d_act

            if np.all(propuesta >= -tolerancia):
                asignacion[activos] = np.maximum(propuesta, 0.0)
                break

            # KKT: eᵢ < 0 => eᵢ = 0; se recalcula λ sin esos clústeres.
            activos = [i for i, valor in zip(activos, propuesta) if valor >= -tolerancia]
            if not activos:
                raise RuntimeError("No se encontró una asignación factible")

        rendimiento_optimo = float(
            np.sum(pesos_arr * np.log1p(asignacion / demandas_arr))
        )
        reparto_igual = np.full(n, presupuesto / n)
        rendimiento_igualitario = float(
            np.sum(pesos_arr * np.log1p(reparto_igual / demandas_arr))
        )

        condiciones_kkt = all(
            abs(pesos_arr[i] / (demandas_arr[i] + asignacion[i]) - lam_final) < 1e-6
            for i in activos
        ) and all(
            pesos_arr[i] / demandas_arr[i] <= lam_final + 1e-6
            for i in range(n)
            if i not in activos
        )

        return {
            "modelo": "R(e) = Σ wᵢ·ln(1 + eᵢ/dᵢ)",
            "lagrangiano": str(lagrangiano),
            "parciales": [str(p) for p in parciales],
            "asignacion": [float(valor) for valor in asignacion],
            "multiplicador_lagrange": lam_final,
            "rendimiento_optimo": rendimiento_optimo,
            "rendimiento_igualitario": rendimiento_igualitario,
            "mejora": rendimiento_optimo - rendimiento_igualitario,
            "clusters_activos": activos,
            "restriccion_cumplida": bool(
                abs(asignacion.sum() - presupuesto) <= tolerancia * max(1.0, presupuesto)
            ),
            "condiciones_kkt": bool(condiciones_kkt),
        }


if __name__ == "__main__":
    op = Optimizacion()

    print("1) ANÁLISIS DEL CONSUMO")
    analisis = op.analisis_consumo_temperatura()
    print(f"T(x) = {analisis['modelo']}")
    print(f"T'(x) = {analisis['derivada']}")
    print(f"T''(x) = {analisis['segunda_derivada']}")
    print("\nPuntos estacionarios y de inflexión:")
    for punto in analisis["puntos_estacionarios"]:
        print(
            f"  x={punto['carga']:.4f}  T={punto['temperatura']:.2f} °C"
            f"  T''={punto['curvatura']:.2f}  -> {punto['tipo']}"
        )
    if analisis["punto_critico"]:
        critico = analisis["punto_critico"]
        print(
            f"\nPunto crítico térmico (máximo): carga={critico['carga']:.4f},"
            f" T={critico['temperatura']:.2f} °C"
        )
    if analisis["requiere_enfriamiento_emergencia"]:
        print(
            f"Enfriamiento de emergencia desde carga="
            f"{analisis['carga_emergencia']:.4f} (umbral "
            f"{analisis['umbral_emergencia']:.1f} °C)"
        )
    else:
        print("No se alcanza el umbral de emergencia en el rango analizado.")

    print("2) AJUSTE DINÁMICO DE REFRIGERACIÓN")
    refrigeracion = op.ajuste_refrigeracion_gradiente()
    print(f"Potencia inicial: {refrigeracion['potencia_inicial']:.4f}")
    print(f"Potencia óptima: {refrigeracion['potencia_optima']:.4f}")
    print(f"Temperatura estimada: {refrigeracion['temperatura_estimada']:.2f} °C")
    print(
        f"Coste: {refrigeracion['costo_inicial']:.4f} -> "
        f"{refrigeracion['costo_minimo']:.4f}"
    )
    print(
        f"Iteraciones: {refrigeracion['iteraciones']}  "
        f"convergido: {refrigeracion['convergido']}"
    )

    print("3) ASIGNACIÓN DEL PRESUPUESTO ELÉCTRICO")
    presupuesto = 100.0
    asignacion = op.asignacion_presupuesto_lagrange(
        presupuesto=presupuesto,
        demandas=[30.0, 25.0, 40.0],
        pesos=[1.5, 1.0, 0.8],
    )
    print(f"Modelo: {asignacion['modelo']}")
    for parcial in asignacion["parciales"]:
        print(f"  ∂L/∂e = {parcial}")
    print(f"λ = {asignacion['multiplicador_lagrange']:.6f}")
    for i, energia in enumerate(asignacion["asignacion"], start=1):
        print(f"  Clúster {i}: {energia:.4f} unidades de energía")
    print(f"Energía total asignada: {sum(asignacion['asignacion']):.4f}")
    print(
        f"Rendimiento: {asignacion['rendimiento_optimo']:.4f} "
        f"(reparto igual: {asignacion['rendimiento_igualitario']:.4f}, "
        f"mejora: {asignacion['mejora']:.4f})"
    )
    print(
        f"Restricción cumplida: {asignacion['restriccion_cumplida']}  "
        f"KKT: {asignacion['condiciones_kkt']}"
    )