"""Envíos: clase base y un tipo concreto por servicio."""

from __future__ import annotations

from abc import ABC
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar, Iterable, Optional

from zyntra import costos
from zyntra.dominio import (Cliente, Paquete, RegistroRastreo, Seguro,
                            ServicioExterno, Sucursal)
from zyntra.tarifas import Tarifa, TipoEnvio

if TYPE_CHECKING:
    from zyntra.costos import CalculadoraCosto


class Envio(ABC):
    """Un envío solicitado por un cliente. Contiene uno o más paquetes."""

    tipo: ClassVar[TipoEnvio]
    admite_aduana: ClassVar[bool] = False

    def __init__(self, *, numero_guia: str, cliente: Cliente, sucursal_origen: Sucursal,
                 direccion_destino: str, paquetes: Iterable[Paquete], tarifa: Tarifa,
                 seguro: Optional[Seguro] = None) -> None:
        self.numero_guia = numero_guia
        self.cliente = cliente
        self.sucursal_origen = sucursal_origen
        self.direccion_destino = direccion_destino
        self.paquetes: tuple[Paquete, ...] = tuple(paquetes)
        self.tarifa = tarifa
        self.seguro = seguro
        self.servicios_externos: list[ServicioExterno] = []
        self._rastreo: list[RegistroRastreo] = []

    # ---- Datos derivados de los paquetes ----
    @property
    def peso_facturable_kg(self) -> Decimal:
        return sum((p.peso_facturable_kg for p in self.paquetes), Decimal(0))

    @property
    def valor_declarado(self) -> Decimal:
        return sum((p.valor_declarado for p in self.paquetes), Decimal(0))

    @property
    def paquetes_fragiles(self) -> int:
        return sum(1 for p in self.paquetes if p.fragil)

    @property
    def asegurado(self) -> bool:
        return self.seguro is not None

    @property
    def rastreo(self) -> tuple[RegistroRastreo, ...]:
        return tuple(self._rastreo)

    # ---- Costo (Decorator) ----
    def armar_calculadora(self) -> "CalculadoraCosto":
        return costos.armar_calculadora(self)

    def calcular_costo(self) -> Decimal:
        return costos.calcular_costo(self)

    def agregar_servicio_externo(self, servicio: ServicioExterno) -> None:
        self.servicios_externos.append(servicio)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.numero_guia}>"


class EnvioNacional(Envio):
    tipo = TipoEnvio.NACIONAL


class EnvioExpress(Envio):
    """Entrega rápida dentro de Honduras (no cruza aduana)."""

    tipo = TipoEnvio.EXPRESS


class EnvioInternacional(Envio):
    tipo = TipoEnvio.INTERNACIONAL
    admite_aduana = True

    def __init__(self, *, pais_destino: str, **datos) -> None:
        super().__init__(**datos)
        self.pais_destino = pais_destino
