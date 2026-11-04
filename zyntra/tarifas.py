"""Tipos de envío y sus tarifas (resuelve DT-2 y DT-5).

Las tarifas ya no están escritas dentro de la lógica: se cargan de
``datos/tarifas.json``. Cambiar un precio es editar ese archivo.
Todos los montos están en lempiras (HNL) y se manejan con ``Decimal``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from pathlib import Path
from typing import Optional

MONEDA = "HNL"
RUTA_TARIFAS = Path(__file__).parent / "datos" / "tarifas.json"
CENTAVO = Decimal("0.01")


def redondear(monto: Decimal) -> Decimal:
    return monto.quantize(CENTAVO, rounding=ROUND_HALF_UP)


class TipoEnvio(Enum):
    NACIONAL = "nacional"
    INTERNACIONAL = "internacional"
    EXPRESS = "express"


@dataclass(frozen=True)
class Tarifa:
    fija: Decimal
    por_kg: Decimal
    tasa_seguro: Decimal      # proporción del valor declarado (0.03 = 3 %)
    recargo_fragil: Decimal   # por cada paquete frágil


def cargar_tarifas(ruta: Optional[Path] = None) -> dict[TipoEnvio, Tarifa]:
    with open(ruta or RUTA_TARIFAS, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    tarifas = {}
    for tipo in TipoEnvio:
        valores = datos[tipo.value]
        tarifas[tipo] = Tarifa(**{clave: Decimal(str(v)) for clave, v in valores.items()})
    return tarifas
