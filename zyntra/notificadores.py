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
