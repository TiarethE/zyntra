"""Observer (comportamiento): bus de eventos para el rastreo en tiempo real.

Cada cambio de estado se publica como un evento. Los suscriptores
(notificaciones, panel de rastreo) se enteran sin que el envío los conozca
(DT-7). Es tiempo real blando: publicar nunca bloquea, cada suscriptor tiene
un tiempo límite y un fallo no afecta a los demás. Un aviso que falla se
reintenta con espera exponencial; si se agotan los intentos, queda en la
cola de fallidos para reprocesarlo después.
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
MAX_REINTENTOS = 3         # intentos extra antes de mandar el aviso a la cola de fallidos
ESPERA_BASE_S = 0.1        # espera antes del primer reintento; se duplica en cada uno


@dataclass(frozen=True)
class CambioEstado:
    numero_guia: str
    anterior: NombreEstado
    nuevo: NombreEstado
    descripcion: str
    destinatario: str          # correo del cliente
    marca_tiempo: datetime


@dataclass(frozen=True)
class EventoFallido:
    """Aviso que agotó sus reintentos (cola de fallidos o *dead-letter*)."""

    evento: CambioEstado
    suscriptor: str
    intentos: int
    motivo: str
    marca_tiempo: datetime


class Suscriptor(ABC):
    nombre: str = "suscriptor"

    @abstractmethod
    async def notificar(self, evento: CambioEstado) -> None:
        ...


class BusEventos:
    """Sujeto del patrón Observer. Se crea fuera y se inyecta (no es global)."""

    def __init__(self, capacidad: int = CAPACIDAD_COLA,
                 tiempo_limite: float = TIEMPO_LIMITE_S,
                 max_reintentos: int = MAX_REINTENTOS,
                 espera_base: float = ESPERA_BASE_S) -> None:
        self._suscriptores: list[Suscriptor] = []
        self._cola: asyncio.Queue[CambioEstado] = asyncio.Queue(maxsize=capacidad)
        self._tiempo_limite = tiempo_limite
        self._max_reintentos = max_reintentos
        self._espera_base = espera_base
        self._tarea: Optional[asyncio.Task] = None
        self.cola_fallidos: list[EventoFallido] = []
        self.entregados = 0
        self.reintentos = 0
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
        return {"entregados": self.entregados, "reintentos": self.reintentos,
                "fallidos": self.fallidos, "descartados": self.descartados,
                "pendientes": self._cola.qsize(), "en_cola_fallidos": len(self.cola_fallidos)}

    async def reprocesar_fallidos(self) -> int:
        """Vuelve a intentar los avisos de la cola de fallidos.

        Devuelve cuántos se entregaron; los que vuelven a fallar regresan a la cola.
        """
        pendientes, self.cola_fallidos = self.cola_fallidos, []
        por_nombre = {s.nombre: s for s in self._suscriptores}
        entregados = 0
        for fallido in pendientes:
            suscriptor = por_nombre.get(fallido.suscriptor)
            if suscriptor is None:
                self.cola_fallidos.append(fallido)
                continue
            if await self._entregar(suscriptor, fallido.evento):
                entregados += 1
        return entregados

    async def _trabajar(self) -> None:
        while True:
            evento = await self._cola.get()
            try:
                # Todos los suscriptores a la vez: uno lento no retrasa a los demás.
                await asyncio.gather(*(self._entregar(s, evento) for s in self._suscriptores))
            finally:
                self._cola.task_done()

    async def _entregar(self, suscriptor: Suscriptor, evento: CambioEstado) -> bool:
        """Entrega con reintentos y espera exponencial. Devuelve si se entregó."""
        motivo = ""
        for intento in range(self._max_reintentos + 1):
            if intento:
                self.reintentos += 1
                await asyncio.sleep(self._espera_base * 2 ** (intento - 1))
            try:
                await asyncio.wait_for(suscriptor.notificar(evento), self._tiempo_limite)
                self.entregados += 1
                return True
            except asyncio.TimeoutError:
                motivo = f"tardó más de {self._tiempo_limite}s"
            except Exception as error:  # un suscriptor que falla no detiene al bus
                motivo = f"{type(error).__name__}: {error}"
            log.warning("%s: intento %d con %s fallido (%s)", suscriptor.nombre,
                        intento + 1, evento.numero_guia, motivo)
        self.fallidos += 1
        self.cola_fallidos.append(EventoFallido(
            evento=evento, suscriptor=suscriptor.nombre, intentos=self._max_reintentos + 1,
            motivo=motivo, marca_tiempo=datetime.now()))
        return False
