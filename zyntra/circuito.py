"""Circuit breaker: deja de llamar a un servicio que está caído.

Si un suscriptor falla muchas veces seguidas, seguir llamándolo solo hace
esperar al bus. El circuito se abre y los avisos van directo a la cola de
fallidos. Pasado un tiempo, se deja pasar una llamada de prueba: si
responde, el circuito se cierra; si falla, vuelve a abrirse.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Callable

UMBRAL_FALLOS = 5          # fallos seguidos que abren el circuito
TIEMPO_ESPERA_S = 30.0     # segundos abierto antes de permitir una prueba


class EstadoCircuito(Enum):
    CERRADO = "cerrado"          # normal: se llama al servicio
    ABIERTO = "abierto"          # caído: no se llama
    SEMIABIERTO = "semiabierto"  # en prueba: se permite una llamada


class CircuitBreaker:
    def __init__(self, umbral_fallos: int = UMBRAL_FALLOS,
                 tiempo_espera: float = TIEMPO_ESPERA_S,
                 reloj: Callable[[], float] = time.monotonic) -> None:
        self._umbral_fallos = umbral_fallos
        self._tiempo_espera = tiempo_espera
        self._reloj = reloj
        self._estado = EstadoCircuito.CERRADO
        self._abierto_desde = 0.0
        self._prueba_en_curso = False
        self.fallos_seguidos = 0
        self.aperturas = 0

    @property
    def estado(self) -> EstadoCircuito:
        if (self._estado is EstadoCircuito.ABIERTO
                and self._reloj() - self._abierto_desde >= self._tiempo_espera):
            self._estado = EstadoCircuito.SEMIABIERTO
            self._prueba_en_curso = False
        return self._estado

    def permite_llamada(self) -> bool:
        estado = self.estado
        if estado is EstadoCircuito.CERRADO:
            return True
        if estado is EstadoCircuito.SEMIABIERTO and not self._prueba_en_curso:
            self._prueba_en_curso = True
            return True
        return False

    def registrar_exito(self) -> None:
        self._estado = EstadoCircuito.CERRADO
        self.fallos_seguidos = 0
        self._prueba_en_curso = False

    def registrar_fallo(self) -> None:
        self.fallos_seguidos += 1
        if (self._estado is EstadoCircuito.SEMIABIERTO
                or self.fallos_seguidos >= self._umbral_fallos):
            self._abrir()

    def _abrir(self) -> None:
        self._estado = EstadoCircuito.ABIERTO
        self._abierto_desde = self._reloj()
        self._prueba_en_curso = False
        self.aperturas += 1
