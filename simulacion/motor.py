from __future__ import annotations

from typing import Any, Callable
import random

import simpy

from simulacion.defaults import PERFILES_PAQUETE_DEFECTO, TOPOLOGIA_DEFECTO
from simulacion.puente_matematico import (
    AsignadorEnergiaLagrange,
    AsignadorMochila,
    ControladorGradienteRefrigeracion,
    EnrutadorProgramacionDinamica,
    ModeloTemperatura,
)
from simulacion.modelos import (
    Enlace,
    EstadoNodo,
    EstadoSimulacion,
    NodoRed,
    Paquete,
    TipoNodo,
)
from simulacion.validadores import validar_config_simulacion, validar_topologia


class SimuladorCentroDatos:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        topologia: dict[str, Any] | None = None,
    ):
        cfg = validar_config_simulacion(config or {})
        topo = validar_topologia(topologia or TOPOLOGIA_DEFECTO)

        self.config = cfg
        self.rng = random.Random(cfg["semilla"])
        self.env = simpy.Environment()

        nodos = {
            n["id"]: NodoRed(
                id_nodo=n["id"],
                tipo=TipoNodo(n["tipo"]),
                x=n["x"],
                y=n["y"],
                capacidad=n["capacidad"],
                cluster=n.get("cluster", 0),
            )
            for n in topo["nodos"]
        }
        enlaces = [Enlace(o, d, lat) for o, d, lat in topo["enlaces"]]
        self.estado = EstadoSimulacion(nodos=nodos, enlaces=enlaces)

        self.enrutador = EnrutadorProgramacionDinamica(list(nodos.keys()))
        self.modelo_temp = ModeloTemperatura()
        self.refrigeracion = ControladorGradienteRefrigeracion()
        self.energia = AsignadorEnergiaLagrange(
            presupuesto=cfg["presupuesto_energia"],
            n_clusters=max(
                1,
                len({n.cluster for n in nodos.values() if n.tipo == TipoNodo.SERVIDOR}),
            ),
        )
        self.almacenes_servidor: dict[str, simpy.Store] = {}
        self._suma_latencia = 0.0
        self._completados = 0
        self._al_tick: Callable[[EstadoSimulacion], None] | None = None

        for servidor in self.estado.servidores():
            self.almacenes_servidor[servidor.id_nodo] = simpy.Store(self.env)

    def definir_callback_tick(self, callback: Callable[[EstadoSimulacion], None]) -> None:
        self._al_tick = callback

    def construir(self) -> None:
        self.env.process(self._proceso_llegadas())
        self.env.process(self._proceso_fallas())
        self.env.process(self._bucle_optimizacion())
        self.env.process(self._bucle_metricas())
        for servidor in self.estado.servidores():
            self.env.process(self._trabajador_servidor(servidor.id_nodo))

    def _asegurar_construido(self) -> None:
        if not getattr(self, "_construido", False):
            self.construir()
            self._construido = True

    def ejecutar(self, hasta: float | None = None) -> EstadoSimulacion:
        self._asegurar_construido()
        horizonte = hasta if hasta is not None else self.config["duracion_sim"]
        if self.env.now < horizonte:
            self.env.run(until=horizonte)
        self.estado.finalizada = True
        self.estado.en_ejecucion = False
        self.estado.mensaje = "Simulación finalizada"
        self._actualizar_metricas(forzar_ruta=True)
        return self.estado

    def avanzar_hasta(self, tiempo_objetivo: float) -> EstadoSimulacion:
        if self.estado.finalizada:
            return self.estado
        self._asegurar_construido()
        objetivo = min(tiempo_objetivo, self.config["duracion_sim"])
        if self.env.now < objetivo:
            self.env.run(until=objetivo)
        if self.env.now >= self.config["duracion_sim"]:
            self.estado.finalizada = True
            self.estado.en_ejecucion = False
            self.estado.mensaje = "Simulación finalizada"
        self._actualizar_metricas()
        return self.estado

    def _proceso_llegadas(self):
        tasa = self.config["tasa_llegada"]
        perfiles = PERFILES_PAQUETE_DEFECTO
        while True:
            espera = self.rng.expovariate(tasa)
            yield self.env.timeout(espera)
            perfil = self.rng.choice(perfiles)
            paquete = Paquete.crear(
                nombre=perfil["nombre"],
                tamano=float(perfil["tamano"]),
                prioridad=int(perfil["prioridad"]),
                media_proc=float(perfil["media_proc"]),
                creado_en=self.env.now,
            )
            self.estado.paquetes[paquete.id_paquete] = paquete
            self.estado.metricas.paquetes_creados += 1
            self.env.process(self._enrutar_paquete(paquete))

    def _enrutar_paquete(self, paquete: Paquete):
        ruta, costo = self._calcular_mejor_ruta()
        if not ruta or costo == float("inf"):
            paquete.estado = "descartado"
            self.estado.metricas.paquetes_descartados += 1
            return

        paquete.ruta = ruta
        paquete.servidor_asignado = ruta[-1]
        paquete.estado = "en_transito"
        self.estado.paquetes_activos.append(paquete.id_paquete)

        mapa = self.estado.mapa_enlaces()
        for salto in range(len(ruta) - 1):
            origen, destino = ruta[salto], ruta[salto + 1]
            if (
                self.estado.nodos[origen].estado == EstadoNodo.CAIDO
                or self.estado.nodos[destino].estado == EstadoNodo.CAIDO
            ):
                paquete.estado = "descartado"
                self.estado.metricas.paquetes_descartados += 1
                self._liberar_activo(paquete.id_paquete)
                return

            enlace = mapa.get((origen, destino))
            demora = (enlace.latencia if enlace else 10.0) / 100.0
            if enlace:
                enlace.congestion = min(1.0, enlace.congestion + 0.05)
            yield self.env.timeout(max(0.05, demora))
            paquete.salto_actual = salto + 1
            if enlace:
                enlace.congestion = max(0.0, enlace.congestion - 0.03)

        id_servidor = paquete.servidor_asignado
        servidor = self.estado.nodos[id_servidor]
        if servidor.estado == EstadoNodo.CAIDO or not servidor.puede_aceptar(paquete.tamano):
            alterno = self._asignar_por_mochila(paquete)
            if alterno is None:
                paquete.estado = "descartado"
                servidor.descartados += 1
                self.estado.metricas.paquetes_descartados += 1
                self._liberar_activo(paquete.id_paquete)
                return
            id_servidor = alterno
            paquete.servidor_asignado = alterno
            servidor = self.estado.nodos[id_servidor]

        servidor.carga += paquete.tamano
        servidor.longitud_cola += 1
        paquete.estado = "en_cola"
        yield self.almacenes_servidor[id_servidor].put(paquete)

    def _trabajador_servidor(self, id_servidor: str):
        almacen = self.almacenes_servidor[id_servidor]
        servidor = self.estado.nodos[id_servidor]
        while True:
            paquete = yield almacen.get()
            if servidor.estado == EstadoNodo.CAIDO:
                paquete.estado = "descartado"
                servidor.descartados += 1
                self.estado.metricas.paquetes_descartados += 1
                servidor.carga = max(0.0, servidor.carga - paquete.tamano)
                servidor.longitud_cola = max(0, servidor.longitud_cola - 1)
                self._liberar_activo(paquete.id_paquete)
                continue

            paquete.estado = "procesando"
            factor_energia = self._factor_energia(servidor.cluster)
            media = max(0.05, paquete.media_proc / max(0.25, factor_energia))
            servicio = self.rng.expovariate(1.0 / media)
            yield self.env.timeout(servicio)

            paquete.estado = "completado"
            paquete.completado_en = self.env.now
            latencia = paquete.completado_en - paquete.creado_en
            self.estado.muestras_latencia.append(latencia)
            self._suma_latencia += latencia
            self._completados += 1
            servidor.procesados += 1
            servidor.carga = max(0.0, servidor.carga - paquete.tamano)
            servidor.longitud_cola = max(0, servidor.longitud_cola - 1)
            self.estado.metricas.paquetes_completados += 1
            self._liberar_activo(paquete.id_paquete)

    def _proceso_fallas(self):
        tasa_falla = self.config["tasa_falla"]
        tasa_recup = self.config["tasa_recuperacion"]
        candidatos = [n for n in self.estado.nodos.values() if n.tipo != TipoNodo.PUERTA]
        while True:
            yield self.env.timeout(
                self.rng.expovariate(max(tasa_falla, 1e-6) * max(1, len(candidatos)))
            )
            activos = [n for n in candidatos if n.estado == EstadoNodo.ACTIVO]
            if not activos:
                continue
            victima = self.rng.choice(activos)
            victima.estado = EstadoNodo.CAIDO
            self.estado.mensaje = f"Nodo {victima.id_nodo} FALLÓ"
            self.env.process(self._recuperar_nodo(victima, tasa_recup))

    def _recuperar_nodo(self, nodo: NodoRed, tasa_recup: float):
        demora = self.rng.expovariate(max(tasa_recup, 1e-6))
        yield self.env.timeout(demora)
        nodo.estado = EstadoNodo.ACTIVO
        self.estado.mensaje = f"Nodo {nodo.id_nodo} RECUPERADO"

    def _bucle_optimizacion(self):
        intervalo = self.config["intervalo_opt"]
        while True:
            yield self.env.timeout(intervalo)
            self._actualizar_temperatura_y_refrigeracion()
            self._actualizar_asignacion_energia()
            for enlace in self.estado.enlaces:
                enlace.congestion = max(0.0, enlace.congestion * 0.9)

    def _bucle_metricas(self):
        while True:
            yield self.env.timeout(0.25)
            self._actualizar_metricas()
            if self._al_tick:
                self._al_tick(self.estado)

    def _liberar_activo(self, id_paquete: str) -> None:
        try:
            self.estado.paquetes_activos.remove(id_paquete)
        except ValueError:
            pass

    def _no_disponibles(self) -> set[str]:
        return {
            n.id_nodo for n in self.estado.nodos.values() if n.estado == EstadoNodo.CAIDO
        }

    def _enlaces_ponderados(self) -> list[tuple[str, str, float]]:
        return [(e.origen, e.destino, e.latencia) for e in self.estado.enlaces]

    def _calcular_mejor_ruta(self) -> tuple[list[str], float]:
        puerta = self.estado.id_puerta()
        destinos = [
            s.id_nodo for s in self.estado.servidores() if s.estado == EstadoNodo.ACTIVO
        ]
        return self.enrutador.ruta_mas_corta(
            origen=puerta,
            destinos=destinos,
            enlaces_ponderados=self._enlaces_ponderados(),
            no_disponibles=self._no_disponibles(),
        )

    def _asignar_por_mochila(self, paquete: Paquete) -> str | None:
        candidatos: list[tuple[str, float, float]] = []
        for servidor in self.estado.servidores():
            libre = servidor.capacidad - servidor.carga
            if servidor.estado == EstadoNodo.ACTIVO and libre >= paquete.tamano:
                candidatos.append(
                    (servidor.id_nodo, paquete.tamano, float(paquete.prioridad) + libre * 0.01)
                )
        if not candidatos:
            return None
        seleccion = AsignadorMochila.seleccionar(
            [(sid, 1.0, val) for sid, _, val in candidatos],
            capacidad=1.0,
        )
        return seleccion[0] if seleccion else candidatos[0][0]

    def _actualizar_temperatura_y_refrigeracion(self) -> None:
        temps = []
        for servidor in self.estado.servidores():
            servidor.temperatura = self.modelo_temp.temperatura(servidor.utilizacion)
            temps.append(servidor.temperatura)
        ambiente = sum(temps) / len(temps) if temps else 35.0
        potencia = self.refrigeracion.paso(ambiente)
        for servidor in self.estado.servidores():
            servidor.temperatura = max(25.0, servidor.temperatura - 20.0 * potencia * 0.15)
        m = self.estado.metricas
        m.potencia_refrigeracion = potencia
        m.historial_refrigeracion.append((self.env.now, potencia))
        if len(m.historial_refrigeracion) > 200:
            m.historial_refrigeracion = m.historial_refrigeracion[-200:]

    def _actualizar_asignacion_energia(self) -> None:
        servidores = self.estado.servidores()
        n = self.energia.n_clusters
        demandas = [0.1] * n
        for servidor in servidores:
            idx = min(servidor.cluster, n - 1)
            demandas[idx] += 0.5 + servidor.utilizacion + 0.1 * servidor.longitud_cola
        alloc, lam = self.energia.asignar(demandas)
        m = self.estado.metricas
        m.asignacion_energia = alloc.tolist()
        m.lambda_lagrange = lam
        m.historial_energia.append((self.env.now, alloc.tolist()))
        if len(m.historial_energia) > 200:
            m.historial_energia = m.historial_energia[-200:]

    def _factor_energia(self, cluster: int) -> float:
        alloc = self.estado.metricas.asignacion_energia
        if not alloc:
            return 1.0
        idx = min(cluster, len(alloc) - 1)
        media = sum(alloc) / len(alloc)
        return max(0.25, alloc[idx] / max(media, 1e-6))

    def _actualizar_metricas(self, forzar_ruta: bool = False) -> None:
        ruta, _ = self._calcular_mejor_ruta()
        m = self.estado.metricas
        anterior = list(m.ruta_activa)
        m.ruta_anterior = anterior
        m.ruta_activa = ruta
        m.ruta_cambio = bool(anterior and ruta and anterior != ruta)
        if forzar_ruta and not anterior:
            m.ruta_cambio = False
        m.tiempo_sim = self.env.now
        m.paquetes_en_vuelo = len(self.estado.paquetes_activos)
        m.latencia_promedio = (
            self._suma_latencia / self._completados if self._completados else 0.0
        )
        m.cargas_nodo = {nid: n.utilizacion for nid, n in self.estado.nodos.items()}
        m.nodos_fallidos = [
            nid for nid, n in self.estado.nodos.items() if n.estado == EstadoNodo.CAIDO
        ]
        if m.ruta_cambio:
            self.estado.mensaje = f"Ruta más corta actualizada: {' → '.join(ruta)}"
