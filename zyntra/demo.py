"""Demostración ejecutable: python -m zyntra.demo"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from zyntra.creadores import crear_creadores
from zyntra.dominio import Bodega, Cliente, Empleado, Paquete, Rol, Seguro, Sucursal
from zyntra.estados import NombreEstado as E, TransicionInvalida
from zyntra.eventos import BusEventos, CambioEstado, Suscriptor
from zyntra.gestor import GestorEnvios
from zyntra.notificadores import NotificadorCliente, PanelRastreo
from zyntra.tarifas import MONEDA, TipoEnvio, cargar_tarifas


class NotificadorCaido(Suscriptor):
    nombre = "notificador SMS (simulado caído)"

    async def notificar(self, evento: CambioEstado) -> None:
        await asyncio.sleep(5)


def titulo(texto: str) -> None:
    print(f"\n== {texto} ==")


async def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="  [aviso] %(message)s")

    sucursal = Sucursal(id_punto=1, nombre="Zyntra Tegucigalpa Centro",
                        direccion="Av. Cervantes", ciudad="Tegucigalpa")
    bodega = Bodega(id_punto=2, nombre="Bodega San Pedro Sula", direccion="Bulevar del Norte",
                    ciudad="San Pedro Sula", capacidad_maxima=5000)
    cliente = Cliente(id_usuario=1, nombre="Ana López", email="ana@correo.hn",
                      direccion="Col. Palmira, Tegucigalpa", telefono="9999-0000")
    repartidor = Empleado(id_usuario=2, nombre="Luis Martínez", email="luis@zyntra.hn",
                          sucursal=sucursal, rol=Rol.REPARTIDOR)

    bus = BusEventos(tiempo_limite=0.3, max_reintentos=1, espera_base=0.05)
    correo, panel = NotificadorCliente(demora_s=0.1), PanelRastreo()
    for suscriptor in (correo, panel, NotificadorCaido()):
        bus.suscribir(suscriptor)
    await bus.iniciar()

    gestor = GestorEnvios(crear_creadores(cargar_tarifas()), bus)

    titulo("1. Factory Method: se registra un envío internacional")
    envio = gestor.registrar_envio(
        TipoEnvio.INTERNACIONAL, numero_guia="ZYN-00000042", cliente=cliente,
        sucursal_origen=sucursal, direccion_destino="1200 Brickell Ave, Miami",
        pais_destino="Estados Unidos", seguro=Seguro(numero_poliza="POL-7781"),
        paquetes=[Paquete(peso_kg=Decimal("3.5"), alto_cm=Decimal(20), ancho_cm=Decimal(30),
                          largo_cm=Decimal(40), contenido="Café de Marcala",
                          valor_declarado=Decimal(1500)),
                  Paquete(peso_kg=Decimal(1), alto_cm=Decimal(15), ancho_cm=Decimal(15),
                          largo_cm=Decimal(15), contenido="Artesanía de barro",
                          valor_declarado=Decimal(800), fragil=True)])
    print(f"  {envio!r} creado por {type(envio).__name__}Creator")

    try:
        gestor.registrar_envio(TipoEnvio.NACIONAL, numero_guia="ZYN-1", cliente=cliente,
                               sucursal_origen=sucursal, direccion_destino="SPS",
                               paquetes=[])
    except ValueError as error:
        print(f"  Datos inválidos rechazados: {error}")

    titulo("2. Decorator: desglose del costo")
    for concepto, monto in envio.armar_calculadora().desglose():
        print(f"  {concepto:<38} {MONEDA} {monto:>10.2f}")
    print(f"  {'TOTAL':<38} {MONEDA} {envio.calcular_costo():>10.2f}")

    titulo("3. State + Observer: recorrido del envío")
    pasos = [(E.EN_TRANSITO, dict(punto=bodega, descripcion="Salió de bodega San Pedro Sula")),
             (E.RETENIDO_EN_ADUANA, dict(descripcion="Revisión en aduana de Miami")),
             (E.EN_TRANSITO, dict(descripcion="Liberado por aduana")),
             (E.EN_REPARTO, dict(responsable=repartidor, descripcion="En ruta de entrega")),
             (E.ENTREGADO, dict(responsable=repartidor, descripcion="Recibido por el cliente"))]
    for destino, detalles in pasos:
        gestor.cambiar_estado(envio.numero_guia, destino, **detalles)
        print(f"  -> {envio.estado.value}")

    try:
        gestor.cambiar_estado(envio.numero_guia, E.CANCELADO)
    except TransicionInvalida as error:
        print(f"  Transición rechazada: {error}")

    await bus.detener()

    titulo("4. Rastreo registrado")
    for registro in gestor.rastrear(envio.numero_guia):
        print(f"  {registro.marca_tiempo:%H:%M:%S}  {registro.estado:<20} {registro.descripcion}")

    titulo("5. Notificaciones entregadas al cliente")
    for destinatario, mensaje in correo.enviados:
        print(f"  {destinatario}: {mensaje}")
    print(f"  Panel de rastreo: {panel.ultimo_estado[envio.numero_guia].nuevo.value}")

    titulo("6. Métricas del módulo de respuesta")
    stats = bus.estadisticas
    for clave in ("entregados", "reintentos", "fallidos", "descartados",
                  "rechazados_por_circuito", "en_cola_fallidos"):
        print(f"  {clave:<26} {stats[clave]}")
    for clave in ("latencia_promedio_ms", "latencia_p95_ms", "latencia_max_ms"):
        print(f"  {clave:<26} {stats[clave]} ms")
    salud = bus.salud()
    print(f"  Salud del bus: {salud['estado']}")
    for nombre, datos in salud["suscriptores"].items():
        print(f"    {nombre:<34} circuito {datos['circuito']}, "
              f"{datos['en_cola_fallidos']} en cola de fallidos")


if __name__ == "__main__":
    asyncio.run(main())
