"""Pruebas del módulo de respuesta (Segundo Parcial)."""

import asyncio
import time
import unittest

from tests.apoyo import creadores, datos_envio
from zyntra.circuito import CircuitBreaker, EstadoCircuito as C
from zyntra.estados import NombreEstado as E
from zyntra.eventos import BusEventos, Suscriptor
from zyntra.gestor import GestorEnvios
from zyntra.notificadores import PanelRastreo
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
        bus = BusEventos(max_reintentos=0, umbral_circuito=2, espera_circuito=60)
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


if __name__ == "__main__":
    unittest.main()
