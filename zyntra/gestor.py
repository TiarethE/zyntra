"""Capa de aplicación: punto de entrada para registrar y mover envíos.

Une los patrones: pide el envío al creador de su tipo (Factory Method),
cambia su estado (State) y publica el evento en el bus (Observer).

Es seguro usarlo desde varios hilos: los cambios sobre una misma guía se
hacen uno a la vez (un candado por envío) y los de guías distintas en paralelo.
"""

from __future__ import annotations

import threading
from typing import Optional

from zyntra.creadores import EnvioCreator
from zyntra.dominio import RegistroRastreo
from zyntra.envios import Envio
from zyntra.estados import NombreEstado
from zyntra.eventos import BusEventos, CambioEstado
from zyntra.tarifas import TipoEnvio


class EnvioNoEncontrado(KeyError):
    pass


class GestorEnvios:
    def __init__(self, creadores: dict[TipoEnvio, EnvioCreator],
                 bus: Optional[BusEventos] = None) -> None:
        self._creadores = creadores
        self._bus = bus
        self._envios: dict[str, Envio] = {}
        self._candados: dict[str, threading.Lock] = {}
        self._candado_registro = threading.Lock()

    def registrar_envio(self, tipo: TipoEnvio, **datos) -> Envio:
        envio = self._creadores[tipo].crear_envio(**datos)
        with self._candado_registro:
            if envio.numero_guia in self._envios:
                raise ValueError(f"Ya existe un envío con la guía {envio.numero_guia}")
            self._envios[envio.numero_guia] = envio
            self._candados[envio.numero_guia] = threading.Lock()
        return envio

    def obtener(self, numero_guia: str) -> Envio:
        try:
            return self._envios[numero_guia]
        except KeyError:
            raise EnvioNoEncontrado(numero_guia) from None

    def cambiar_estado(self, numero_guia: str, destino: NombreEstado, **detalles) -> RegistroRastreo:
        """El rastreo se guarda en el momento (síncrono); las notificaciones
        se entregan después por el bus. Si la cola se llena, se pierde un
        aviso pero nunca un registro de rastreo."""
        envio = self.obtener(numero_guia)
        # Leer el estado, cambiarlo y publicar es una sola operación por envío:
        # así dos escaneos simultáneos no parten del mismo estado.
        with self._candados[numero_guia]:
            anterior = envio.estado
            registro = envio.cambiar_estado(destino, **detalles)
            if self._bus is not None:
                self._bus.publicar(CambioEstado(
                    numero_guia=numero_guia, anterior=anterior, nuevo=envio.estado,
                    descripcion=registro.descripcion, destinatario=envio.cliente.email,
                    marca_tiempo=registro.marca_tiempo))
        return registro

    def rastrear(self, numero_guia: str) -> tuple[RegistroRastreo, ...]:
        return self.obtener(numero_guia).rastreo
