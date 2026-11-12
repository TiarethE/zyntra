"""Suscriptores concretos del bus de eventos (observadores)."""

from __future__ import annotations

import asyncio

from zyntra.eventos import CambioEstado, Suscriptor


class NotificadorCliente(Suscriptor):
    """Avisa al cliente de cada cambio. Aquí se simula guardando el mensaje;
    en producción enviaría un correo o SMS."""

    nombre = "notificador de clientes"

    def __init__(self, demora_s: float = 0.0) -> None:
        self._demora_s = demora_s
        self.enviados: list[tuple[str, str]] = []

    async def notificar(self, evento: CambioEstado) -> None:
        await asyncio.sleep(self._demora_s)  # simula la latencia del servicio de correo
        mensaje = (f"Tu envío {evento.numero_guia} ahora está «{evento.nuevo.value}»: "
                   f"{evento.descripcion}")
        self.enviados.append((evento.destinatario, mensaje))


class PanelRastreo(Suscriptor):
    """Vista en tiempo real del último estado de cada envío."""

    nombre = "panel de rastreo"

    def __init__(self) -> None:
        self.ultimo_estado: dict[str, CambioEstado] = {}

    async def notificar(self, evento: CambioEstado) -> None:
        self.ultimo_estado[evento.numero_guia] = evento


class TransmisorEnVivo(Suscriptor):
    """Reenvía cada cambio a las pantallas abiertas (interfaz web).

    Cada pantalla conectada recibe su propia cola. Si una pantalla no lee
    a tiempo y su cola se llena, se le salta el aviso: una pantalla lenta
    nunca frena al bus ni a las demás.
    """

    nombre = "transmisor en vivo"
    CAPACIDAD_POR_PANTALLA = 100

    def __init__(self) -> None:
        self._pantallas: set[asyncio.Queue[CambioEstado]] = set()
        self.omitidos = 0

    @property
    def conectadas(self) -> int:
        return len(self._pantallas)

    def conectar(self) -> asyncio.Queue[CambioEstado]:
        cola: asyncio.Queue[CambioEstado] = asyncio.Queue(self.CAPACIDAD_POR_PANTALLA)
        self._pantallas.add(cola)
        return cola

    def desconectar(self, cola: asyncio.Queue[CambioEstado]) -> None:
        self._pantallas.discard(cola)

    async def notificar(self, evento: CambioEstado) -> None:
        for cola in list(self._pantallas):
            try:
                cola.put_nowait(evento)
            except asyncio.QueueFull:
                self.omitidos += 1
