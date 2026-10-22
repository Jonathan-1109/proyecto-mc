from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import html
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class GeneradorInformePDF:
    def __init__(self, dir_salida: str | Path = "reports"):
        self.dir_salida = Path(dir_salida)
        self.dir_salida.mkdir(parents=True, exist_ok=True)

    def generar(
        self,
        metricas: dict[str, Any],
        config: dict[str, Any],
        analisis: dict[str, Any],
        nombre_archivo: str | None = None,
    ) -> Path:
        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
        salida = self.dir_salida / (nombre_archivo or f"informe_datastream_{sello}.pdf")

        estilos = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle(
            "TituloES",
            parent=estilos["Title"],
            fontSize=18,
            leading=22,
            spaceAfter=8,
            textColor=colors.HexColor("#0B3A4A"),
        )
        estilo_sub = ParagraphStyle(
            "SubtituloES",
            parent=estilos["Heading2"],
            fontSize=13,
            leading=16,
            spaceAfter=6,
            textColor=colors.HexColor("#134E4A"),
        )
        estilo_h = ParagraphStyle(
            "EncabezadoES",
            parent=estilos["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#0E7490"),
        )
        estilo_h3 = ParagraphStyle(
            "SubencabezadoES",
            parent=estilos["Heading3"],
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=4,
            textColor=colors.HexColor("#155E75"),
        )
        cuerpo = ParagraphStyle(
            "CuerpoES",
            parent=estilos["BodyText"],
            fontSize=10,
            leading=14,
            spaceAfter=4,
        )
        celda = ParagraphStyle(
            "CeldaES",
            parent=estilos["BodyText"],
            fontSize=9,
            leading=12,
        )
        celda_header = ParagraphStyle(
            "CeldaHeaderES",
            parent=celda,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        )
        vineta = ParagraphStyle(
            "VinetaES",
            parent=cuerpo,
            leftIndent=14,
            bulletIndent=0,
            spaceBefore=2,
            spaceAfter=2,
        )

        doc = SimpleDocTemplate(
            str(salida),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title="DataStream Networks — Informe de simulación",
        )

        historia: list[Any] = []
        historia.append(Paragraph("DataStream Networks", estilo_titulo))
        historia.append(
            Paragraph("Módulo 3 — Informe de simulación SimPy / Pygame", estilo_sub)
        )
        historia.append(
            Paragraph(
                f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                cuerpo,
            )
        )

        historia.append(Paragraph("1. Configuración", estilo_h))
        filas_cfg = [
            [
                Paragraph("<b>Parámetro</b>", celda_header),
                Paragraph("<b>Valor</b>", celda_header),
            ],
            [self._p("duracion_sim", celda), self._p(config.get("duracion_sim"), celda)],
            [self._p("tasa_llegada", celda), self._p(config.get("tasa_llegada"), celda)],
            [self._p("semilla", celda), self._p(config.get("semilla"), celda)],
            [self._p("tasa_falla", celda), self._p(config.get("tasa_falla"), celda)],
            [
                self._p("tasa_recuperacion", celda),
                self._p(config.get("tasa_recuperacion"), celda),
            ],
            [
                self._p("presupuesto_energia", celda),
                self._p(config.get("presupuesto_energia"), celda),
            ],
        ]
        historia.append(self._tabla(filas_cfg))
        historia.append(Spacer(1, 0.25 * cm))

        historia.append(Paragraph("2. Métricas clave", estilo_h))
        ruta = " → ".join(metricas.get("ruta_activa") or []) or "—"
        energia = ", ".join(f"{v:.2f}" for v in (metricas.get("asignacion_energia") or [])) or "—"
        filas_met = [
            [
                Paragraph("<b>Métrica</b>", celda_header),
                Paragraph("<b>Valor</b>", celda_header),
            ],
            [self._p("Paquetes creados", celda), self._p(metricas.get("paquetes_creados"), celda)],
            [
                self._p("Paquetes completados", celda),
                self._p(metricas.get("paquetes_completados"), celda),
            ],
            [
                self._p("Paquetes descartados", celda),
                self._p(metricas.get("paquetes_descartados"), celda),
            ],
            [
                self._p("Latencia promedio (u. simulación)", celda),
                self._p(f"{float(metricas.get('latencia_promedio', 0)):.4f}", celda),
            ],
            [
                self._p("Potencia refrigeración", celda),
                self._p(f"{float(metricas.get('potencia_refrigeracion', 0)):.4f}", celda),
            ],
            [
                self._p("λ de Lagrange", celda),
                self._p(f"{float(metricas.get('lambda_lagrange', 0)):.6f}", celda),
            ],
            [self._p("Ruta PD activa", celda), self._p(ruta, celda)],
            [self._p("Asignación energética", celda), self._p(energia, celda)],
            [
                self._p("Nodos fallidos al cierre", celda),
                self._p(", ".join(metricas.get("nodos_fallidos") or []) or "ninguno", celda),
            ],
        ]
        historia.append(self._tabla(filas_met))
        historia.append(Spacer(1, 0.25 * cm))

        historia.append(Paragraph("3. Análisis de IA", estilo_h))
        historia.append(
            Paragraph(
                f"<b>Fuente:</b> {html.escape(str(analisis.get('fuente', 'n/a')))} "
                f"({html.escape(str(analisis.get('modelo', 'n/a')))}) &nbsp;&nbsp; "
                f"<b>Riesgo:</b> {html.escape(str(analisis.get('nivel_riesgo', 'n/a')))}",
                cuerpo,
            )
        )
        historia.append(Spacer(1, 0.15 * cm))
        resumen = self._limpiar_texto(str(analisis.get("resumen", "")))
        if resumen:
            historia.append(Paragraph(html.escape(resumen), cuerpo))

        hallazgos = self._lista_limpia(analisis.get("hallazgos"))
        if hallazgos:
            historia.append(Paragraph("Hallazgos", estilo_h3))
            for item in hallazgos:
                historia.append(Paragraph(f"• {html.escape(item)}", vineta))

        recs = self._lista_limpia(analisis.get("recomendaciones"))
        if recs:
            historia.append(Paragraph("Recomendaciones", estilo_h3))
            for item in recs:
                historia.append(Paragraph(f"• {html.escape(item)}", vineta))

        historia.append(Paragraph("4. Notas conceptuales", estilo_h))
        historia.append(
            Paragraph(
                "Esta corrida acopla llegadas por colas (SimPy), rutas más cortas por "
                "programación dinámica bajo congestión, admisión tipo mochila en servidores, "
                "descenso por gradiente para el costo no lineal de refrigeración y "
                "multiplicadores de Lagrange para la asignación energética con restricción. "
                "Pygame renderizó el tráfico y las gráficas de optimización.",
                cuerpo,
            )
        )

        doc.build(historia)
        return salida

    @staticmethod
    def _p(valor: Any, estilo: ParagraphStyle) -> Paragraph:
        return Paragraph(html.escape(str(valor)), estilo)

    @staticmethod
    def _limpiar_texto(texto: str) -> str:
        texto = texto.strip()
        texto = re.sub(r"\b(\d+(?:\.\d+)?)\s*ms\b", r"\1 unidades de simulación", texto)
        return texto

    @classmethod
    def _lista_limpia(cls, items: Any) -> list[str]:
        if not items:
            return []
        limpios: list[str] = []
        for item in items:
            t = cls._limpiar_texto(str(item))
            if t:
                limpios.append(t)
        return limpios

    @staticmethod
    def _tabla(filas: list[list[Any]]) -> Table:
        tabla = Table(filas, colWidths=[7 * cm, 9 * cm], hAlign="LEFT")
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0E7490")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                        colors.HexColor("#F8FAFC"),
                        colors.HexColor("#EEF2FF"),
                    ]),
                ]
            )
        )
        return tabla
