"""Envíos: clase base y un tipo concreto por servicio."""

from __future__ import annotations

from abc import ABC
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar, Iterable, Optional

from zyntra import costos
from zyntra.dominio import (Cliente, Paquete, PuntoLogistico, RegistroRastreo, Seguro,
                            ServicioExterno, Sucursal, Usuario)
from zyntra.estados import EstadoEnvio, NombreEstado, Registrado
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
        self._estado: EstadoEnvio = Registrado()
        self._rastreo: list[RegistroRastreo] = []
        self._registrar(f"Recibido en {sucursal_origen.nombre}", sucursal_origen, None,
                        None, None, None)

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

    # ---- Estado (State) ----
    @property
    def estado(self) -> NombreEstado:
        return self._estado.nombre

    def puede_ir_a(self, destino: NombreEstado) -> bool:
        return self._estado.puede_ir_a(self, destino)

    def cambiar_estado(self, destino: NombreEstado, *, descripcion: str = "",
                       punto: Optional[PuntoLogistico] = None,
                       responsable: Optional[Usuario] = None,
                       latitud: Optional[float] = None, longitud: Optional[float] = None,
                       momento: Optional[datetime] = None) -> RegistroRastreo:
        """Cambia de estado y deja el registro de rastreo en el mismo paso.

        Lanza TransicionInvalida si el estado actual no permite el cambio.
        """
        self._estado = self._estado.transicionar(self, destino)
        return self._registrar(descripcion or destino.value, punto, responsable,
                               latitud, longitud, momento)

    def _registrar(self, descripcion, punto, responsable, latitud, longitud,
                   momento) -> RegistroRastreo:
        registro = RegistroRastreo(numero_guia=self.numero_guia,
                                   marca_tiempo=momento or datetime.now(),
                                   estado=self.estado.value, descripcion=descripcion,
                                   punto=punto, responsable=responsable,
                                   latitud=latitud, longitud=longitud)
        self._rastreo.append(registro)
        return registro

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
