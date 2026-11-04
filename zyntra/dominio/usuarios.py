"""Usuarios del sistema: clientes y empleados."""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zyntra.dominio.puntos import Sucursal


class Rol(Enum):
    CLIENTE = "cliente"
    EMPLEADO_SUCURSAL = "empleado de sucursal"
    REPARTIDOR = "repartidor"
    ADMINISTRADOR = "administrador"


def _hash(contrasena: str, sal: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", contrasena.encode(), sal, 100_000).hex()


@dataclass(kw_only=True)
class Usuario:
    id_usuario: int
    nombre: str
    email: str
    rol: Rol
    _sal: bytes = field(default=b"", repr=False)
    _hash_contrasena: str = field(default="", repr=False)

    def establecer_contrasena(self, contrasena: str) -> None:
        self._sal = os.urandom(16)
        self._hash_contrasena = _hash(contrasena, self._sal)

    def autenticar(self, contrasena: str) -> bool:
        if not self._hash_contrasena:
            return False
        return hmac.compare_digest(self._hash_contrasena, _hash(contrasena, self._sal))


@dataclass(kw_only=True)
class Cliente(Usuario):
    direccion: str
    telefono: str
    rol: Rol = Rol.CLIENTE


@dataclass(kw_only=True)
class Empleado(Usuario):
    """Personal que registra, mueve y entrega envíos."""

    sucursal: "Sucursal"
    rol: Rol = Rol.EMPLEADO_SUCURSAL

    def __post_init__(self) -> None:
        if self.rol is Rol.CLIENTE:
            raise ValueError("Un empleado no puede tener el rol de cliente")
