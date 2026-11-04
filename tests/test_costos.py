import itertools
import unittest
from decimal import Decimal

from legado.envio_legado import Envio as EnvioLegado
from tests.apoyo import SEGURO, nuevo_envio, paquete
from zyntra.costos import (CostoBase, ManejoFragilDecorator, SeguroDecorator,
                           armar_calculadora)
from zyntra.tarifas import TipoEnvio, cargar_tarifas

TARIFAS = cargar_tarifas()


class TestCostoPorCombinacion(unittest.TestCase):
    """Criterio de aceptación: los costos coinciden con la tabla para todas
    las combinaciones de tipo, seguro y fragilidad."""

    def test_todas_las_combinaciones(self):
        peso, valor = Decimal(4), Decimal(2000)
        for tipo, asegurado, fragil in itertools.product(TipoEnvio, (False, True), (False, True)):
            with self.subTest(tipo=tipo.value, asegurado=asegurado, fragil=fragil):
                t = TARIFAS[tipo]
                esperado = t.fija + t.por_kg * peso
                esperado += t.tasa_seguro * valor if asegurado else 0
                esperado += t.recargo_fragil if fragil else 0
                envio = nuevo_envio(tipo, paquetes=[paquete(peso=peso, valor=valor, fragil=fragil)],
                                    seguro=SEGURO if asegurado else None)
                self.assertEqual(envio.calcular_costo(), esperado)

    def test_ejemplo_del_documento(self):
        # Internacional, 4 kg, valor 2000, asegurado y frágil.
        envio = nuevo_envio(TipoEnvio.INTERNACIONAL, seguro=SEGURO,
                            paquetes=[paquete(peso=4, valor=2000, fragil=True)])
        self.assertEqual(envio.calcular_costo(), Decimal("2370.00"))


class TestDecorator(unittest.TestCase):
    def test_las_capas_se_aplican_solo_cuando_hacen_falta(self):
        simple = armar_calculadora(nuevo_envio())
        self.assertIsInstance(simple, CostoBase)

        completo = armar_calculadora(nuevo_envio(
            paquetes=[paquete(valor=100, fragil=True)], seguro=SEGURO))
        self.assertIsInstance(completo, ManejoFragilDecorator)
        self.assertIsInstance(completo._envuelto, SeguroDecorator)
        self.assertIsInstance(completo._envuelto._envuelto, CostoBase)

    def test_recargo_fragil_por_cada_paquete_fragil(self):
        envio = nuevo_envio(paquetes=[paquete(fragil=True), paquete(fragil=True), paquete()])
        # 80 + 15 × 6 kg + 2 × 50
        self.assertEqual(envio.calcular_costo(), Decimal(270))

    def test_desglose_suma_el_total(self):
        envio = nuevo_envio(paquetes=[paquete(valor=300, fragil=True)], seguro=SEGURO)
        desglose = envio.armar_calculadora().desglose()
        self.assertEqual(sum(monto for _, monto in desglose), envio.calcular_costo())
        self.assertEqual(len(desglose), 4)

    def test_conserva_centavos(self):
        envio = nuevo_envio(paquetes=[paquete(peso=1, valor=10)], seguro=SEGURO)
        self.assertEqual(envio.calcular_costo(), Decimal("95.30"))

    def test_cobra_peso_volumetrico(self):
        envio = nuevo_envio(paquetes=[paquete(peso=1, lado=30)])  # 27 000 cm³ → 5.4 kg
        self.assertEqual(envio.calcular_costo(), Decimal(80) + Decimal(15) * Decimal("5.4"))


class TestMismoResultadoQueV01(unittest.TestCase):
    """La refactorización conserva los costos de la versión original."""

    def test_costos_iguales_a_la_version_original(self):
        for tipo, asegurado, fragil in itertools.product(TipoEnvio, (False, True), (False, True)):
            with self.subTest(tipo=tipo.value, asegurado=asegurado, fragil=fragil):
                legado = EnvioLegado("G", "D", tipo.value, 3, fragil, asegurado, 1000)
                nuevo = nuevo_envio(tipo, paquetes=[paquete(peso=3, valor=1000, fragil=fragil)],
                                    seguro=SEGURO if asegurado else None)
                self.assertEqual(nuevo.calcular_costo(), legado.calcular_costo())


if __name__ == "__main__":
    unittest.main()
