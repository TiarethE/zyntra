"""Outbox: registro en disco de los avisos para que no se pierdan.

La cola del bus vive en memoria. Si el proceso se cae, lo que estaba en ella
se pierde. Con el outbox, cada evento se escribe en un archivo JSON Lines
antes de encolarse, y cada entrega exitosa a un suscriptor se anota en el
mismo archivo. Al iniciar, el bus lee el archivo y reencola solo lo que le
falta a cada suscriptor: lo ya entregado no se vuelve a enviar.

Formato (una línea por registro, solo se agregan líneas al final):

    {"tipo": "evento", "id": "...", "evento": {...}}
    {"tipo": "entregado", "id": "...", "suscriptor": "panel de rastreo"}
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from zyntra.estados import NombreEstado

if TYPE_CHECKING:
    from zyntra.eventos import CambioEstado


class Outbox:
    def __init__(self, ruta: str | os.PathLike) -> None:
        self.ruta = Path(ruta)
        self._candado = threading.Lock()  # publicar() puede llamarse desde varios hilos

    def guardar(self, evento: "CambioEstado") -> None:
        self._agregar({"tipo": "evento", "id": evento.id, "evento": _a_dict(evento)})

    def marcar_entregado(self, evento: "CambioEstado", suscriptor: str) -> None:
        self._agregar({"tipo": "entregado", "id": evento.id, "suscriptor": suscriptor})

    def pendientes(self, suscriptores: Iterable[str]) -> list[tuple["CambioEstado", set[str]]]:
        """Eventos que les faltan a alguno de los suscriptores, en el orden
        en que se publicaron, con los nombres a los que les faltan."""
        nombres = set(suscriptores)
        eventos: dict[str, CambioEstado] = {}
        entregados: dict[str, set[str]] = {}
        for registro in self._leer():
            if registro["tipo"] == "evento":
                eventos[registro["id"]] = _de_dict(registro["id"], registro["evento"])
            else:
                entregados.setdefault(registro["id"], set()).add(registro["suscriptor"])
        resultado = []
        for id_, evento in eventos.items():
            faltan = nombres - entregados.get(id_, set())
            if faltan:
                resultado.append((evento, faltan))
        return resultado

    def compactar(self, suscriptores: Iterable[str]) -> None:
        """Reescribe el archivo dejando solo lo pendiente, para que no crezca sin fin."""
        nombres = set(suscriptores)
        pendientes = self.pendientes(nombres)
        temporal = self.ruta.with_suffix(self.ruta.suffix + ".tmp")
        with self._candado:
            with temporal.open("w", encoding="utf-8") as archivo:
                for evento, faltan in pendientes:
                    archivo.write(_linea({"tipo": "evento", "id": evento.id,
                                          "evento": _a_dict(evento)}))
                    for nombre in sorted(nombres - faltan):
                        archivo.write(_linea({"tipo": "entregado", "id": evento.id,
                                              "suscriptor": nombre}))
            os.replace(temporal, self.ruta)

    def _agregar(self, registro: dict) -> None:
        with self._candado, self.ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(_linea(registro))
            archivo.flush()

    def _leer(self) -> list[dict]:
        if not self.ruta.exists():
            return []
        registros = []
        with self.ruta.open(encoding="utf-8") as archivo:
            for linea in archivo:
                try:
                    registros.append(json.loads(linea))
                except json.JSONDecodeError:
                    # Última línea a medias si el proceso se cayó mientras escribía.
                    continue
        return registros


def _linea(registro: dict) -> str:
    return json.dumps(registro, ensure_ascii=False) + "\n"


def _a_dict(evento: "CambioEstado") -> dict:
    return {"numero_guia": evento.numero_guia, "anterior": evento.anterior.value,
            "nuevo": evento.nuevo.value, "descripcion": evento.descripcion,
            "destinatario": evento.destinatario,
            "marca_tiempo": evento.marca_tiempo.isoformat()}


def _de_dict(id_: str, datos: dict) -> "CambioEstado":
    from zyntra.eventos import CambioEstado
    return CambioEstado(numero_guia=datos["numero_guia"],
                        anterior=NombreEstado(datos["anterior"]),
                        nuevo=NombreEstado(datos["nuevo"]),
                        descripcion=datos["descripcion"],
                        destinatario=datos["destinatario"],
                        marca_tiempo=datetime.fromisoformat(datos["marca_tiempo"]),
                        id=id_)
