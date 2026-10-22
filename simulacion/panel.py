from __future__ import annotations

from typing import Sequence
import math

import pygame

from simulacion.defaults import FPS_DEFECTO, TAMANO_VENTANA_DEFECTO
from simulacion.motor import SimuladorCentroDatos
from simulacion.modelos import EstadoNodo, EstadoSimulacion, TipoNodo

COLORES = {
    "fondo": (12, 18, 28),
    "panel": (20, 30, 44),
    "rejilla": (28, 42, 60),
    "texto": (220, 230, 240),
    "tenue": (140, 160, 180),
    "acento": (0, 200, 180),
    "aviso": (255, 170, 50),
    "peligro": (240, 80, 80),
    "ruta": (80, 220, 140),
    "enlace": (60, 85, 110),
    "paquete": (255, 220, 90),
    "puerta": (90, 180, 255),
    "router": (160, 190, 210),
    "servidor": (70, 210, 160),
    "caido": (180, 60, 60),
    "serie_a": (0, 200, 180),
    "serie_b": (255, 170, 50),
    "serie_c": (90, 180, 255),
}


class PanelControl:
    def __init__(
        self,
        simulador: SimuladorCentroDatos,
        tamano_ventana: tuple[int, int] = TAMANO_VENTANA_DEFECTO,
        fps: int = FPS_DEFECTO,
    ):
        self.sim = simulador
        self.ancho, self.alto = tamano_ventana
        self.fps = fps
        self._frames_flash_ruta = 0
        self._fuente = None
        self._fuente_sm = None
        self._fuente_lg = None

    def ejecutar(self) -> EstadoSimulacion:
        pygame.init()
        pygame.display.set_caption("DataStream Networks — Módulo 3")
        pantalla = pygame.display.set_mode((self.ancho, self.alto))
        reloj = pygame.time.Clock()
        self._fuente = pygame.font.SysFont("DejaVu Sans", 18)
        self._fuente_sm = pygame.font.SysFont("DejaVu Sans", 14)
        self._fuente_lg = pygame.font.SysFont("DejaVu Sans", 26, bold=True)

        presupuesto_pared = min(90.0, max(40.0, self.sim.config["duracion_sim"] / 2))
        velocidad_sim = self.sim.config["duracion_sim"] / presupuesto_pared

        en_marcha = True
        while en_marcha:
            dt = reloj.tick(self.fps) / 1000.0
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    en_marcha = False
                elif evento.type == pygame.KEYDOWN:
                    if evento.key in (pygame.K_ESCAPE, pygame.K_q):
                        en_marcha = False
                    elif evento.key == pygame.K_SPACE:
                        self.sim.estado.en_ejecucion = not self.sim.estado.en_ejecucion

            if self.sim.estado.en_ejecucion and not self.sim.estado.finalizada:
                objetivo = self.sim.env.now + velocidad_sim * dt
                self.sim.avanzar_hasta(objetivo)

            if self.sim.estado.metricas.ruta_cambio:
                self._frames_flash_ruta = int(self.fps * 1.2)

            pantalla.fill(COLORES["fondo"])
            self._dibujar_layout(pantalla, self.sim.estado)
            pygame.display.flip()

            if self.sim.estado.finalizada:
                pygame.time.delay(800)
                en_marcha = False

            if self._frames_flash_ruta > 0:
                self._frames_flash_ruta -= 1

        pygame.quit()
        return self.sim.estado

    def _dibujar_layout(self, pantalla: pygame.Surface, estado: EstadoSimulacion) -> None:
        area_mapa = pygame.Rect(20, 60, int(self.ancho * 0.58), self.alto - 80)
        area_lado = pygame.Rect(
            area_mapa.right + 16, 60, self.ancho - area_mapa.right - 36, self.alto - 80
        )

        titulo = self._fuente_lg.render(
            "DataStream Networks — Panel en vivo", True, COLORES["texto"]
        )
        pantalla.blit(titulo, (20, 16))
        ayuda = self._fuente_sm.render("SPACE pausa · ESC salir", True, COLORES["tenue"])
        pantalla.blit(ayuda, (self.ancho - 220, 24))

        self._panel(pantalla, area_mapa)
        self._dibujar_topologia(pantalla, area_mapa, estado)
        self._panel(pantalla, area_lado)
        self._dibujar_panel_lateral(pantalla, area_lado, estado)

    def _panel(self, pantalla: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(pantalla, COLORES["panel"], rect, border_radius=10)
        pygame.draw.rect(pantalla, COLORES["rejilla"], rect, width=1, border_radius=10)

    def _pos_nodo(self, x: float, y: float, area: pygame.Rect) -> tuple[int, int]:
        pad = 48
        px = area.left + pad + x * (area.width - 2 * pad)
        py = area.top + pad + y * (area.height - 2 * pad)
        return int(px), int(py)

    def _dibujar_topologia(
        self, pantalla: pygame.Surface, area: pygame.Rect, estado: EstadoSimulacion
    ) -> None:
        encabezado = self._fuente.render("Topología y tráfico", True, COLORES["acento"])
        pantalla.blit(encabezado, (area.left + 16, area.top + 12))

        activa = set(zip(estado.metricas.ruta_activa, estado.metricas.ruta_activa[1:]))
        vieja = set(zip(estado.metricas.ruta_anterior, estado.metricas.ruta_anterior[1:]))
        flash = self._frames_flash_ruta > 0

        posiciones = {
            nid: self._pos_nodo(n.x, n.y, area) for nid, n in estado.nodos.items()
        }
        for enlace in estado.enlaces:
            p1, p2 = posiciones[enlace.origen], posiciones[enlace.destino]
            clave = (enlace.origen, enlace.destino)
            if clave in activa:
                color, grosor = COLORES["ruta"], 4
            elif flash and clave in vieja:
                color, grosor = COLORES["aviso"], 3
            else:
                c = enlace.congestion
                color = (
                    int(COLORES["enlace"][0] + 120 * c),
                    int(COLORES["enlace"][1] - 40 * c),
                    int(COLORES["enlace"][2] - 40 * c),
                )
                grosor = 2
            pygame.draw.line(pantalla, color, p1, p2, grosor)

        self._dibujar_paquetes(pantalla, estado, posiciones)

        for nid, nodo in estado.nodos.items():
            pos = posiciones[nid]
            if nodo.estado == EstadoNodo.CAIDO:
                color = COLORES["caido"]
            elif nodo.tipo == TipoNodo.PUERTA:
                color = COLORES["puerta"]
            elif nodo.tipo == TipoNodo.SERVIDOR:
                color = COLORES["servidor"]
            else:
                color = COLORES["router"]

            radio = 18 if nodo.tipo != TipoNodo.SERVIDOR else 20
            pygame.draw.circle(pantalla, color, pos, radio)
            pygame.draw.circle(pantalla, COLORES["texto"], pos, radio, 1)

            if nodo.tipo == TipoNodo.SERVIDOR and nodo.capacidad > 0:
                self._dibujar_arco(pantalla, pos, radio + 5, nodo.utilizacion, COLORES["aviso"])

            etiqueta = self._fuente_sm.render(nid, True, COLORES["texto"])
            pantalla.blit(
                etiqueta, (pos[0] - etiqueta.get_width() // 2, pos[1] + radio + 4)
            )

        if flash:
            pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 80)
            aviso = self._fuente.render(
                "Ruta más corta actualizada (PD)",
                True,
                (255, int(180 + 50 * pulso), 40),
            )
            pantalla.blit(aviso, (area.left + 16, area.bottom - 36))
        elif estado.mensaje:
            msg = self._fuente_sm.render(estado.mensaje[:70], True, COLORES["tenue"])
            pantalla.blit(msg, (area.left + 16, area.bottom - 32))

    def _dibujar_paquetes(
        self,
        pantalla: pygame.Surface,
        estado: EstadoSimulacion,
        posiciones: dict[str, tuple[int, int]],
    ) -> None:
        for pid in list(estado.paquetes_activos)[:80]:
            paquete = estado.paquetes.get(pid)
            if not paquete or len(paquete.ruta) < 2:
                continue
            salto = min(paquete.salto_actual, len(paquete.ruta) - 2)
            a, b = paquete.ruta[salto], paquete.ruta[salto + 1]
            if a not in posiciones or b not in posiciones:
                continue
            p1, p2 = posiciones[a], posiciones[b]
            fase = ((pygame.time.get_ticks() / 400.0) + int(pid, 16) % 17) % 1.0
            x = int(p1[0] + (p2[0] - p1[0]) * fase)
            y = int(p1[1] + (p2[1] - p1[1]) * fase)
            pygame.draw.circle(pantalla, COLORES["paquete"], (x, y), 4)

    def _dibujar_arco(
        self,
        pantalla: pygame.Surface,
        centro: tuple[int, int],
        radio: int,
        ratio: float,
        color: tuple[int, int, int],
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        if ratio <= 0:
            return
        rect = pygame.Rect(centro[0] - radio, centro[1] - radio, radio * 2, radio * 2)
        inicio = -math.pi / 2
        fin = inicio + 2 * math.pi * ratio
        pygame.draw.arc(pantalla, color, rect, inicio, fin, 3)

    def _dibujar_panel_lateral(
        self, pantalla: pygame.Surface, area: pygame.Rect, estado: EstadoSimulacion
    ) -> None:
        m = estado.metricas
        y = area.top + 14
        x = area.left + 16

        def linea(texto: str, color=COLORES["texto"], fuente=None) -> None:
            nonlocal y
            surf = (fuente or self._fuente_sm).render(texto, True, color)
            pantalla.blit(surf, (x, y))
            y += surf.get_height() + 4

        linea("Métricas de simulación", COLORES["acento"], self._fuente)
        y += 4
        linea(f"t = {m.tiempo_sim:6.2f} / {self.sim.config['duracion_sim']:.0f}")
        linea(f"Creados    : {m.paquetes_creados}")
        linea(f"Completados: {m.paquetes_completados}")
        linea(
            f"Descartados: {m.paquetes_descartados}",
            COLORES["peligro"] if m.paquetes_descartados else COLORES["texto"],
        )
        linea(f"En vuelo   : {m.paquetes_en_vuelo}")
        linea(f"Latencia media: {m.latencia_promedio:.3f}")
        ruta_txt = " → ".join(m.ruta_activa) if m.ruta_activa else "—"
        linea(f"Ruta PD: {ruta_txt}", COLORES["ruta"])
        if m.nodos_fallidos:
            linea(f"Caídos: {', '.join(m.nodos_fallidos)}", COLORES["peligro"])
        linea(f"Refrigeración P: {m.potencia_refrigeracion:.3f}")
        linea(f"Lagrange λ: {m.lambda_lagrange:.4f}")

        y += 10
        graf1 = pygame.Rect(area.left + 12, y, area.width - 24, 140)
        self._dibujar_serie(
            pantalla,
            graf1,
            "Potencia de refrigeración (gradiente)",
            [(t, p) for t, p in m.historial_refrigeracion],
            COLORES["serie_a"],
            y_max=1.0,
        )
        y = graf1.bottom + 18

        graf2 = pygame.Rect(area.left + 12, y, area.width - 24, 170)
        self._dibujar_energia(pantalla, graf2, m.historial_energia, m.asignacion_energia)

    def _dibujar_serie(
        self,
        pantalla: pygame.Surface,
        rect: pygame.Rect,
        titulo: str,
        serie: Sequence[tuple[float, float]],
        color: tuple[int, int, int],
        y_max: float,
    ) -> None:
        pygame.draw.rect(pantalla, COLORES["fondo"], rect, border_radius=6)
        pygame.draw.rect(pantalla, COLORES["rejilla"], rect, 1, border_radius=6)
        etiqueta = self._fuente_sm.render(titulo, True, COLORES["tenue"])
        pantalla.blit(etiqueta, (rect.left + 8, rect.top + 6))

        if len(serie) < 2:
            vacio = self._fuente_sm.render("esperando muestras…", True, COLORES["tenue"])
            pantalla.blit(vacio, (rect.left + 8, rect.centery))
            return

        tiempos = [t for t, _ in serie]
        t0, t1 = tiempos[0], tiempos[-1]
        span = max(1e-6, t1 - t0)
        puntos = []
        plot = rect.inflate(-16, -28)
        plot.top += 12
        for t, v in serie:
            px = plot.left + (t - t0) / span * plot.width
            py = plot.bottom - (max(0.0, min(y_max, v)) / y_max) * plot.height
            puntos.append((px, py))
        if len(puntos) >= 2:
            pygame.draw.lines(pantalla, color, False, puntos, 2)

    def _dibujar_energia(
        self,
        pantalla: pygame.Surface,
        rect: pygame.Rect,
        historial: list[tuple[float, list[float]]],
        actual: list[float],
    ) -> None:
        pygame.draw.rect(pantalla, COLORES["fondo"], rect, border_radius=6)
        pygame.draw.rect(pantalla, COLORES["rejilla"], rect, 1, border_radius=6)
        etiqueta = self._fuente_sm.render(
            "Asignación energética Lagrange (clusters)", True, COLORES["tenue"]
        )
        pantalla.blit(etiqueta, (rect.left + 8, rect.top + 6))

        colores = [COLORES["serie_a"], COLORES["serie_b"], COLORES["serie_c"]]
        if historial:
            n_series = len(historial[-1][1])
            tiempos = [t for t, _ in historial]
            t0, t1 = tiempos[0], tiempos[-1]
            span = max(1e-6, t1 - t0)
            plot = rect.inflate(-16, -50)
            plot.top += 14
            presupuesto = self.sim.config["presupuesto_energia"]
            for i in range(n_series):
                pts = []
                for t, alloc in historial:
                    if i >= len(alloc):
                        continue
                    px = plot.left + (t - t0) / span * plot.width
                    py = plot.bottom - (alloc[i] / max(presupuesto, 1e-6)) * plot.height
                    pts.append((px, py))
                if len(pts) >= 2:
                    pygame.draw.lines(pantalla, colores[i % len(colores)], False, pts, 2)

        if actual:
            area_barra = pygame.Rect(rect.left + 12, rect.bottom - 36, rect.width - 24, 22)
            total = sum(actual) or 1.0
            bx = area_barra.left
            for i, val in enumerate(actual):
                w = int(area_barra.width * (val / total))
                pygame.draw.rect(
                    pantalla,
                    colores[i % len(colores)],
                    pygame.Rect(bx, area_barra.top, max(2, w), area_barra.height),
                    border_radius=3,
                )
                bx += w
            leyenda = self._fuente_sm.render(
                "  ".join(f"C{i}:{v:.1f}" for i, v in enumerate(actual)),
                True,
                COLORES["texto"],
            )
            pantalla.blit(leyenda, (rect.left + 12, rect.bottom - 52))


def ejecutar_panel(simulador: SimuladorCentroDatos, **kwargs) -> EstadoSimulacion:
    return PanelControl(simulador, **kwargs).ejecutar()
