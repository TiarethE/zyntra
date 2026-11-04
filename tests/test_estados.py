import itertools
import unittest

from tests.apoyo import SUCURSAL, nuevo_envio
from zyntra.estados import CLASES_ESTADO, NombreEstado as E, TransicionInvalida
from zyntra.tarifas import TipoEnvio

# Transiciones permitidas según el diagrama de estados.
PERMITIDAS = {
    (E.REGISTRADO, E.EN_TRANSITO), (E.REGISTRADO, E.CANCELADO),
    (E.EN_TRANSITO, E.EN_REPARTO), (E.EN_TRANSITO, E.RETENIDO_EN_ADUANA),
    (E.RETENIDO_EN_ADUANA, E.EN_TRANSITO),
    (E.EN_REPARTO, E.ENTREGADO),
}


class TestState(unittest.TestCase):
    def test_empieza_registrado_con_un_registro_de_rastreo(self):
        envio = nuevo_envio()
        self.assertIs(envio.estado, E.REGISTRADO)
        self.assertEqual(len(envio.rastreo), 1)
        self.assertIs(envio.rastreo[0].punto, SUCURSAL)

    def test_solo_se_permiten_las_transiciones_del_diagrama(self):
        envio = nuevo_envio(TipoEnvio.INTERNACIONAL)
        for origen, clase in CLASES_ESTADO.items():
            for destino in E:
                with self.subTest(origen=origen.value, destino=destino.value):
                    self.assertEqual(clase().puede_ir_a(envio, destino),
                                     (origen, destino) in PERMITIDAS)

    def test_recorrido_completo(self):
        envio = nuevo_envio()
        for destino in (E.EN_TRANSITO, E.EN_REPARTO, E.ENTREGADO):
            envio.cambiar_estado(destino)
        self.assertIs(envio.estado, E.ENTREGADO)
        self.assertEqual([r.estado for r in envio.rastreo],
                         ["Registrado", "En tránsito", "En reparto", "Entregado"])

    def test_transicion_invalida_lanza_error_y_no_cambia_nada(self):
        envio = nuevo_envio()
        with self.assertRaises(TransicionInvalida):
            envio.cambiar_estado(E.ENTREGADO)
        self.assertIs(envio.estado, E.REGISTRADO)
        self.assertEqual(len(envio.rastreo), 1)

    def test_entregado_y_cancelado_son_finales(self):
        for nombre in (E.ENTREGADO, E.CANCELADO):
            self.assertTrue(CLASES_ESTADO[nombre]().es_final)

    def test_aduana_solo_para_internacionales(self):
        for tipo in (TipoEnvio.NACIONAL, TipoEnvio.EXPRESS):
            envio = nuevo_envio(tipo)
            envio.cambiar_estado(E.EN_TRANSITO)
            with self.assertRaises(TransicionInvalida):
                envio.cambiar_estado(E.RETENIDO_EN_ADUANA)

        internacional = nuevo_envio(TipoEnvio.INTERNACIONAL)
        internacional.cambiar_estado(E.EN_TRANSITO)
        internacional.cambiar_estado(E.RETENIDO_EN_ADUANA)
        internacional.cambiar_estado(E.EN_TRANSITO, descripcion="Liberado por aduana")
        self.assertIs(internacional.estado, E.EN_TRANSITO)


class TestMismasTransicionesQueV01(unittest.TestCase):
    """La refactorización conserva las transiciones de la versión original."""

    def test_mismas_transiciones(self):
        from legado.envio_legado import Envio as EnvioLegado
        texto = {e: e.value.replace("á", "a") for e in E}
        for tipo in TipoEnvio:
            for origen, destino in itertools.product(E, E):
                with self.subTest(tipo=tipo.value, origen=origen.value, destino=destino.value):
                    legado = EnvioLegado("G", "D", tipo.value, 1)
                    legado.estado = texto[origen]
                    nuevo = nuevo_envio(tipo)
                    self.assertEqual(CLASES_ESTADO[origen]().puede_ir_a(nuevo, destino),
                                     legado.cambiar_estado(texto[destino]))


if __name__ == "__main__":
    unittest.main()
