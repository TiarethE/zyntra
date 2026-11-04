"""Puntos logísticos de la empresa: sucursales y bodegas."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class Vehiculo:
    placas: str
    capacidad_carga_kg: float
    disponible: bool = True


@dataclass(kw_only=True)
class PuntoLogistico(ABC):
    id_punto: int
    nombre: str
    direccion: str
    ciudad: str


@dataclass(kw_only=True)
class Sucursal(PuntoLogistico):
    """Atiende al público: ahí se reciben los envíos."""

    atiende_publico: bool = True


@dataclass(kw_only=True)
class Bodega(PuntoLogistico):
    """Almacena paquetes y opera los vehículos de reparto."""

    capacidad_maxima: int
    vehiculos: list[Vehiculo] = field(default_factory=list)

    def vehiculos_disponibles(self) -> list[Vehiculo]:
        return [v for v in self.vehiculos if v.disponible]
