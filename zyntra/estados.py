"""State (comportamiento): cada estado del envío es una clase.

Cada estado sabe a cuáles puede pasar. El envío solo le pregunta a su
estado actual si el cambio es válido (DT-3). Los nombres de estado son un
enum, no textos sueltos (DT-2).
"""

from __future__ import annotations

from abc import ABC
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from zyntra.envios import Envio


class NombreEstado(Enum):
    REGISTRADO = "Registrado"
    EN_TRANSITO = "En tránsito"
    RETENIDO_EN_ADUANA = "Retenido en aduana"
    EN_REPARTO = "En reparto"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"


class TransicionInvalida(Exception):
    pass


class EstadoEnvio(ABC):
    nombre: ClassVar[NombreEstado]
    destinos: ClassVar[frozenset[NombreEstado]] = frozenset()

    @property
    def es_final(self) -> bool:
        return not self.destinos

    def puede_ir_a(self, envio: "Envio", destino: NombreEstado) -> bool:
        return destino in self.destinos

    def transicionar(self, envio: "Envio", destino: NombreEstado) -> "EstadoEnvio":
        if not self.puede_ir_a(envio, destino):
            raise TransicionInvalida(
                f"{envio.numero_guia}: no se puede pasar de «{self.nombre.value}» "
                f"a «{destino.value}»")
        return CLASES_ESTADO[destino]()

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class Registrado(EstadoEnvio):
    """Recibido en la sucursal de origen."""

    nombre = NombreEstado.REGISTRADO
    destinos = frozenset({NombreEstado.EN_TRANSITO, NombreEstado.CANCELADO})


class EnTransito(EstadoEnvio):
    nombre = NombreEstado.EN_TRANSITO
    destinos = frozenset({NombreEstado.EN_REPARTO, NombreEstado.RETENIDO_EN_ADUANA})

    def puede_ir_a(self, envio: "Envio", destino: NombreEstado) -> bool:
        # Regla propia de este estado: solo los internacionales pasan por aduana.
        if destino is NombreEstado.RETENIDO_EN_ADUANA and not envio.admite_aduana:
            return False
        return super().puede_ir_a(envio, destino)


class RetenidoEnAduana(EstadoEnvio):
    nombre = NombreEstado.RETENIDO_EN_ADUANA
    destinos = frozenset({NombreEstado.EN_TRANSITO})


class EnReparto(EstadoEnvio):
    nombre = NombreEstado.EN_REPARTO
    destinos = frozenset({NombreEstado.ENTREGADO})


class Entregado(EstadoEnvio):
    nombre = NombreEstado.ENTREGADO


class Cancelado(EstadoEnvio):
    nombre = NombreEstado.CANCELADO


CLASES_ESTADO: dict[NombreEstado, type[EstadoEnvio]] = {
    clase.nombre: clase
    for clase in (Registrado, EnTransito, RetenidoEnAduana, EnReparto, Entregado, Cancelado)
}
