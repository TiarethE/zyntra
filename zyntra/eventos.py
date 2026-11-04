"""Observer (comportamiento): bus de eventos para el rastreo en tiempo real.

Cada cambio de estado se publica como un evento. Los suscriptores
(notificaciones, panel de rastreo) se enteran sin que el envío los conozca
(DT-7). Es tiempo real blando: publicar nunca bloquea, cada suscriptor tiene
un tiempo límite y un fallo no afecta a los demás.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from zyntra.estados import NombreEstado

log = logging.getLogger(__name__)

CAPACIDAD_COLA = 1000      # eventos en espera antes de empezar a descartar
TIEMPO_LIMITE_S = 2.0      # segundos que se espera a cada suscriptor


@dataclass(frozen=True)
class CambioEstado:
    numero_guia: str
    anterior: NombreEstado
    nuevo: NombreEstado
    descripcion: str
    destinatario: str          # correo del cliente
    marca_tiempo: datetime


class Suscriptor(ABC):
    nombre: str = "suscriptor"

    @abstractmethod
    async def notificar(self, evento: CambioEstado) -> None:
        ...


class BusEventos:
    """Sujeto del patrón Observer. Se crea fuera y se inyecta (no es global)."""

    def __init__(self, capacidad: int = CAPACIDAD_COLA,
                 tiempo_limite: float = TIEMPO_LIMITE_S) -> None:
        self._suscriptores: list[Suscriptor] = []
        self._cola: asyncio.Queue[CambioEstado] = asyncio.Queue(maxsize=capacidad)
        self._tiempo_limite = tiempo_limite
        self._tarea: Optional[asyncio.Task] = None
        self.entregados = 0
        self.fallidos = 0
        self.descartados = 0

    def suscribir(self, suscriptor: Suscriptor) -> None:
        self._suscriptores.append(suscriptor)

    def publicar(self, evento: CambioEstado) -> bool:
        """Encola el evento sin esperar. Si la cola está llena, lo descarta."""
        try:
            self._cola.put_nowait(evento)
            return True
        except asyncio.QueueFull:
            self.descartados += 1
            log.warning("Cola llena: se descartó el evento de %s", evento.numero_guia)
            return False

    async def iniciar(self) -> None:
        if self._tarea is None:
            self._tarea = asyncio.create_task(self._trabajar())

    async def detener(self) -> None:
        """Espera a que se entreguen los eventos pendientes y se detiene."""
        if self._tarea is None:
            return
        await self._cola.join()
        self._tarea.cancel()
        try:
            await self._tarea
        except asyncio.CancelledError:
            pass
        self._tarea = None

    @property
    def estadisticas(self) -> dict[str, int]:
        return {"entregados": self.entregados, "fallidos": self.fallidos,
                "descartados": self.descartados, "pendientes": self._cola.qsize()}

    async def _trabajar(self) -> None:
        while True:
            evento = await self._cola.get()
            try:
                # Todos los suscriptores a la vez: uno lento no retrasa a los demás.
                await asyncio.gather(*(self._entregar(s, evento) for s in self._suscriptores))
            finally:
                self._cola.task_done()

    async def _entregar(self, suscriptor: Suscriptor, evento: CambioEstado) -> None:
        try:
            await asyncio.wait_for(suscriptor.notificar(evento), self._tiempo_limite)
            self.entregados += 1
        except asyncio.TimeoutError:
            self.fallidos += 1
            log.warning("%s tardó más de %ss con %s", suscriptor.nombre,
                        self._tiempo_limite, evento.numero_guia)
        except Exception:  # un suscriptor que falla no detiene al bus
            self.fallidos += 1
            log.exception("%s falló con %s", suscriptor.nombre, evento.numero_guia)
