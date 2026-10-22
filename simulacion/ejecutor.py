from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from simulacion.cliente_ia import ClienteInformeIA
from simulacion.defaults import TOPOLOGIA_DEFECTO, como_diccionario
from simulacion.informe_pdf import GeneradorInformePDF
from simulacion.motor import SimuladorCentroDatos
from simulacion.validadores import validar_config_simulacion, validar_topologia


class EjecutorSimulacion:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        topologia: dict[str, Any] | None = None,
    ):
        self.config = validar_config_simulacion(config or {})
        self.topologia = validar_topologia(topologia or TOPOLOGIA_DEFECTO)
        self.simulador = SimuladorCentroDatos(self.config, self.topologia)
        self.ia = ClienteInformeIA()
        self.pdf = GeneradorInformePDF(self.config["dir_reportes"])

    def ejecutar(self) -> dict[str, Any]:
        if self.config["sin_ventana"]:
            estado = self.simulador.ejecutar()
        else:
            from simulacion.panel import ejecutar_panel

            estado = ejecutar_panel(self.simulador, fps=self.config["fps"])
            if not estado.finalizada:
                self.simulador.estado.en_ejecucion = True
                estado = self.simulador.ejecutar()

        metricas = estado.metricas.a_diccionario()
        metricas["historial_refrigeracion"] = list(estado.metricas.historial_refrigeracion)
        metricas["historial_energia"] = list(estado.metricas.historial_energia)

        analisis = {
            "fuente": "desactivada",
            "resumen": "IA desactivada",
            "hallazgos": [],
            "recomendaciones": [],
            "nivel_riesgo": "n/a",
        }
        if self.config["ia_activa"]:
            analisis = self.ia.analizar(metricas, self.config)

        ruta_pdf = self.pdf.generar(metricas, self.config, analisis)
        sidecar = Path(ruta_pdf).with_suffix(".json")
        sidecar.write_text(
            json.dumps(
                {
                    "config": self.config,
                    "metricas": {
                        k: v
                        for k, v in metricas.items()
                        if k not in {"historial_refrigeracion", "historial_energia"}
                    },
                    "analisis": analisis,
                    "pdf": str(ruta_pdf),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            "estado": estado,
            "metricas": metricas,
            "analisis": analisis,
            "pdf": str(ruta_pdf),
            "json": str(sidecar),
        }


def cargar_topologia(ruta: str | Path) -> dict[str, Any]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return validar_topologia(datos)


def banner_defaults() -> str:
    cfg = como_diccionario()
    return (
        f"defaults: duracion={cfg['duracion_sim']}, tasa_llegada={cfg['tasa_llegada']}, "
        f"semilla={cfg['semilla']}, presupuesto_energia={cfg['presupuesto_energia']}"
    )
