from __future__ import annotations

from typing import Any
import json
import os
import urllib.error
import urllib.request


def cargar_env(ruta: str = ".env") -> None:
    if not os.path.isfile(ruta):
        return
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave, valor = clave.strip(), valor.strip().strip('"').strip("'")
            if clave and clave not in os.environ:
                os.environ[clave] = valor


class ClienteInformeIA:
    def __init__(
        self,
        api_key: str | None = None,
        modelo: str | None = None,
        timeout: float = 45.0,
    ):
        cargar_env()
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("DATASTREAM_AI_API_KEY")
            or ""
        )
        self.modelo = (
            modelo
            or os.getenv("GEMINI_MODEL")
            or os.getenv("DATASTREAM_AI_MODEL")
            or "gemini-2.0-flash"
        )
        self.timeout = timeout

    @property
    def disponible(self) -> bool:
        return bool(self.api_key)

    def analizar(self, metricas: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        if self.disponible:
            try:
                return self._analizar_gemini(metricas, config)
            except Exception as exc:  # noqa: BLE001
                local = self._analizar_local(metricas, config)
                local["resumen"] = f"(API no disponible: {exc}) " + local["resumen"]
                local["fuente"] = "local-fallback"
                return local
        return self._analizar_local(metricas, config)

    def _analizar_gemini(self, metricas: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        instruccion = (
            "Eres un SRE senior analizando una simulación de red de centro de datos. "
            "Responde SOLO JSON con claves: resumen (string), hallazgos (array de strings), "
            "recomendaciones (array de strings), nivel_riesgo (bajo|medio|alto). "
            "Usa español. No inventes unidades: la latencia está en unidades de simulación "
            "(nunca digas ms salvo que el dato lo indique). Cada hallazgo/recomendación "
            "debe ser una frase completa y no vacía."
        )
        usuario = (
            "Analiza estos resultados de DataStream Networks.\n"
            f"CONFIG: {json.dumps(config, ensure_ascii=False)}\n"
            f"METRICAS: {json.dumps(metricas, ensure_ascii=False)}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": instruccion}]},
            "contents": [{"role": "user", "parts": [{"text": usuario}]}],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
            },
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.modelo}:generateContent?key={self.api_key}"
        )
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                cuerpo = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detalle = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detalle[:300]}") from exc

        texto = cuerpo["candidates"][0]["content"]["parts"][0]["text"]
        parseado = json.loads(texto)
        return {
            "fuente": "gemini",
            "resumen": str(parseado.get("resumen", parseado.get("summary", ""))),
            "hallazgos": list(parseado.get("hallazgos", parseado.get("findings", []))),
            "recomendaciones": list(
                parseado.get("recomendaciones", parseado.get("recommendations", []))
            ),
            "nivel_riesgo": str(
                parseado.get("nivel_riesgo", parseado.get("risk_level", "medio"))
            ),
            "modelo": self.modelo,
        }

    def _analizar_local(self, metricas: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        creados = int(metricas.get("paquetes_creados", 0))
        completados = int(metricas.get("paquetes_completados", 0))
        descartados = int(metricas.get("paquetes_descartados", 0))
        lat_prom = float(metricas.get("latencia_promedio", 0.0))
        refrigeracion = float(metricas.get("potencia_refrigeracion", 0.0))
        lam = float(metricas.get("lambda_lagrange", 0.0))
        fallidos = metricas.get("nodos_fallidos") or []
        ruta = metricas.get("ruta_activa") or []

        tasa_descarte = (descartados / creados) if creados else 0.0
        exito = (completados / creados) if creados else 0.0

        if tasa_descarte > 0.2 or len(fallidos) >= 2:
            riesgo = "alto"
        elif tasa_descarte > 0.08 or lat_prom > 5:
            riesgo = "medio"
        else:
            riesgo = "bajo"

        hallazgos = [
            f"Procesados {completados}/{creados} paquetes (éxito={exito:.1%}, descarte={tasa_descarte:.1%}).",
            f"Latencia media extremo a extremo ≈ {lat_prom:.3f} unidades de simulación.",
            f"Refrigeración por gradiente cerca de P={refrigeracion:.3f}; λ de Lagrange≈{lam:.4f}.",
            f"Ruta PD activa: {' → '.join(ruta) if ruta else 'n/a'}.",
        ]
        if fallidos:
            hallazgos.append(f"Nodos fallidos al cierre: {', '.join(map(str, fallidos))}.")

        recomendaciones = []
        if tasa_descarte > 0.1:
            recomendaciones.append(
                "Aumentar capacidades de servidor o reducir tasa_llegada; hay saturación."
            )
        if lat_prom > 4:
            recomendaciones.append(
                "La congestión infló latencias; revisar pesos de enlaces o capacidad en rutas calientes."
            )
        if refrigeracion > 0.75:
            recomendaciones.append(
                "Potencia de refrigeración alta; redistribuir energía Lagrange hacia clusters calientes."
            )
        if not recomendaciones:
            recomendaciones.append(
                "Sistema equilibrado con parámetros por defecto; estresar con mayor tasa_llegada en la defensa."
            )

        resumen = (
            f"Analista local: riesgo={riesgo}. La red SimPy completó {completados} tareas con "
            f"{tasa_descarte:.1%} de descarte. La programación dinámica mantuvo la ruta "
            f"{' → '.join(ruta) if ruta else 'estable'}, mientras gradiente y Lagrange "
            f"ajustaron refrigeración y energía (presupuesto={config.get('presupuesto_energia', '?')})."
        )
        return {
            "fuente": "local",
            "resumen": resumen,
            "hallazgos": hallazgos,
            "recomendaciones": recomendaciones,
            "nivel_riesgo": riesgo,
            "modelo": "heuristica-local",
        }
