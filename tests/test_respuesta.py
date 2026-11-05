"""Pruebas del módulo de respuesta (Segundo Parcial)."""

import asyncio
import os
import random
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from tests.apoyo import creadores, datos_envio
from zyntra.creadores import EnvioCreator
from zyntra.circuito import CircuitBreaker, EstadoCircuito as C
from zyntra.estados import EstadoEnvio, NombreEstado as E, TransicionInvalida
from zyntra.eventos import BusEventos, Suscriptor
from zyntra.gestor import GestorEnvios
from zyntra.notificadores import PanelRastreo
from zyntra.outbox import Outbox
from zyntra.tarifas import TipoEnvio


class FallaNVeces(Suscriptor):
    nombre = "falla n veces"

    def __init__(self, fallos):
        self.fallos_restantes = fallos
        self.recibidos = []

    async def notificar(self, evento):
        if self.fallos_restantes:
            self.fallos_restantes -= 1
            raise ConnectionError("servicio no disponible")
        self.recibidos.append(evento)


def gestor_con(bus, guias=("ZYN-00000001",)):
    gestor = GestorEnvios(creadores(), bus)
    for guia in guias:
        gestor.registrar_envio(TipoEnvio.NACIONAL, **datos_envio(guia=guia))
    return gestor


class TestReintentos(unittest.IsolatedAsyncioTestCase):
    """Issue #2: reintentos con espera exponencial y cola de fallidos."""

    async def test_se_entrega_despues_de_dos_fallos(self):
        bus = BusEventos(max_reintentos=3, espera_base=0.01)
        suscriptor = FallaNVeces(2)
        bus.suscribir(suscriptor)
        await bus.iniciar()
        with self.assertLogs("zyntra.eventos", "WARNING") as avisos:
            gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            await bus.detener()

        self.assertEqual(len(suscriptor.recibidos), 1)
        self.assertEqual(bus.reintentos, 2)
        self.assertEqual(bus.fallidos, 0)
        self.assertEqual(len(avisos.output), 2)

    async def test_si_siempre_falla_queda_en_la_cola_de_fallidos(self):
        bus = BusEventos(max_reintentos=2, espera_base=0.01)
        bus.suscribir(FallaNVeces(99))
        await bus.iniciar()
        with self.assertLogs("zyntra.eventos", "WARNING"):
            gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            await bus.detener()

        self.assertEqual(len(bus.cola_fallidos), 1)
        fallido = bus.cola_fallidos[0]
        self.assertEqual(fallido.intentos, 3)
        self.assertEqual(fallido.suscriptor, "falla n veces")
        self.assertIn("ConnectionError", fallido.motivo)
        self.assertIs(fallido.evento.nuevo, E.EN_TRANSITO)

    async def test_la_espera_crece_de_forma_exponencial(self):
        bus = BusEventos(max_reintentos=3, espera_base=0.05)
        bus.suscribir(FallaNVeces(3))
        await bus.iniciar()
        inicio = time.perf_counter()
        with self.assertLogs("zyntra.eventos", "WARNING"):
            gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            await bus.detener()
        # 0.05 + 0.10 + 0.20 = 0.35 s de espera antes del cuarto intento
        self.assertGreaterEqual(time.perf_counter() - inicio, 0.35)

    async def test_los_reintentos_no_retrasan_a_los_demas(self):
        bus = BusEventos(max_reintentos=3, espera_base=0.2)
        panel = PanelRastreo()
        bus.suscribir(FallaNVeces(3))
        bus.suscribir(panel)
        await bus.iniciar()
        with self.assertLogs("zyntra.eventos", "WARNING"):
            gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            await asyncio.sleep(0.05)
            # El panel ya recibió el aviso aunque el otro suscriptor sigue reintentando.
            self.assertIn("ZYN-00000001", panel.ultimo_estado)
            await bus.detener()

    async def test_reprocesar_la_cola_de_fallidos(self):
        bus = BusEventos(max_reintentos=0, espera_base=0.01)
        suscriptor = FallaNVeces(1)
        bus.suscribir(suscriptor)
        await bus.iniciar()
        with self.assertLogs("zyntra.eventos", "WARNING"):
            gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            await bus.detener()
        self.assertEqual(len(bus.cola_fallidos), 1)

        # El servicio se recuperó: el reproceso entrega el aviso pendiente.
        self.assertEqual(await bus.reprocesar_fallidos(), 1)
        self.assertEqual(bus.cola_fallidos, [])
        self.assertEqual(len(suscriptor.recibidos), 1)


class RelojFalso:
    def __init__(self):
        self.ahora = 0.0

    def __call__(self):
        return self.ahora


class TestCircuitBreaker(unittest.TestCase):
    """Issue #3: aislar suscriptores caídos."""

    def setUp(self):
        self.reloj = RelojFalso()
        self.circuito = CircuitBreaker(umbral_fallos=3, tiempo_espera=10, reloj=self.reloj)

    def test_se_abre_tras_n_fallos_seguidos(self):
        for _ in range(2):
            self.circuito.registrar_fallo()
        self.assertIs(self.circuito.estado, C.CERRADO)
        self.circuito.registrar_fallo()
        self.assertIs(self.circuito.estado, C.ABIERTO)
        self.assertFalse(self.circuito.permite_llamada())

    def test_un_exito_reinicia_la_cuenta(self):
        self.circuito.registrar_fallo()
        self.circuito.registrar_fallo()
        self.circuito.registrar_exito()
        self.circuito.registrar_fallo()
        self.assertIs(self.circuito.estado, C.CERRADO)

    def test_tras_la_espera_permite_una_sola_prueba(self):
        for _ in range(3):
            self.circuito.registrar_fallo()
        self.reloj.ahora = 10
        self.assertIs(self.circuito.estado, C.SEMIABIERTO)
        self.assertTrue(self.circuito.permite_llamada())
        self.assertFalse(self.circuito.permite_llamada())

    def test_si_la_prueba_responde_se_cierra(self):
        for _ in range(3):
            self.circuito.registrar_fallo()
        self.reloj.ahora = 10
        self.circuito.permite_llamada()
        self.circuito.registrar_exito()
        self.assertIs(self.circuito.estado, C.CERRADO)
        self.assertEqual(self.circuito.fallos_seguidos, 0)

    def test_si_la_prueba_falla_se_vuelve_a_abrir(self):
        for _ in range(3):
            self.circuito.registrar_fallo()
        self.reloj.ahora = 10
        self.circuito.permite_llamada()
        self.circuito.registrar_fallo()
        self.assertIs(self.circuito.estado, C.ABIERTO)
        self.assertEqual(self.circuito.aperturas, 2)


class TestCircuitBreakerEnElBus(unittest.IsolatedAsyncioTestCase):
    async def test_con_el_circuito_abierto_no_se_llama_al_suscriptor(self):
        # Un solo trabajador: la prueba cuenta llamadas exactas, y con varios
        # trabajadores las entregas que ya estaban en curso cuando el circuito
        # seguía cerrado también llegan al servicio (en Python 3.11 wait_for
        # crea una tarea aparte y las cinco pasan el chequeo antes del primer fallo).
        bus = BusEventos(max_reintentos=0, umbral_circuito=2, espera_circuito=60,
                         trabajadores=1)
        caido = FallaNVeces(99)
        bus.suscribir(caido)
        await bus.iniciar()
        guias = [f"ZYN-0000000{i}" for i in range(1, 6)]
        gestor = gestor_con(bus, guias)
        with self.assertLogs("zyntra.eventos", "WARNING") as avisos:
            for guia in guias:
                gestor.cambiar_estado(guia, E.EN_TRANSITO)
            await bus.detener()

        # Solo los 2 primeros llegaron al servicio; los otros 3 se rechazaron sin llamarlo.
        self.assertEqual(caido.fallos_restantes, 97)
        self.assertEqual(len(avisos.output), 2)
        self.assertEqual(bus.rechazados_por_circuito, 3)
        self.assertEqual(len(bus.cola_fallidos), 5)
        self.assertEqual(bus.cola_fallidos[-1].motivo, "circuito abierto")
        self.assertIs(bus.circuitos["falla n veces"].estado, C.ABIERTO)


class RegistraOrden(Suscriptor):
    nombre = "registra orden"

    def __init__(self, demora_maxima=0.0):
        self.demora_maxima = demora_maxima
        self.por_guia = {}

    async def notificar(self, evento):
        await asyncio.sleep(random.uniform(0, self.demora_maxima))
        self.por_guia.setdefault(evento.numero_guia, []).append(evento.nuevo)


class TestTrabajadoresConcurrentes(unittest.IsolatedAsyncioTestCase):
    """Issue #4: varios trabajadores sin perder el orden de cada envío."""

    RECORRIDO = [E.EN_TRANSITO, E.EN_REPARTO, E.ENTREGADO]

    async def test_cada_envio_recibe_sus_avisos_en_orden(self):
        bus = BusEventos(trabajadores=4)
        orden = RegistraOrden(demora_maxima=0.003)
        bus.suscribir(orden)
        await bus.iniciar()
        guias = [f"ZYN-{i:08d}" for i in range(1, 201)]
        gestor = gestor_con(bus, guias)
        for destino in self.RECORRIDO:
            for guia in guias:
                gestor.cambiar_estado(guia, destino)
        await bus.detener()

        self.assertEqual(len(orden.por_guia), 200)
        for guia in guias:
            self.assertEqual(orden.por_guia[guia], self.RECORRIDO, guia)

    async def test_los_envios_se_reparten_entre_los_trabajadores(self):
        bus = BusEventos(trabajadores=4)
        guias = [f"ZYN-{i:08d}" for i in range(1, 101)]
        gestor_con(bus, guias)
        usadas = {id(bus._cola_de(guia)) for guia in guias}
        self.assertEqual(len(usadas), 4)
        self.assertIs(bus._cola_de(guias[0]), bus._cola_de(guias[0]))

    async def test_cuatro_trabajadores_son_mas_rapidos_que_uno(self):
        async def medir(trabajadores):
            bus = BusEventos(trabajadores=trabajadores)
            bus.suscribir(Demora(0.02))
            await bus.iniciar()
            guias = [f"ZYN-{i:08d}" for i in range(1, 41)]
            gestor = gestor_con(bus, guias)
            inicio = time.perf_counter()
            for guia in guias:
                gestor.cambiar_estado(guia, E.EN_TRANSITO)
            await bus.detener()
            return time.perf_counter() - inicio

        uno, cuatro = await medir(1), await medir(4)
        # 40 avisos × 20 ms: ~0.8 s con uno, ~0.2 s con cuatro.
        self.assertLess(cuatro, uno / 2.5)

    def test_requiere_al_menos_un_trabajador(self):
        with self.assertRaises(ValueError):
            BusEventos(trabajadores=0)


class TestOutbox(unittest.IsolatedAsyncioTestCase):
    """Issue #6: los avisos pendientes sobreviven a un reinicio."""

    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = os.path.join(carpeta.name, "outbox.jsonl")

    def bus_nuevo(self, *suscriptores, **opciones):
        bus = BusEventos(outbox=Outbox(self.ruta), **opciones)
        for suscriptor in suscriptores:
            bus.suscribir(suscriptor)
        return bus

    async def test_un_bus_nuevo_entrega_lo_que_quedo_pendiente(self):
        # El proceso "se cae" antes de que el bus arranque: la cola en memoria se pierde.
        caido = self.bus_nuevo(RegistraOrden())
        gestor = gestor_con(caido)
        for destino in TestTrabajadoresConcurrentes.RECORRIDO:
            gestor.cambiar_estado("ZYN-00000001", destino)
        del caido, gestor

        orden = RegistraOrden()
        bus = self.bus_nuevo(orden)
        await bus.iniciar()
        await bus.detener()
        self.assertEqual(orden.por_guia["ZYN-00000001"], TestTrabajadoresConcurrentes.RECORRIDO)

    async def test_lo_ya_entregado_no_se_vuelve_a_enviar(self):
        primero = RegistraOrden()
        bus = self.bus_nuevo(primero)
        await bus.iniciar()
        gestor = gestor_con(bus)
        gestor.cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
        await bus.detener()
        gestor.cambiar_estado("ZYN-00000001", E.EN_REPARTO)  # queda sin entregar

        segundo = RegistraOrden()
        bus = self.bus_nuevo(segundo)
        await bus.iniciar()
        await bus.detener()
        self.assertEqual(primero.por_guia["ZYN-00000001"], [E.EN_TRANSITO])
        self.assertEqual(segundo.por_guia["ZYN-00000001"], [E.EN_REPARTO])

        # Un tercer arranque ya no tiene nada pendiente.
        tercero = RegistraOrden()
        bus = self.bus_nuevo(tercero)
        await bus.iniciar()
        await bus.detener()
        self.assertEqual(tercero.por_guia, {})

    async def test_solo_se_reenvia_al_suscriptor_que_fallo(self):
        panel = PanelRastreo()
        bus = self.bus_nuevo(FallaNVeces(99), panel, max_reintentos=0)
        await bus.iniciar()
        with self.assertLogs("zyntra.eventos", "WARNING"):
            gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            await bus.detener()
        self.assertEqual(len(bus.cola_fallidos), 1)

        # Al reiniciar, el servicio ya responde; el panel no recibe el aviso dos veces.
        recuperado, panel_nuevo = FallaNVeces(0), PanelRastreo()
        bus = self.bus_nuevo(recuperado, panel_nuevo)
        await bus.iniciar()
        await bus.detener()
        self.assertEqual(len(recuperado.recibidos), 1)
        self.assertEqual(panel_nuevo.ultimo_estado, {})

    async def test_el_evento_recuperado_es_igual_al_original(self):
        bus = self.bus_nuevo(RegistraOrden())
        gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
        (original,) = [e for e, _ in Outbox(self.ruta).pendientes(["registra orden"])]
        self.assertEqual(original.nuevo, E.EN_TRANSITO)
        self.assertEqual(original.numero_guia, "ZYN-00000001")

    async def test_tolera_una_linea_a_medias(self):
        bus = self.bus_nuevo(RegistraOrden())
        gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write('{"tipo": "entregado", "id": ')  # se cayó escribiendo

        orden = RegistraOrden()
        bus = self.bus_nuevo(orden)
        await bus.iniciar()
        await bus.detener()
        self.assertEqual(orden.por_guia["ZYN-00000001"], [E.EN_TRANSITO])

    async def test_al_iniciar_se_compacta_el_archivo(self):
        bus = self.bus_nuevo(RegistraOrden())
        await bus.iniciar()
        gestor = gestor_con(bus, [f"ZYN-{i:08d}" for i in range(1, 21)])
        for i in range(1, 21):
            gestor.cambiar_estado(f"ZYN-{i:08d}", E.EN_TRANSITO)
        await bus.detener()
        with open(self.ruta, encoding="utf-8") as archivo:
            self.assertEqual(len(archivo.readlines()), 40)

        bus = self.bus_nuevo(RegistraOrden())
        await bus.iniciar()
        await bus.detener()
        with open(self.ruta, encoding="utf-8") as archivo:
            self.assertEqual(archivo.read(), "")


class Demora(Suscriptor):
    nombre = "servicio lento"

    def __init__(self, segundos):
        self.segundos = segundos

    async def notificar(self, evento):
        await asyncio.sleep(self.segundos)


def transicion_lenta(segundos=0.002):
    """Simula una validación lenta (p. ej. una consulta a base de datos) para
    que la ventana entre leer el estado y cambiarlo sea visible en la prueba."""
    original = EstadoEnvio.transicionar

    def lenta(self, envio, destino):
        time.sleep(segundos)
        return original(self, envio, destino)

    return mock.patch.object(EstadoEnvio, "transicionar", lenta)


class TestCambiosSimultaneos(unittest.IsolatedAsyncioTestCase):
    """Issue #5: cambios de estado simultáneos sobre el mismo envío."""

    async def test_solo_un_hilo_gana_la_misma_transicion(self):
        gestor = gestor_con(None)
        barrera = threading.Barrier(50)

        def intentar():
            barrera.wait()
            try:
                gestor.cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
                return "ok"
            except TransicionInvalida:
                return "rechazado"

        with transicion_lenta(), ThreadPoolExecutor(max_workers=50) as hilos:
            resultados = list(hilos.map(lambda _: intentar(), range(50)))

        self.assertEqual(resultados.count("ok"), 1)
        self.assertEqual(resultados.count("rechazado"), 49)
        rastreo = gestor.rastrear("ZYN-00000001")
        self.assertEqual(len(rastreo), 2)  # registrado + un solo "en tránsito"

    async def test_hilos_publican_en_el_bus_en_marcha(self):
        bus = BusEventos(trabajadores=4)
        orden = RegistraOrden()
        bus.suscribir(orden)
        await bus.iniciar()
        guias = [f"ZYN-{i:08d}" for i in range(1, 101)]
        gestor = gestor_con(bus, guias)

        def recorrer(guia):
            for destino in TestTrabajadoresConcurrentes.RECORRIDO:
                gestor.cambiar_estado(guia, destino)

        def en_paralelo():
            with ThreadPoolExecutor(max_workers=16) as hilos:
                list(hilos.map(recorrer, guias))

        # Los hilos publican mientras el bucle de eventos sigue entregando.
        await asyncio.to_thread(en_paralelo)
        await asyncio.wait_for(bus.detener(), timeout=5)

        self.assertEqual(bus.descartados, 0)
        for guia in guias:
            self.assertEqual(orden.por_guia[guia], TestTrabajadoresConcurrentes.RECORRIDO, guia)

    async def test_registrar_la_misma_guia_desde_varios_hilos(self):
        gestor = GestorEnvios(creadores(), None)
        barrera = threading.Barrier(20)

        def registrar():
            barrera.wait()
            try:
                gestor.registrar_envio(TipoEnvio.NACIONAL, **datos_envio(guia="ZYN-00000009"))
                return True
            except ValueError:
                return False

        original = EnvioCreator.crear_envio

        def creacion_lenta(self, **datos):
            time.sleep(0.002)
            return original(self, **datos)

        with mock.patch.object(EnvioCreator, "crear_envio", creacion_lenta), \
                ThreadPoolExecutor(max_workers=20) as hilos:
            resultados = list(hilos.map(lambda _: registrar(), range(20)))
        self.assertEqual(resultados.count(True), 1)


if __name__ == "__main__":
    unittest.main()
