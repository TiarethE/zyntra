import unittest
from decimal import Decimal

from tests.apoyo import SEGURO, creadores, datos_envio, nuevo_envio, paquete
from zyntra.creadores import CLASES_CREADOR
from zyntra.envios import EnvioExpress, EnvioInternacional, EnvioNacional
from zyntra.tarifas import TipoEnvio


class TestFactoryMethod(unittest.TestCase):
    def test_cada_creador_fabrica_su_tipo(self):
        esperado = {TipoEnvio.NACIONAL: EnvioNacional,
                    TipoEnvio.INTERNACIONAL: EnvioInternacional,
                    TipoEnvio.EXPRESS: EnvioExpress}
        for tipo, clase in esperado.items():
            envio = nuevo_envio(tipo)
            self.assertIsInstance(envio, clase)
            self.assertIs(envio.tipo, tipo)

    def test_hay_un_creador_por_tipo(self):
        self.assertEqual(set(CLASES_CREADOR), set(TipoEnvio))

    def test_el_envio_recibe_la_tarifa_de_su_tipo(self):
        envio = nuevo_envio(TipoEnvio.EXPRESS)
        self.assertEqual(envio.tarifa.fija, Decimal(150))

    def test_peso_y_valor_se_suman_entre_paquetes(self):
        envio = nuevo_envio(paquetes=[paquete(peso=2, valor=100), paquete(peso=3, valor=50)])
        self.assertEqual(envio.peso_facturable_kg, Decimal(5))
        self.assertEqual(envio.valor_declarado, Decimal(150))


class TestValidaciones(unittest.TestCase):
    def setUp(self):
        self.nacional = creadores()[TipoEnvio.NACIONAL]
        self.internacional = creadores()[TipoEnvio.INTERNACIONAL]

    def test_guia_con_formato_invalido(self):
        for guia in ("", "123", "ZYN-12"):
            with self.assertRaises(ValueError):
                self.nacional.crear_envio(**datos_envio(guia=guia))

    def test_sin_paquetes(self):
        datos = datos_envio()
        datos["paquetes"] = []
        with self.assertRaises(ValueError):
            self.nacional.crear_envio(**datos)

    def test_seguro_sin_valor_declarado(self):
        with self.assertRaises(ValueError):
            self.nacional.crear_envio(**datos_envio(seguro=SEGURO))

    def test_nacional_no_acepta_pais_destino(self):
        with self.assertRaises(TypeError):
            self.nacional.crear_envio(**datos_envio(pais_destino="Guatemala"))

    def test_internacional_requiere_pais_distinto_de_honduras(self):
        for pais in ("", "Honduras"):
            with self.assertRaises(ValueError):
                self.internacional.crear_envio(
                    **datos_envio(paquetes=[paquete(valor=100)], pais_destino=pais))

    def test_internacional_requiere_valor_en_cada_paquete(self):
        with self.assertRaises(ValueError):
            self.internacional.crear_envio(
                **datos_envio(paquetes=[paquete(valor=100), paquete(valor=0)],
                              pais_destino="México"))

    def test_express_limita_el_peso(self):
        with self.assertRaises(ValueError):
            nuevo_envio(TipoEnvio.EXPRESS, paquetes=[paquete(peso=31)])


if __name__ == "__main__":
    unittest.main()
