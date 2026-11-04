import asyncio
import time
import unittest

from tests.apoyo import creadores, datos_envio
from zyntra.estados import NombreEstado as E
from zyntra.eventos import BusEventos, Suscriptor
from zyntra.gestor import GestorEnvios
from zyntra.notificadores import NotificadorCliente, PanelRastreo
from zyntra.tarifas import TipoEnvio


class Falla(Suscriptor):
    nombre = "suscriptor que falla"

    async def notificar(self, evento):
        raise RuntimeError("servicio caído")


class Lento(Suscriptor):
    nombre = "suscriptor lento"

    async def notificar(self, evento):
        await asyncio.sleep(10)


def gestor_con(bus):
    gestor = GestorEnvios(creadores(), bus)
    gestor.registrar_envio(TipoEnvio.NACIONAL, **datos_envio())
    return gestor


class TestObserver(unittest.IsolatedAsyncioTestCase):
    async def test_cada_cambio_llega_a_todos_los_suscriptores(self):
        bus = BusEventos()
        notificador, panel = NotificadorCliente(), PanelRastreo()
        bus.suscribir(notificador)
        bus.suscribir(panel)
        await bus.iniciar()
        gestor = gestor_con(bus)

        gestor.cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
        gestor.cambiar_estado("ZYN-00000001", E.EN_REPARTO)
        await bus.detener()

        self.assertEqual(len(notificador.enviados), 2)
        self.assertEqual(notificador.enviados[0][0], "ana@correo.hn")
        self.assertIs(panel.ultimo_estado["ZYN-00000001"].nuevo, E.EN_REPARTO)
        self.assertEqual(bus.estadisticas["entregados"], 4)

    async def test_un_suscriptor_que_falla_no_afecta_a_los_demas(self):
        bus = BusEventos()
        panel = PanelRastreo()
        bus.suscribir(Falla())
        bus.suscribir(panel)
        await bus.iniciar()
        with self.assertLogs("zyntra.eventos", "WARNING"):
            gestor_con(bus).cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            await bus.detener()

        self.assertIn("ZYN-00000001", panel.ultimo_estado)
        self.assertEqual(bus.fallidos, 1)
        self.assertEqual(bus.entregados, 1)

    async def test_suscriptor_lento_se_corta_por_tiempo_limite(self):
        bus = BusEventos(tiempo_limite=0.05)
        panel = PanelRastreo()
        bus.suscribir(Lento())
        bus.suscribir(panel)
        await bus.iniciar()
        gestor = gestor_con(bus)

        with self.assertLogs("zyntra.eventos", "WARNING"):
            inicio = time.perf_counter()
            gestor.cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            duracion = time.perf_counter() - inicio
            await bus.detener()

        # Criterio de aceptación: el cambio de estado no espera al notificador.
        self.assertLess(duracion, 0.01)
        self.assertIs(gestor.obtener("ZYN-00000001").estado, E.EN_TRANSITO)
        self.assertEqual(bus.fallidos, 1)
        self.assertIn("ZYN-00000001", panel.ultimo_estado)

    async def test_cola_llena_descarta_avisos_pero_no_rastreo(self):
        bus = BusEventos(capacidad=1)   # sin iniciar: la cola no se vacía
        gestor = gestor_con(bus)
        with self.assertLogs("zyntra.eventos", "WARNING"):
            gestor.cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
            gestor.cambiar_estado("ZYN-00000001", E.EN_REPARTO)
            gestor.cambiar_estado("ZYN-00000001", E.ENTREGADO)

        self.assertEqual(bus.descartados, 2)
        # Criterio de aceptación: cada cambio deja su registro de rastreo.
        self.assertEqual(len(gestor.rastrear("ZYN-00000001")), 4)


class TestGestor(unittest.TestCase):
    def test_no_permite_guias_repetidas(self):
        gestor = gestor_con(None)
        with self.assertRaises(ValueError):
            gestor.registrar_envio(TipoEnvio.NACIONAL, **datos_envio())

    def test_funciona_sin_bus(self):
        gestor = gestor_con(None)
        gestor.cambiar_estado("ZYN-00000001", E.CANCELADO)
        self.assertIs(gestor.obtener("ZYN-00000001").estado, E.CANCELADO)


if __name__ == "__main__":
    unittest.main()
