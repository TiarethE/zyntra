"""Pruebas de la interfaz web: la API y el transmisor en vivo.

Las de la API necesitan FastAPI (pip install -r requirements.txt); si no está
instalado se saltan, porque el núcleo de zyntra no depende de librerías externas.
"""

import asyncio
import time
import unittest

from tests.apoyo import creadores, datos_envio
from zyntra.estados import NombreEstado as E
from zyntra.eventos import BusEventos
from zyntra.gestor import GestorEnvios
from zyntra.notificadores import TransmisorEnVivo
from zyntra.tarifas import TipoEnvio

try:
    from fastapi.testclient import TestClient

    from interfaz import servicio as modulo_servicio
    from interfaz.app import crear_app
    HAY_FASTAPI = True
except ImportError:  # pragma: no cover
    HAY_FASTAPI = False


class TestTransmisorEnVivo(unittest.IsolatedAsyncioTestCase):
    async def test_cada_pantalla_conectada_recibe_el_cambio(self):
        bus, transmisor = BusEventos(), TransmisorEnVivo()
        bus.suscribir(transmisor)
        await bus.iniciar()
        pantalla_1, pantalla_2 = transmisor.conectar(), transmisor.conectar()
        gestor = GestorEnvios(creadores(), bus)
        gestor.registrar_envio(TipoEnvio.NACIONAL, **datos_envio())
        gestor.cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
        await bus.detener()
        for pantalla in (pantalla_1, pantalla_2):
            self.assertEqual(pantalla.get_nowait().nuevo, E.EN_TRANSITO)

    async def test_pantalla_desconectada_ya_no_recibe(self):
        transmisor = TransmisorEnVivo()
        pantalla = transmisor.conectar()
        transmisor.desconectar(pantalla)
        self.assertEqual(transmisor.conectadas, 0)

    async def test_pantalla_llena_no_frena_a_las_demas(self):
        bus, transmisor = BusEventos(), TransmisorEnVivo()
        transmisor.CAPACIDAD_POR_PANTALLA = 1
        bus.suscribir(transmisor)
        await bus.iniciar()
        lenta, rapida = transmisor.conectar(), transmisor.conectar()
        gestor = GestorEnvios(creadores(), bus)
        gestor.registrar_envio(TipoEnvio.NACIONAL, **datos_envio())
        gestor.cambiar_estado("ZYN-00000001", E.EN_TRANSITO)
        await bus.detener()
        rapida.get_nowait()
        await bus.iniciar()
        gestor.cambiar_estado("ZYN-00000001", E.EN_REPARTO)
        await bus.detener()
        self.assertEqual(rapida.get_nowait().nuevo, E.EN_REPARTO)
        self.assertEqual(lenta.qsize(), 1)
        self.assertEqual(transmisor.omitidos, 1)
        self.assertEqual(bus.estadisticas["fallidos"], 0)


class TestListar(unittest.TestCase):
    def test_lista_del_mas_reciente_al_mas_antiguo(self):
        gestor = GestorEnvios(creadores())
        gestor.registrar_envio(TipoEnvio.NACIONAL, **datos_envio(guia="ZYN-00000001"))
        gestor.registrar_envio(TipoEnvio.NACIONAL, **datos_envio(guia="ZYN-00000002"))
        self.assertEqual([e.numero_guia for e in gestor.listar()],
                         ["ZYN-00000002", "ZYN-00000001"])


PAQUETE = {"contenido": "Café", "peso_kg": "2", "alto_cm": 10, "ancho_cm": 10, "largo_cm": 10}


def envio_nacional(**cambios):
    return {"tipo": "nacional", "sucursal_origen": 1, "direccion_destino": "Col. Kennedy",
            "cliente": {"nombre": "Ana López", "email": "ana@correo.hn"},
            "paquetes": [PAQUETE], **cambios}


@unittest.skipUnless(HAY_FASTAPI, "requiere FastAPI: pip install -r requirements.txt")
class TestApi(unittest.TestCase):
    def setUp(self):
        self.cliente = TestClient(crear_app(con_ejemplos=False))
        self.cliente.__enter__()  # arranca el bus de eventos

    def tearDown(self):
        self.cliente.__exit__(None, None, None)

    def test_la_pagina_principal_carga(self):
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Zyntra", respuesta.text)

    def test_los_archivos_de_la_pagina_se_sirven_sin_internet(self):
        for ruta in ("/estatico/app.js", "/estatico/mapa.js", "/estatico/app.css",
                     "/estatico/logo.svg", "/estatico/fuentes/archivo.woff2"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.cliente.get(ruta).status_code, 200)
        self.assertNotIn("https://", self.cliente.get("/").text)

    def test_cotizar_usa_las_tarifas_y_los_decoradores(self):
        respuesta = self.cliente.post("/api/cotizar", json=envio_nacional(
            asegurar=True, paquetes=[{**PAQUETE, "valor_declarado": 1000, "fragil": True}]))
        self.assertEqual(respuesta.status_code, 200)
        # 80 fijo + 15 × 2 kg + 3 % de 1000 + 50 por frágil
        self.assertEqual(respuesta.json()["total"], "190.00")
        self.assertEqual(len(respuesta.json()["desglose"]), 4)
        self.assertEqual(self.cliente.get("/api/envios").json(), [])  # no registra nada

    def test_reglas_del_dominio_llegan_como_error_legible(self):
        casos = [
            (envio_nacional(tipo="express", paquetes=[{**PAQUETE, "peso_kg": 31}]), "30 kg"),
            (envio_nacional(tipo="internacional", pais_destino="Honduras"), "nacional"),
            (envio_nacional(paquetes=[{**PAQUETE, "peso_kg": "abc"}]), "número"),
            (envio_nacional(paquetes=[]), "al menos un paquete"),
        ]
        for datos, texto in casos:
            with self.subTest(texto=texto):
                respuesta = self.cliente.post("/api/cotizar", json=datos)
                self.assertEqual(respuesta.status_code, 422)
                self.assertIn(texto, respuesta.json()["error"])

    def test_registrar_mover_y_rastrear(self):
        creado = self.cliente.post("/api/envios", json=envio_nacional())
        self.assertEqual(creado.status_code, 201)
        guia = creado.json()["guia"]
        self.assertRegex(guia, r"^ZYN-\d{8}$")
        self.assertEqual(creado.json()["siguientes"], ["En tránsito", "Cancelado"])

        movido = self.cliente.post(f"/api/envios/{guia}/estado", json={"destino": "En tránsito"})
        self.assertEqual(movido.json()["estado"], "En tránsito")
        # Un nacional no puede ir a aduana: lo decide el estado EnTransito.
        self.assertNotIn("Retenido en aduana", movido.json()["siguientes"])
        rechazo = self.cliente.post(f"/api/envios/{guia}/estado",
                                    json={"destino": "Retenido en aduana"})
        self.assertEqual(rechazo.status_code, 409)

        detalle = self._esperar(guia, lambda d: d["notificaciones"])
        self.assertEqual([r["estado"] for r in detalle["rastreo"]], ["Registrado", "En tránsito"])
        self.assertIn("En tránsito", detalle["notificaciones"][0])

    def test_guia_inexistente_da_404(self):
        self.assertEqual(self.cliente.get("/api/envios/ZYN-99999999").status_code, 404)

    def test_el_websocket_recibe_los_cambios_en_vivo(self):
        guia = self.cliente.post("/api/envios", json=envio_nacional()).json()["guia"]
        with self.cliente.websocket_connect("/ws") as ws:
            self._esperar_pantalla()
            self.cliente.post(f"/api/envios/{guia}/estado", json={"destino": "En tránsito"})
            mensaje = ws.receive_json()
        self.assertEqual((mensaje["guia"], mensaje["nuevo"]), (guia, "En tránsito"))

    def test_simular_recorre_el_envio_hasta_entregarlo(self):
        modulo_servicio.PAUSA_SIMULACION_S, anterior = 0.01, modulo_servicio.PAUSA_SIMULACION_S
        self.addCleanup(setattr, modulo_servicio, "PAUSA_SIMULACION_S", anterior)
        guia = self.cliente.post("/api/envios", json=envio_nacional(
            tipo="internacional", pais_destino="Canadá",
            paquetes=[{**PAQUETE, "valor_declarado": 500}])).json()["guia"]
        self.cliente.post(f"/api/envios/{guia}/simular")
        detalle = self._esperar(guia, lambda d: d["estado"] == "Entregado")
        self.assertEqual([r["estado"] for r in detalle["rastreo"]],
                         ["Registrado", "En tránsito", "Retenido en aduana", "En tránsito",
                          "En reparto", "Entregado"])

    def test_caida_del_sms_no_afecta_al_correo(self):
        self.cliente.post("/api/sistema/sms", json={"caido": True})
        guia = self.cliente.post("/api/envios", json=envio_nacional()).json()["guia"]
        self.cliente.post(f"/api/envios/{guia}/estado", json={"destino": "En tránsito"})
        detalle = self._esperar(guia, lambda d: d["notificaciones"])
        self.assertEqual(len(detalle["notificaciones"]), 1)
        sistema = self._esperar_sistema(lambda s: s["estadisticas"]["en_cola_fallidos"])
        self.assertEqual(sistema["fallidos"][0]["suscriptor"], "notificador SMS")

        self.cliente.post("/api/sistema/sms", json={"caido": False})
        reproceso = self.cliente.post("/api/sistema/reprocesar").json()
        self.assertEqual(reproceso["reprocesados"], 1)
        self.assertEqual(reproceso["estadisticas"]["en_cola_fallidos"], 0)

    # ---- apoyo ----
    def _esperar(self, guia, condicion, limite=5.0):
        fin = time.monotonic() + limite
        while True:
            detalle = self.cliente.get(f"/api/envios/{guia}").json()
            if condicion(detalle) or time.monotonic() > fin:
                return detalle
            time.sleep(0.02)

    def _esperar_sistema(self, condicion, limite=5.0):
        fin = time.monotonic() + limite
        while True:
            sistema = self.cliente.get("/api/sistema").json()
            if condicion(sistema) or time.monotonic() > fin:
                return sistema
            time.sleep(0.02)

    def _esperar_pantalla(self, limite=5.0):
        fin = time.monotonic() + limite
        while self.cliente.get("/api/sistema").json()["pantallas"] == 0:
            if time.monotonic() > fin:
                self.fail("La pantalla no se conectó")
            time.sleep(0.02)


if __name__ == "__main__":
    unittest.main()
