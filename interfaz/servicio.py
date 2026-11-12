"""Servicio de la interfaz: traduce lo que llega de la pantalla al dominio.

No tiene reglas de negocio propias. Toda validación, costo y cambio de
estado lo hacen las clases de ``zyntra`` (Factory Method, Decorator, State
y Observer). Aquí solo se arman los objetos y se convierten a diccionarios
para enviarlos como JSON.
"""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from zyntra.creadores import crear_creadores
from zyntra.dominio import Bodega, Cliente, Empleado, Paquete, Rol, Seguro, Sucursal
from zyntra.envios import Envio
from zyntra.estados import NombreEstado
from zyntra.eventos import BusEventos, CambioEstado, Suscriptor
from zyntra.gestor import GestorEnvios
from zyntra.notificadores import NotificadorCliente, PanelRastreo, TransmisorEnVivo
from zyntra.tarifas import MONEDA, TipoEnvio, cargar_tarifas

GUIA_COTIZACION = "ZYN-00000000"   # guía temporal: la cotización no se registra
PRIMERA_GUIA = 10_000_101
PAUSA_SIMULACION_S = 2.5

SUCURSALES = [
    Sucursal(id_punto=1, nombre="Zyntra Tegucigalpa Centro", direccion="Av. Cervantes",
             ciudad="Tegucigalpa"),
    Sucursal(id_punto=2, nombre="Zyntra San Pedro Sula", direccion="Bulevar Los Próceres",
             ciudad="San Pedro Sula"),
    Sucursal(id_punto=3, nombre="Zyntra La Ceiba", direccion="Av. San Isidro",
             ciudad="La Ceiba"),
    Sucursal(id_punto=4, nombre="Zyntra Choluteca", direccion="Barrio El Centro",
             ciudad="Choluteca"),
]
BODEGAS = [
    Bodega(id_punto=10, nombre="Centro de distribución Comayagüela",
           direccion="Anillo Periférico", ciudad="Tegucigalpa", capacidad_maxima=8000),
    Bodega(id_punto=11, nombre="Centro de distribución San Pedro Sula",
           direccion="Bulevar del Norte", ciudad="San Pedro Sula", capacidad_maxima=5000),
]
REPARTIDOR = Empleado(id_usuario=900, nombre="Luis Martínez", email="luis@zyntra.hn",
                      sucursal=SUCURSALES[0], rol=Rol.REPARTIDOR)

# Recorrido normal de cada tipo, que usa «Simular recorrido».
RECORRIDO = {
    TipoEnvio.NACIONAL: [
        (NombreEstado.EN_TRANSITO, "Salió del centro de distribución"),
        (NombreEstado.EN_REPARTO, "En ruta de entrega"),
        (NombreEstado.ENTREGADO, "Recibido por el destinatario")],
    TipoEnvio.EXPRESS: [
        (NombreEstado.EN_TRANSITO, "Salida express hacia la ciudad de destino"),
        (NombreEstado.EN_REPARTO, "En ruta de entrega express"),
        (NombreEstado.ENTREGADO, "Recibido por el destinatario")],
    TipoEnvio.INTERNACIONAL: [
        (NombreEstado.EN_TRANSITO, "Salió de Honduras hacia el país de destino"),
        (NombreEstado.RETENIDO_EN_ADUANA, "Revisión en aduana del país de destino"),
        (NombreEstado.EN_TRANSITO, "Liberado por aduana"),
        (NombreEstado.EN_REPARTO, "En ruta de entrega"),
        (NombreEstado.ENTREGADO, "Recibido por el destinatario")],
}


class DatosInvalidos(ValueError):
    """Los datos del formulario no se pueden convertir a objetos del dominio."""


class NotificadorSMS(Suscriptor):
    """Servicio de SMS simulado. Desde la pantalla «Sistema» se puede «tirar»
    para ver en vivo los reintentos, la cola de fallidos y el circuit breaker."""

    nombre = "notificador SMS"

    def __init__(self) -> None:
        self.caido = False
        self.enviados: list[tuple[str, str]] = []

    async def notificar(self, evento: CambioEstado) -> None:
        await asyncio.sleep(0.05)
        if self.caido:
            raise ConnectionError("el proveedor de SMS no responde")
        self.enviados.append((evento.numero_guia, f"Zyntra: {evento.numero_guia} "
                                                  f"{evento.nuevo.value}"))


@dataclass
class Metadatos:
    creado: datetime
    simulando: bool = False


def _decimal(valor: Any, campo: str) -> Decimal:
    texto = "" if valor is None else str(valor).strip()
    try:
        return Decimal(texto or "0")
    except InvalidOperation:
        raise DatosInvalidos(f"«{campo}» debe ser un número") from None


def _paquetes(datos: list[dict]) -> list[Paquete]:
    paquetes = []
    for i, p in enumerate(datos or [], start=1):
        try:
            paquetes.append(Paquete(
                peso_kg=_decimal(p.get("peso_kg"), "peso"),
                alto_cm=_decimal(p.get("alto_cm"), "alto"),
                ancho_cm=_decimal(p.get("ancho_cm"), "ancho"),
                largo_cm=_decimal(p.get("largo_cm"), "largo"),
                contenido=str(p.get("contenido") or ""),
                valor_declarado=_decimal(p.get("valor_declarado"), "valor declarado"),
                fragil=bool(p.get("fragil"))))
        except DatosInvalidos as error:
            raise DatosInvalidos(f"Paquete {i}: {error}") from None
        except ValueError as error:
            raise DatosInvalidos(f"Paquete {i}: {_texto_campo(error)}") from None
    return paquetes


def _texto_campo(error: Exception) -> str:
    texto = str(error)
    for campo, legible in (("peso_kg", "el peso"), ("alto_cm", "el alto"),
                           ("ancho_cm", "el ancho"), ("largo_cm", "el largo"),
                           ("valor_declarado", "el valor declarado")):
        texto = texto.replace(campo, legible)
    return texto[:1].upper() + texto[1:]


def _monto(valor: Decimal) -> str:
    return f"{valor.quantize(Decimal('0.01'))}"


class ServicioZyntra:
    def __init__(self) -> None:
        self.tarifas = cargar_tarifas()
        self.creadores = crear_creadores(self.tarifas)
        self.bus = BusEventos(tiempo_limite=0.5, max_reintentos=2, espera_base=0.1,
                              espera_circuito=15)
        self.correo = NotificadorCliente(demora_s=0.05)
        self.sms = NotificadorSMS()
        self.panel = PanelRastreo()
        self.transmisor = TransmisorEnVivo()
        for suscriptor in (self.correo, self.sms, self.panel, self.transmisor):
            self.bus.suscribir(suscriptor)
        self.gestor = GestorEnvios(self.creadores, self.bus)
        self._guias = itertools.count(PRIMERA_GUIA)
        self._polizas = itertools.count(5001)
        self._clientes = itertools.count(1)
        self._meta: dict[str, Metadatos] = {}
        self._tareas: set[asyncio.Task] = set()

    # ---- Ciclo de vida ----
    async def iniciar(self, con_ejemplos: bool = True) -> None:
        await self.bus.iniciar()
        if con_ejemplos and not self.gestor.listar():
            self._cargar_ejemplos()

    async def detener(self) -> None:
        for tarea in list(self._tareas):
            tarea.cancel()
        await asyncio.gather(*self._tareas, return_exceptions=True)
        await self.bus.detener()

    # ---- Catálogos ----
    def catalogo(self) -> dict:
        return {
            "moneda": MONEDA,
            "sucursales": [{"id": s.id_punto, "nombre": s.nombre, "ciudad": s.ciudad}
                           for s in SUCURSALES],
            "tipos": [{"id": t.value, "fija": _monto(tar.fija), "por_kg": _monto(tar.por_kg),
                       "tasa_seguro": str(tar.tasa_seguro),
                       "recargo_fragil": _monto(tar.recargo_fragil)}
                      for t, tar in self.tarifas.items()],
            "estados": [e.value for e in NombreEstado],
        }

    # ---- Cotizar y registrar (Factory Method + Decorator) ----
    def _armar(self, datos: dict, numero_guia: str, cliente: Cliente,
               poliza: str) -> tuple[TipoEnvio, dict]:
        try:
            tipo = TipoEnvio(datos.get("tipo"))
        except ValueError:
            raise DatosInvalidos("Elija el tipo de envío") from None
        sucursal = self._sucursal(datos.get("sucursal_origen"))
        paquetes = _paquetes(datos.get("paquetes"))
        extra: dict[str, Any] = {}
        if tipo is TipoEnvio.INTERNACIONAL:
            extra["pais_destino"] = str(datos.get("pais_destino") or "")
        seguro = Seguro(numero_poliza=poliza) if datos.get("asegurar") else None
        return tipo, dict(numero_guia=numero_guia, cliente=cliente, sucursal_origen=sucursal,
                          direccion_destino=str(datos.get("direccion_destino") or ""),
                          paquetes=paquetes, seguro=seguro, **extra)

    def cotizar(self, datos: dict) -> dict:
        """Calcula el costo con las mismas clases que el registro, sin guardar nada."""
        cliente = Cliente(id_usuario=0, nombre="Cotización", email="", direccion="",
                          telefono="")
        # Para cotizar bastan peso y medidas: lo demás se completa provisionalmente.
        borrador = {**datos,
                    "direccion_destino": datos.get("direccion_destino") or "(por definir)",
                    "paquetes": [{**p, "contenido": p.get("contenido") or "(por definir)"}
                                 for p in datos.get("paquetes") or []]}
        tipo, armado = self._armar(borrador, GUIA_COTIZACION, cliente, "POL-COTIZACION")
        try:
            envio = self.creadores[tipo].crear_envio(**armado)
        except (ValueError, TypeError) as error:
            raise DatosInvalidos(str(error)) from None
        return self._costo(envio)

    def registrar(self, datos: dict) -> dict:
        cliente = self._cliente(datos.get("cliente") or {})
        guia = f"ZYN-{next(self._guias):08d}"
        tipo, armado = self._armar(datos, guia, cliente, f"POL-{next(self._polizas)}")
        try:
            envio = self.gestor.registrar_envio(tipo, **armado)
        except (ValueError, TypeError) as error:
            raise DatosInvalidos(str(error)) from None
        self._meta[guia] = Metadatos(creado=datetime.now())
        return self.detalle(guia)

    # ---- Consultar ----
    def listar(self) -> list[dict]:
        return [self._resumen(e) for e in self.gestor.listar()]

    def detalle(self, numero_guia: str) -> dict:
        envio = self.gestor.obtener(numero_guia.strip().upper())
        datos = self._resumen(envio)
        datos.update(
            cliente={"nombre": envio.cliente.nombre, "email": envio.cliente.email,
                     "telefono": envio.cliente.telefono},
            sucursal_origen=envio.sucursal_origen.nombre,
            asegurado=envio.asegurado,
            poliza=envio.seguro.numero_poliza if envio.seguro else None,
            paquetes=[{"contenido": p.contenido, "peso_kg": str(p.peso_kg),
                       "medidas": f"{p.alto_cm} × {p.ancho_cm} × {p.largo_cm} cm",
                       "peso_facturable_kg": str(p.peso_facturable_kg.quantize(Decimal("0.01"))),
                       "valor_declarado": _monto(p.valor_declarado), "fragil": p.fragil}
                      for p in envio.paquetes],
            costo=self._costo(envio),
            rastreo=[{"hora": r.marca_tiempo.isoformat(timespec="seconds"),
                      "estado": r.estado, "descripcion": r.descripcion,
                      "lugar": r.punto.nombre if r.punto else None,
                      "responsable": r.responsable.nombre if r.responsable else None}
                     for r in envio.rastreo],
            siguientes=[e.value for e in NombreEstado if envio.puede_ir_a(e)],
            notificaciones=[m for d, m in self.correo.enviados
                            if d == envio.cliente.email and envio.numero_guia in m],
        )
        return datos

    # ---- Mover (State + Observer) ----
    def cambiar_estado(self, numero_guia: str, destino: str, descripcion: str = "") -> dict:
        envio = self.gestor.obtener(numero_guia)
        try:
            estado = NombreEstado(destino)
        except ValueError:
            raise DatosInvalidos(f"Estado desconocido: {destino}") from None
        self.gestor.cambiar_estado(numero_guia, estado, descripcion=descripcion,
                                   **self._detalles(envio, estado))
        return self.detalle(numero_guia)

    def simular(self, numero_guia: str) -> dict:
        """Avanza el envío solo, un paso cada PAUSA_SIMULACION_S segundos."""
        envio = self.gestor.obtener(numero_guia)
        meta = self._meta.setdefault(numero_guia, Metadatos(creado=datetime.now()))
        if not meta.simulando and self._pasos_pendientes(envio):
            meta.simulando = True
            tarea = asyncio.get_running_loop().create_task(self._recorrer(envio, meta))
            self._tareas.add(tarea)
            tarea.add_done_callback(self._tareas.discard)
        return self.detalle(numero_guia)

    async def _recorrer(self, envio: Envio, meta: Metadatos) -> None:
        try:
            for destino, texto in self._pasos_pendientes(envio):
                await asyncio.sleep(PAUSA_SIMULACION_S)
                if not envio.puede_ir_a(destino):
                    break
                self.gestor.cambiar_estado(envio.numero_guia, destino, descripcion=texto,
                                           **self._detalles(envio, destino))
        finally:
            meta.simulando = False

    @staticmethod
    def _pasos_pendientes(envio: Envio) -> list[tuple[NombreEstado, str]]:
        pasos = RECORRIDO[envio.tipo]
        hechos = [r.estado for r in envio.rastreo[1:]]
        # Se salta lo que ya recorrió (mismo orden), y se sigue desde ahí.
        i = 0
        for estado in hechos:
            if i < len(pasos) and pasos[i][0].value == estado:
                i += 1
            elif estado != NombreEstado.EN_TRANSITO.value:
                i = len(pasos)  # salió del recorrido normal (p. ej. cancelado)
        return pasos[i:]

    # ---- Monitor del sistema (módulo de respuesta) ----
    def sistema(self) -> dict:
        return {"estadisticas": self.bus.estadisticas, "salud": self.bus.salud(),
                "sms_caido": self.sms.caido, "pantallas": self.transmisor.conectadas,
                "fallidos": [{"guia": f.evento.numero_guia, "suscriptor": f.suscriptor,
                              "estado": f.evento.nuevo.value, "intentos": f.intentos,
                              "motivo": f.motivo,
                              "hora": f.marca_tiempo.isoformat(timespec="seconds")}
                             for f in self.bus.cola_fallidos[-20:]]}

    def tirar_sms(self, caido: bool) -> dict:
        self.sms.caido = caido
        return self.sistema()

    async def reprocesar(self) -> dict:
        entregados = await self.bus.reprocesar_fallidos()
        return {"reprocesados": entregados, **self.sistema()}

    # ---- Apoyo ----
    def _resumen(self, envio: Envio) -> dict:
        meta = self._meta.get(envio.numero_guia)
        return {"guia": envio.numero_guia, "tipo": envio.tipo.value,
                "estado": envio.estado.value, "cliente_nombre": envio.cliente.nombre,
                "origen": envio.sucursal_origen.ciudad,
                "destino": envio.direccion_destino,
                "pais_destino": getattr(envio, "pais_destino", "Honduras"),
                "total": _monto(envio.calcular_costo()),
                "creado": envio.rastreo[0].marca_tiempo.isoformat(timespec="seconds"),
                "ultimo_movimiento": envio.rastreo[-1].marca_tiempo.isoformat(timespec="seconds"),
                "peso_kg": str(envio.peso_facturable_kg.quantize(Decimal("0.01"))),
                "simulando": bool(meta and meta.simulando)}

    @staticmethod
    def _costo(envio: Envio) -> dict:
        return {"moneda": MONEDA,
                "peso_facturable_kg": str(envio.peso_facturable_kg.quantize(Decimal("0.01"))),
                "desglose": [{"concepto": c, "monto": _monto(m)}
                             for c, m in envio.armar_calculadora().desglose()],
                "total": _monto(envio.calcular_costo())}

    @staticmethod
    def _sucursal(id_punto: Any) -> Sucursal:
        for sucursal in SUCURSALES:
            if str(sucursal.id_punto) == str(id_punto):
                return sucursal
        raise DatosInvalidos("Elija la sucursal de origen")

    def _cliente(self, datos: dict) -> Cliente:
        nombre = str(datos.get("nombre") or "").strip()
        email = str(datos.get("email") or "").strip()
        if not nombre:
            raise DatosInvalidos("Escriba el nombre del cliente")
        if "@" not in email:
            raise DatosInvalidos("Escriba un correo válido del cliente")
        return Cliente(id_usuario=next(self._clientes), nombre=nombre, email=email,
                       direccion=str(datos.get("direccion") or ""),
                       telefono=str(datos.get("telefono") or ""))

    @staticmethod
    def _detalles(envio: Envio, destino: NombreEstado) -> dict:
        if destino is NombreEstado.EN_TRANSITO:
            ciudad = envio.sucursal_origen.ciudad
            bodega = next((b for b in BODEGAS if b.ciudad == ciudad), BODEGAS[0])
            return {"punto": bodega}
        if destino in (NombreEstado.EN_REPARTO, NombreEstado.ENTREGADO):
            return {"responsable": REPARTIDOR}
        return {}

    def _cargar_ejemplos(self) -> None:
        """Envíos de ejemplo para que la pantalla no arranque vacía."""
        ahora = datetime.now()
        ejemplos = [
            ({"tipo": "internacional", "sucursal_origen": 1,
              "direccion_destino": "1200 Brickell Ave, Miami, FL", "pais_destino": "Estados Unidos",
              "asegurar": True,
              "cliente": {"nombre": "Ana López", "email": "ana@correo.hn", "telefono": "9999-0000"},
              "paquetes": [{"peso_kg": "3.5", "alto_cm": 20, "ancho_cm": 30, "largo_cm": 40,
                            "contenido": "Café de Marcala", "valor_declarado": 1500},
                           {"peso_kg": 1, "alto_cm": 15, "ancho_cm": 15, "largo_cm": 15,
                            "contenido": "Artesanía de barro", "valor_declarado": 800,
                            "fragil": True}]},
             [NombreEstado.EN_TRANSITO, NombreEstado.RETENIDO_EN_ADUANA]),
            ({"tipo": "nacional", "sucursal_origen": 2,
              "direccion_destino": "Col. Kennedy, Tegucigalpa",
              "cliente": {"nombre": "Carlos Mejía", "email": "carlos@correo.hn",
                          "telefono": "9888-1212"},
              "paquetes": [{"peso_kg": 6, "alto_cm": 30, "ancho_cm": 30, "largo_cm": 30,
                            "contenido": "Repuestos de moto"}]},
             [NombreEstado.EN_TRANSITO, NombreEstado.EN_REPARTO]),
            ({"tipo": "express", "sucursal_origen": 1,
              "direccion_destino": "Barrio La Merced, La Ceiba",
              "cliente": {"nombre": "María Fernanda Reyes", "email": "mafer@correo.hn",
                          "telefono": "3311-4455"},
              "paquetes": [{"peso_kg": "0.8", "alto_cm": 5, "ancho_cm": 25, "largo_cm": 35,
                            "contenido": "Documentos legales"}]},
             []),
            ({"tipo": "nacional", "sucursal_origen": 4,
              "direccion_destino": "Res. Las Colinas, San Pedro Sula", "asegurar": True,
              "cliente": {"nombre": "José Antonio Flores", "email": "jflores@correo.hn",
                          "telefono": "9776-3030"},
              "paquetes": [{"peso_kg": 2, "alto_cm": 20, "ancho_cm": 20, "largo_cm": 20,
                            "contenido": "Teléfono celular", "valor_declarado": 9500,
                            "fragil": True}]},
             [NombreEstado.EN_TRANSITO, NombreEstado.EN_REPARTO, NombreEstado.ENTREGADO]),
        ]
        ejemplos = [(datos, pasos, 9 - n * 2) for n, (datos, pasos) in enumerate(ejemplos)]
        ejemplos = _ejemplos_semana() + ejemplos
        for datos, pasos, horas_atras in ejemplos:
            guia = self.registrar(datos)["guia"]
            envio = self.gestor.obtener(guia)
            inicio = ahora - timedelta(hours=horas_atras)
            # Solo para los ejemplos: se adelanta la hora de recepción para que
            # el rastreo se vea como un recorrido real de varias horas.
            envio._rastreo[0] = replace(envio.rastreo[0], marca_tiempo=inicio)
            self._meta[guia].creado = inicio
            textos: dict[NombreEstado, str] = {}
            for estado_paso, texto in RECORRIDO[envio.tipo]:
                textos.setdefault(estado_paso, texto)  # el primer texto de cada estado
            for i, destino in enumerate(pasos, start=1):
                momento = min(inicio + timedelta(hours=3 * i), ahora - timedelta(minutes=5 * (len(pasos) - i + 1)))
                envio.cambiar_estado(destino, descripcion=textos.get(destino, ""),
                                     momento=momento, **self._detalles(envio, destino))


# Clientes, destinos y contenidos de los envíos de la última semana (datos de ejemplo).
_CLIENTES = [
    ("Daniela Castillo", "dcastillo@correo.hn"), ("Óscar Banegas", "obanegas@correo.hn"),
    ("Karla Zelaya", "kzelaya@correo.hn"), ("Luis Fernando Paz", "lfpaz@correo.hn"),
    ("Gabriela Midence", "gmidence@correo.hn"), ("Roberto Funes", "rfunes@correo.hn"),
    ("Sofía Andino", "sandino@correo.hn"), ("Héctor Bonilla", "hbonilla@correo.hn"),
    ("Valeria Matamoros", "vmatamoros@correo.hn"), ("Marco Antonio Ruiz", "maruiz@correo.hn"),
    ("Paola Cárcamo", "pcarcamo@correo.hn"), ("Iván Rosales", "irosales@correo.hn"),
    ("Nicole Ávila", "navila@correo.hn"), ("Fernando Lagos", "flagos@correo.hn"),
]
_NACIONALES = ["Barrio Guamilito, San Pedro Sula", "Col. Palmira, Tegucigalpa",
               "Barrio El Centro, Juticalpa", "Col. El Sauce, La Ceiba",
               "Barrio San Juan, Comayagua ", "Barrio Mercedes, Santa Rosa de Copán",
               "Col. Las Palmas, Danlí", "West End, Roatán", "Barrio El Centro, Choluteca"]
_INTERNACIONALES = [("4500 Sunset Blvd, Los Ángeles", "Estados Unidos"),
                    ("Calle Gran Vía 28, Madrid", "España"),
                    ("Av. Reforma 222, Ciudad de México", "México"),
                    ("Zona 10, Ciudad de Guatemala", "Guatemala"),
                    ("Av. Central, San José", "Costa Rica"),
                    ("120 King St W, Toronto", "Canadá")]
_CONTENIDOS = [("Café de Marcala", "1.5", 900), ("Puros de Danlí", "0.6", 1200),
               ("Ropa", "2.0", 800), ("Libros", "3.2", 600), ("Repuestos", "4.5", 2500),
               ("Medicamentos", "0.4", 700), ("Artesanía de Valle de Ángeles", "1.2", 1100),
               ("Documentos", "0.3", 0)]


def _ejemplos_semana() -> list[tuple[dict, list[NombreEstado], float]]:
    """Unos 20 envíos repartidos en los últimos 7 días, casi todos ya entregados.

    Son fijos (no aleatorios) para que la pantalla se vea igual en cada demostración.
    """
    E = NombreEstado
    completo = {TipoEnvio.NACIONAL: [E.EN_TRANSITO, E.EN_REPARTO, E.ENTREGADO],
                TipoEnvio.EXPRESS: [E.EN_TRANSITO, E.EN_REPARTO, E.ENTREGADO],
                TipoEnvio.INTERNACIONAL: [E.EN_TRANSITO, E.RETENIDO_EN_ADUANA, E.EN_TRANSITO,
                                          E.EN_REPARTO, E.ENTREGADO]}
    tipos = [TipoEnvio.NACIONAL, TipoEnvio.EXPRESS, TipoEnvio.NACIONAL, TipoEnvio.INTERNACIONAL,
             TipoEnvio.NACIONAL, TipoEnvio.EXPRESS, TipoEnvio.INTERNACIONAL]
    resultado = []
    for n in range(20):
        tipo = tipos[n % len(tipos)]
        nombre, email = _CLIENTES[n % len(_CLIENTES)]
        contenido, peso, valor = _CONTENIDOS[(n * 3) % len(_CONTENIDOS)]
        lado = 15 + (n * 7) % 25
        datos: dict[str, Any] = {
            "tipo": tipo.value, "sucursal_origen": 1 + n % len(SUCURSALES),
            "cliente": {"nombre": nombre, "email": email, "telefono": f"9{n:03d}-{(n * 37) % 10000:04d}"},
            "asegurar": n % 3 == 0 and valor > 0,
            "paquetes": [{"contenido": contenido, "peso_kg": peso, "alto_cm": lado, "ancho_cm": 20,
                          "largo_cm": 30, "valor_declarado": valor or (500 if tipo is TipoEnvio.INTERNACIONAL else 0),
                          "fragil": n % 4 == 1}]}
        if tipo is TipoEnvio.INTERNACIONAL:
            direccion, pais = _INTERNACIONALES[n % len(_INTERNACIONALES)]
            datos.update(direccion_destino=direccion, pais_destino=pais)
        else:
            datos["direccion_destino"] = _NACIONALES[n % len(_NACIONALES)]
        horas_atras = 168 - n * 7.5
        pasos = completo[tipo]
        if n == 15:
            pasos = pasos[:2]           # en reparto (o en aduana si es internacional)
        elif n in (16, 18):
            pasos = []                  # recién recibido en la sucursal
        elif n == 17:
            pasos = pasos[:1]           # todavía en tránsito
        elif n == 19:
            pasos = [E.CANCELADO]       # cancelado por el cliente
        resultado.append((datos, pasos, horas_atras))
    return resultado
