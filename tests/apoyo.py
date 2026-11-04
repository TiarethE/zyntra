"""Datos de ejemplo compartidos por las pruebas."""

from decimal import Decimal

from zyntra.creadores import crear_creadores
from zyntra.dominio import Cliente, Paquete, Seguro, Sucursal
from zyntra.tarifas import TipoEnvio, cargar_tarifas

SUCURSAL = Sucursal(id_punto=1, nombre="Zyntra Centro", direccion="Av. Cervantes",
                    ciudad="Tegucigalpa")
CLIENTE = Cliente(id_usuario=1, nombre="Ana López", email="ana@correo.hn",
                  direccion="Col. Palmira", telefono="9999-0000")
SEGURO = Seguro(numero_poliza="POL-001")


def paquete(peso=2, valor=0, fragil=False, lado=10):
    return Paquete(peso_kg=Decimal(peso), alto_cm=Decimal(lado), ancho_cm=Decimal(lado),
                   largo_cm=Decimal(lado), contenido="Ropa",
                   valor_declarado=Decimal(valor), fragil=fragil)


def creadores():
    return crear_creadores(cargar_tarifas())


def datos_envio(paquetes=None, seguro=None, guia="ZYN-00000001", **extra):
    return dict(numero_guia=guia, cliente=CLIENTE, sucursal_origen=SUCURSAL,
                direccion_destino="Barrio Guamilito, San Pedro Sula",
                paquetes=paquetes or [paquete()], seguro=seguro, **extra)


def nuevo_envio(tipo=TipoEnvio.NACIONAL, **kw):
    if tipo is TipoEnvio.INTERNACIONAL:
        kw.setdefault("pais_destino", "Estados Unidos")
        kw.setdefault("paquetes", [paquete(valor=1000)])
    return creadores()[tipo].crear_envio(**datos_envio(**kw))
