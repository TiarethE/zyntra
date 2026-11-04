"""Comprueba que los diagramas UML de docs/uml coinciden con el código.

Cada clase dibujada debe existir, y cada atributo o método que aparece en
el diagrama debe existir en esa clase. Además, toda clase del paquete
zyntra debe aparecer en al menos un diagrama.
"""

import dataclasses
import importlib
import inspect
import pkgutil
import re
import unittest
from enum import Enum
from pathlib import Path

import zyntra

CARPETA_UML = Path(__file__).resolve().parent.parent / "docs" / "uml"
INICIO_CLASE = re.compile(r'^\s*(?:abstract\s+class|class|enum)\s+(?:"[^"]+"\s+as\s+)?(\w+)')
MIEMBRO = re.compile(r"^\s*[+\-#~]?\s*(?:\{(?:static|abstract)\}\s*)*(\w+)\s*(?:\(|:|$)")
NO_DIBUJADAS = {"demo"}  # módulos que no forman parte del diseño


def clases_del_codigo():
    clases = {}
    for modulo in ["legado.envio_legado"] + [
            m.name for m in pkgutil.walk_packages(zyntra.__path__, "zyntra.")]:
        if modulo.split(".")[-1] in NO_DIBUJADAS:
            continue
        mod = importlib.import_module(modulo)
        for nombre, obj in vars(mod).items():
            if inspect.isclass(obj) and obj.__module__ == modulo:
                clases.setdefault(nombre, []).append(obj)
    return clases


def clases_del_diagrama(texto):
    """Devuelve {clase: [miembros]} de un archivo .puml."""
    resultado, actual = {}, None
    for linea in texto.splitlines():
        if actual is None:
            coincide = INICIO_CLASE.match(linea)
            if coincide:
                nombre = coincide.group(1)
                resultado.setdefault(nombre, [])
                if linea.rstrip().endswith("{"):
                    actual = nombre
        elif linea.strip() == "}":
            actual = None
        elif linea.strip() not in ("", "--", ".."):
            miembro = MIEMBRO.match(linea)
            if miembro:
                resultado[actual].append(miembro.group(1))
    return resultado


def tiene_miembro(clase, nombre):
    if issubclass(clase, Enum):
        return nombre in clase.__members__
    if hasattr(clase, nombre):
        return True
    if dataclasses.is_dataclass(clase) and nombre in {f.name for f in dataclasses.fields(clase)}:
        return True
    for base in clase.__mro__:
        if base is object:
            continue
        try:
            fuente = inspect.getsource(base)
        except (OSError, TypeError):
            continue
        if re.search(rf"self\.{re.escape(nombre)}\b", fuente):
            return True
    return False


class TestDiagramasAlineados(unittest.TestCase):
    def setUp(self):
        self.codigo = clases_del_codigo()
        self.diagramas = {p.name: clases_del_diagrama(p.read_text(encoding="utf-8"))
                          for p in sorted(CARPETA_UML.glob("*.puml"))}

    def test_hay_diagramas(self):
        self.assertGreaterEqual(len(self.diagramas), 8)

    def test_clases_y_miembros_existen_en_el_codigo(self):
        for archivo, clases in self.diagramas.items():
            for nombre, miembros in clases.items():
                with self.subTest(diagrama=archivo, clase=nombre):
                    self.assertIn(nombre, self.codigo, f"{nombre} no existe en el código")
                    candidatas = self.codigo[nombre]
                    if archivo.startswith("01_"):  # el diagrama «antes» es la v0.1
                        candidatas = [c for c in candidatas if c.__module__.startswith("legado")]
                    for miembro in miembros:
                        self.assertTrue(any(tiene_miembro(c, miembro) for c in candidatas),
                                        f"{nombre}.{miembro} no existe en el código")

    def test_toda_clase_del_codigo_aparece_en_un_diagrama(self):
        dibujadas = {nombre for clases in self.diagramas.values() for nombre in clases}
        for nombre, objetos in self.codigo.items():
            if any(o.__module__.startswith("zyntra") for o in objetos):
                with self.subTest(clase=nombre):
                    self.assertIn(nombre, dibujadas)


if __name__ == "__main__":
    unittest.main()
