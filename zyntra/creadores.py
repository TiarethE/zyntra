"""Factory Method (creacional): un creador por tipo de envío.

Resuelve DT-1 (la decisión por tipo ya no se repite), DT-2 (el tipo es una
clase, no un texto) y DT-6 (los datos se validan antes de crear el envío).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Iterable, Optional

from zyntra.dominio import Cliente, Paquete, Seguro, Sucursal
from zyntra.envios import Envio, EnvioExpress, EnvioInternacional, EnvioNacional
from zyntra.tarifas import Tarifa, TipoEnvio

FORMATO_GUIA = re.compile(r"^ZYN-\d{8}$")
PAIS_SEDE = "Honduras"


class EnvioCreator(ABC):
    """Creador: define el paso de creación y deja a cada subclase fabricar su tipo."""

    def __init__(self, tarifa: Tarifa) -> None:
        self.tarifa = tarifa

    def crear_envio(self, *, numero_guia: str, cliente: Cliente, sucursal_origen: Sucursal,
                    direccion_destino: str, paquetes: Iterable[Paquete],
                    seguro: Optional[Seguro] = None, **extra) -> Envio:
        paquetes = tuple(paquetes)
        self._validar(numero_guia, direccion_destino, paquetes, seguro)
        self._validar_extra(paquetes, **extra)
        return self._fabricar(numero_guia=numero_guia, cliente=cliente,
                              sucursal_origen=sucursal_origen,
                              direccion_destino=direccion_destino, paquetes=paquetes,
                              tarifa=self.tarifa, seguro=seguro, **extra)

    @staticmethod
    def _validar(numero_guia: str, direccion_destino: str, paquetes: tuple[Paquete, ...],
                 seguro: Optional[Seguro]) -> None:
        if not FORMATO_GUIA.match(numero_guia or ""):
            raise ValueError("El número de guía debe tener el formato ZYN-00000000")
        if not direccion_destino.strip():
            raise ValueError("Falta la dirección de destino")
        if not paquetes:
            raise ValueError("Un envío debe contener al menos un paquete")
        if seguro and sum((p.valor_declarado for p in paquetes), Decimal(0)) <= 0:
            raise ValueError("Para asegurar un envío hay que declarar su valor")

    def _validar_extra(self, paquetes: tuple[Paquete, ...], **extra) -> None:
        """Reglas propias de cada tipo. Por defecto no acepta datos adicionales."""
        if extra:
            raise TypeError(f"Datos no válidos para este tipo: {', '.join(extra)}")

    @abstractmethod
    def _fabricar(self, **datos) -> Envio:
        ...


class EnvioNacionalCreator(EnvioCreator):
    def _fabricar(self, **datos) -> Envio:
        return EnvioNacional(**datos)


class EnvioExpressCreator(EnvioCreator):
    PESO_MAXIMO_KG = Decimal(30)

    def _validar_extra(self, paquetes, **extra) -> None:
        super()._validar_extra(paquetes, **extra)
        if sum(p.peso_kg for p in paquetes) > self.PESO_MAXIMO_KG:
            raise ValueError(f"El servicio express admite hasta {self.PESO_MAXIMO_KG} kg")

    def _fabricar(self, **datos) -> Envio:
        return EnvioExpress(**datos)


class EnvioInternacionalCreator(EnvioCreator):
    def _validar_extra(self, paquetes, pais_destino: str = "", **extra) -> None:
        super()._validar_extra(paquetes, **extra)
        if not pais_destino.strip():
            raise ValueError("Un envío internacional necesita país de destino")
        if pais_destino.strip().lower() == PAIS_SEDE.lower():
            raise ValueError("Para envíos dentro de Honduras use el servicio nacional")
        if any(p.valor_declarado <= 0 for p in paquetes):
            raise ValueError("La aduana exige valor declarado en cada paquete")

    def _fabricar(self, **datos) -> Envio:
        return EnvioInternacional(**datos)


# Registro de creadores: agregar un tipo es agregar una entrada, sin if/elif.
CLASES_CREADOR: dict[TipoEnvio, type[EnvioCreator]] = {
    TipoEnvio.NACIONAL: EnvioNacionalCreator,
    TipoEnvio.INTERNACIONAL: EnvioInternacionalCreator,
    TipoEnvio.EXPRESS: EnvioExpressCreator,
}


def crear_creadores(tarifas: dict[TipoEnvio, Tarifa]) -> dict[TipoEnvio, EnvioCreator]:
    return {tipo: clase(tarifas[tipo]) for tipo, clase in CLASES_CREADOR.items()}
