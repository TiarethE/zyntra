"""Pruebas de caracterización de la versión v0.1.

Fijan el comportamiento del código original para comprobar que la
refactorización conserva los mismos costos y transiciones.
"""

import unittest

from legado.envio_legado import Envio


class TestLegado(unittest.TestCase):
    def test_costos(self):
        self.assertEqual(Envio("G1", "SPS", "nacional", 2).calcular_costo(), 110)
        self.assertEqual(Envio("G1", "Miami", "internacional", 4, fragil=True,
                               asegurado=True, valor_declarado=2000).calcular_costo(), 2370)
        self.assertEqual(Envio("G1", "SPS", "express", 1, asegurado=True,
                               valor_declarado=500).calcular_costo(), 195)

    def test_trunca_centavos(self):
        # Error del diseño original: int() descarta los centavos.
        envio = Envio("G1", "SPS", "nacional", 1, asegurado=True, valor_declarado=10)
        self.assertEqual(envio.calcular_costo(), 95)  # el valor real es 95.30

    def test_tipo_mal_escrito_no_falla(self):
        # DT-2: un error de escritura en el tipo da costo 0 sin avisar.
        self.assertEqual(Envio("G1", "SPS", "Nacional", 2).calcular_costo(), 0)

    def test_transiciones(self):
        envio = Envio("G1", "SPS", "nacional", 2)
        self.assertFalse(envio.cambiar_estado("Entregado"))
        self.assertTrue(envio.cambiar_estado("En transito"))
        self.assertFalse(envio.cambiar_estado("Retenido en aduana"))
        self.assertTrue(envio.cambiar_estado("En reparto"))
        self.assertTrue(envio.cambiar_estado("Entregado"))

    def test_acepta_peso_negativo(self):
        # DT-6: no hay validación de entrada.
        self.assertEqual(Envio("", "SPS", "nacional", -3).peso, -3)


if __name__ == "__main__":
    unittest.main()
