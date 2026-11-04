"""Seguro, registros de rastreo y servicios de transportistas externos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from zyntra.dominio.puntos import PuntoLogistico
from zyntra.dominio.usuarios import Usuario


@dataclass(frozen=True, kw_only=True)
class Seguro:
    """Póliza opcional (0..1 por envío). Cubre el valor declarado del envío."""

    numero_poliza: str


@dataclass(frozen=True, kw_only=True)
class RegistroRastreo:
    """Un movimiento del envío: cuándo, en qué estado y dónde."""

    numero_guia: str
    marca_tiempo: datetime
    estado: str
    descripcion: str
    punto: Optional[PuntoLogistico] = None
    responsable: Optional[Usuario] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


@dataclass(frozen=True, kw_only=True)
class ServicioExterno:
    """Tramo subcontratado a otra transportista (p. ej. la parte internacional)."""

    empresa_transportista: str
    tipo_transporte: str
    numero_guia_externo: str
    costo_contrato: Decimal
