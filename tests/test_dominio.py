import unittest
from decimal import Decimal

from zyntra.dominio import Cliente, Empleado, Paquete, Rol, Sucursal
from zyntra.tarifas import Tarifa, TipoEnvio, cargar_tarifas


def paquete(**cambios):
    datos = dict(peso_kg=Decimal(2), alto_cm=Decimal(10), ancho_cm=Decimal(10),
                 largo_cm=Decimal(10), contenido="Libros")
    datos.update(cambios)
    return Paquete(**datos)


class TestPaquete(unittest.TestCase):
    def test_rechaza_peso_negativo_o_cero(self):
        for peso in (Decimal(0), Decimal(-1)):
            with self.assertRaises(ValueError):
                paquete(peso_kg=peso)

    def test_rechaza_valor_declarado_negativo(self):
        with self.assertRaises(ValueError):
            paquete(valor_declarado=Decimal(-5))

    def test_rechaza_contenido_vacio(self):
        with self.assertRaises(ValueError):
            paquete(contenido="  ")

    def test_peso_facturable_usa_el_volumetrico_si_es_mayor(self):
        caja_grande = paquete(peso_kg=Decimal(1), alto_cm=Decimal(50),
                              ancho_cm=Decimal(40), largo_cm=Decimal(30))
        self.assertEqual(caja_grande.peso_volumetrico_kg, Decimal(12))
        self.assertEqual(caja_grande.peso_facturable_kg, Decimal(12))

    def test_peso_facturable_usa_el_real_si_es_mayor(self):
        self.assertEqual(paquete().peso_facturable_kg, Decimal(2))


class TestUsuarios(unittest.TestCase):
    def test_autenticacion(self):
        cliente = Cliente(id_usuario=1, nombre="Ana", email="ana@correo.hn",
                          direccion="Col. Palmira", telefono="9999-0000")
        cliente.establecer_contrasena("secreta")
        self.assertTrue(cliente.autenticar("secreta"))
        self.assertFalse(cliente.autenticar("otra"))
        self.assertIs(cliente.rol, Rol.CLIENTE)

    def test_empleado_no_puede_ser_cliente(self):
        sucursal = Sucursal(id_punto=1, nombre="Centro", direccion="Av. Cervantes",
                            ciudad="Tegucigalpa")
        with self.assertRaises(ValueError):
            Empleado(id_usuario=2, nombre="Luis", email="luis@zyntra.hn",
                     sucursal=sucursal, rol=Rol.CLIENTE)


class TestTarifas(unittest.TestCase):
    def test_hay_tarifa_para_cada_tipo(self):
        tarifas = cargar_tarifas()
        self.assertEqual(set(tarifas), set(TipoEnvio))
        self.assertEqual(tarifas[TipoEnvio.NACIONAL],
                         Tarifa(Decimal(80), Decimal(15), Decimal("0.03"), Decimal(50)))


if __name__ == "__main__":
    unittest.main()
