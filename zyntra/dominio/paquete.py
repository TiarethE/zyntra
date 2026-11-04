"""Paquete físico que forma parte de un envío."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Divisor estándar de la industria para peso volumétrico (cm³ por kg).
DIVISOR_VOLUMETRICO = Decimal(5000)


@dataclass(frozen=True, kw_only=True)
class Paquete:
    peso_kg: Decimal
    alto_cm: Decimal
    ancho_cm: Decimal
    largo_cm: Decimal
    contenido: str
    valor_declarado: Decimal = Decimal(0)
    fragil: bool = False

    def __post_init__(self) -> None:
        for nombre in ("peso_kg", "alto_cm", "ancho_cm", "largo_cm"):
            valor = getattr(self, nombre)
            if not isinstance(valor, Decimal):
                object.__setattr__(self, nombre, Decimal(str(valor)))
            if getattr(self, nombre) <= 0:
                raise ValueError(f"{nombre} debe ser mayor que cero")
        if not isinstance(self.valor_declarado, Decimal):
            object.__setattr__(self, "valor_declarado", Decimal(str(self.valor_declarado)))
        if self.valor_declarado < 0:
            raise ValueError("valor_declarado no puede ser negativo")
        if not self.contenido.strip():
            raise ValueError("Se debe describir el contenido del paquete")

    @property
    def peso_volumetrico_kg(self) -> Decimal:
        return self.alto_cm * self.ancho_cm * self.largo_cm / DIVISOR_VOLUMETRICO

    @property
    def peso_facturable_kg(self) -> Decimal:
        """Se cobra el mayor entre el peso real y el volumétrico."""
        return max(self.peso_kg, self.peso_volumetrico_kg)
