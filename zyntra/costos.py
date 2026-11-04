"""Decorator (estructural): el costo se arma en capas.

El costo base se calcula en una pieza; el seguro y el manejo frágil son capas
que se ponen encima solo cuando hacen falta. Un extra nuevo es un decorador
nuevo, sin tocar los existentes (DT-4).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

from zyntra.tarifas import redondear

if TYPE_CHECKING:
    from zyntra.envios import Envio


class CalculadoraCosto(ABC):
    @abstractmethod
    def calcular(self) -> Decimal:
        ...

    @abstractmethod
    def desglose(self) -> list[tuple[str, Decimal]]:
        """Conceptos que forman el costo, en el orden en que se aplicaron."""


class CostoBase(CalculadoraCosto):
    def __init__(self, fija: Decimal, por_kg: Decimal, peso_kg: Decimal) -> None:
        self._fija = fija
        self._por_kg = por_kg
        self._peso_kg = peso_kg

    def calcular(self) -> Decimal:
        return self._fija + self._por_kg * self._peso_kg

    def desglose(self) -> list[tuple[str, Decimal]]:
        return [("Tarifa fija", self._fija),
                (f"Peso ({self._peso_kg} kg)", self._por_kg * self._peso_kg)]


class DecoradorCosto(CalculadoraCosto):
    """Envuelve otra calculadora y le suma un cargo."""

    def __init__(self, envuelto: CalculadoraCosto) -> None:
        self._envuelto = envuelto

    @abstractmethod
    def _cargo(self) -> Decimal:
        ...

    @abstractmethod
    def _concepto(self) -> str:
        ...

    def calcular(self) -> Decimal:
        return self._envuelto.calcular() + self._cargo()

    def desglose(self) -> list[tuple[str, Decimal]]:
        return self._envuelto.desglose() + [(self._concepto(), self._cargo())]


class SeguroDecorator(DecoradorCosto):
    def __init__(self, envuelto: CalculadoraCosto, tasa: Decimal,
                 valor_declarado: Decimal) -> None:
        super().__init__(envuelto)
        self._tasa = tasa
        self._valor_declarado = valor_declarado

    def _cargo(self) -> Decimal:
        return self._valor_declarado * self._tasa

    def _concepto(self) -> str:
        return f"Seguro ({self._tasa * 100:g} % de {self._valor_declarado})"


class ManejoFragilDecorator(DecoradorCosto):
    """Recargo por cada paquete frágil del envío."""

    def __init__(self, envuelto: CalculadoraCosto, recargo: Decimal, paquetes: int) -> None:
        super().__init__(envuelto)
        self._recargo = recargo
        self._paquetes = paquetes

    def _cargo(self) -> Decimal:
        return self._recargo * self._paquetes

    def _concepto(self) -> str:
        return f"Manejo frágil ({self._paquetes} paquete(s))"


def armar_calculadora(envio: "Envio") -> CalculadoraCosto:
    """Compone la cadena de decoradores según lo que necesita el envío."""
    tarifa = envio.tarifa
    calculadora: CalculadoraCosto = CostoBase(tarifa.fija, tarifa.por_kg,
                                              envio.peso_facturable_kg)
    if envio.asegurado:
        calculadora = SeguroDecorator(calculadora, tarifa.tasa_seguro, envio.valor_declarado)
    if envio.paquetes_fragiles:
        calculadora = ManejoFragilDecorator(calculadora, tarifa.recargo_fragil,
                                            envio.paquetes_fragiles)
    return calculadora


def calcular_costo(envio: "Envio") -> Decimal:
    return redondear(armar_calculadora(envio).calcular())
