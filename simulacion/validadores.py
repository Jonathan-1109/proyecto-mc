from __future__ import annotations

from typing import Any, Mapping, Sequence


def exigir_numero_positivo(nombre: str, valor: Any, *, permitir_cero: bool = False) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{nombre}' debe ser un número, recibido: {valor!r}") from exc

    if permitir_cero:
        if numero < 0:
            raise ValueError(f"'{nombre}' debe ser >= 0, recibido: {numero}")
    elif numero <= 0:
        raise ValueError(f"'{nombre}' debe ser > 0, recibido: {numero}")
    return numero


def exigir_entero(nombre: str, valor: Any, *, minimo: int | None = None) -> int:
    try:
        if isinstance(valor, bool):
            raise TypeError
        numero = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{nombre}' debe ser un entero, recibido: {valor!r}") from exc

    if minimo is not None and numero < minimo:
        raise ValueError(f"'{nombre}' debe ser >= {minimo}, recibido: {numero}")
    return numero


def exigir_probabilidad(nombre: str, valor: Any) -> float:
    numero = exigir_numero_positivo(nombre, valor, permitir_cero=True)
    if numero > 1.0:
        raise ValueError(f"'{nombre}' debe estar en [0, 1], recibido: {numero}")
    return numero


def validar_topologia(topologia: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(topologia, Mapping):
        raise ValueError("topologia debe ser un objeto/diccionario")

    nodos = topologia.get("nodos") or topologia.get("nodes")
    enlaces = topologia.get("enlaces") or topologia.get("edges")
    if not isinstance(nodos, Sequence) or not nodos:
        raise ValueError("topologia.nodos debe ser una lista no vacía")
    if not isinstance(enlaces, Sequence) or not enlaces:
        raise ValueError("topologia.enlaces debe ser una lista no vacía")

    ids_nodo: set[str] = set()
    nodos_limpios: list[dict[str, Any]] = []
    for crudo in nodos:
        if not isinstance(crudo, Mapping):
            raise ValueError("cada nodo debe ser un objeto")
        id_nodo = str(crudo.get("id", "")).strip()
        if not id_nodo:
            raise ValueError("cada nodo requiere un 'id' no vacío")
        if id_nodo in ids_nodo:
            raise ValueError(f"id de nodo duplicado: {id_nodo}")

        tipo = str(crudo.get("tipo") or crudo.get("kind") or "router").lower()
        mapa_tipo = {
            "gateway": "puerta",
            "puerta": "puerta",
            "router": "router",
            "server": "servidor",
            "servidor": "servidor",
        }
        if tipo not in mapa_tipo:
            raise ValueError(f"nodo {id_nodo}: tipo debe ser puerta|router|servidor")
        tipo = mapa_tipo[tipo]

        x = float(exigir_numero_positivo(f"nodo[{id_nodo}].x", crudo.get("x", 0), permitir_cero=True))
        y = float(exigir_numero_positivo(f"nodo[{id_nodo}].y", crudo.get("y", 0), permitir_cero=True))
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError(f"nodo {id_nodo}: x/y deben estar en [0, 1]")

        capacidad = float(
            exigir_numero_positivo(
                f"nodo[{id_nodo}].capacidad",
                crudo.get("capacidad", crudo.get("capacity", 0)),
                permitir_cero=True,
            )
        )
        cluster = int(crudo.get("cluster", 0) or 0)
        ids_nodo.add(id_nodo)
        nodos_limpios.append(
            {
                "id": id_nodo,
                "tipo": tipo,
                "x": x,
                "y": y,
                "capacidad": capacidad,
                "cluster": cluster,
            }
        )

    if not any(n["tipo"] == "puerta" for n in nodos_limpios):
        raise ValueError("la topología debe incluir al menos una puerta de enlace")
    if not any(n["tipo"] == "servidor" for n in nodos_limpios):
        raise ValueError("la topología debe incluir al menos un servidor")

    enlaces_limpios: list[tuple[str, str, float]] = []
    for crudo in enlaces:
        if isinstance(crudo, (list, tuple)) and len(crudo) == 3:
            origen, destino, latencia = crudo
        elif isinstance(crudo, Mapping):
            origen = crudo.get("origen") or crudo.get("source")
            destino = crudo.get("destino") or crudo.get("target")
            latencia = crudo.get("latencia") or crudo.get("latency")
        else:
            raise ValueError("cada enlace debe ser [origen, destino, latencia] o un objeto")

        origen_s, destino_s = str(origen).strip(), str(destino).strip()
        if origen_s not in ids_nodo or destino_s not in ids_nodo:
            raise ValueError(f"enlace con nodo desconocido: {origen_s!r} -> {destino_s!r}")
        lat = exigir_numero_positivo(f"enlace {origen_s}->{destino_s} latencia", latencia)
        enlaces_limpios.append((origen_s, destino_s, lat))

    return {"nodos": nodos_limpios, "enlaces": enlaces_limpios}


def validar_config_simulacion(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "duracion_sim": exigir_numero_positivo(
            "duracion_sim", config.get("duracion_sim", config.get("sim_duration", 120))
        ),
        "tasa_llegada": exigir_numero_positivo(
            "tasa_llegada", config.get("tasa_llegada", config.get("arrival_rate", 2.5))
        ),
        "semilla": exigir_entero("semilla", config.get("semilla", config.get("seed", 42)), minimo=0),
        "tasa_falla": exigir_probabilidad(
            "tasa_falla", config.get("tasa_falla", config.get("failure_rate", 0.008))
        ),
        "tasa_recuperacion": exigir_probabilidad(
            "tasa_recuperacion",
            config.get("tasa_recuperacion", config.get("recovery_rate", 0.20)),
        ),
        "intervalo_opt": exigir_numero_positivo(
            "intervalo_opt", config.get("intervalo_opt", config.get("opt_interval", 1.0))
        ),
        "presupuesto_energia": exigir_numero_positivo(
            "presupuesto_energia",
            config.get("presupuesto_energia", config.get("energy_budget", 100)),
        ),
        "fps": exigir_entero("fps", config.get("fps", 30), minimo=1),
        "sin_ventana": bool(config.get("sin_ventana", config.get("headless", False))),
        "ia_activa": bool(config.get("ia_activa", config.get("ai_enabled", True))),
        "dir_reportes": str(config.get("dir_reportes", config.get("report_dir", "reports"))),
    }
