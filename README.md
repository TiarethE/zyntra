# Zyntra

Sistema de gestión de envíos de una paquetería con sede en Tegucigalpa, Honduras. Registra envíos nacionales, internacionales y express, calcula su costo en lempiras, controla su ciclo de vida y avisa al cliente cada vez que su paquete cambia de estado.

Proyecto integrador de Ingeniería de Software II, Universidad Anáhuac Mayab.

## Cómo ejecutarlo

Requiere Python 3.11 o superior. No usa librerías externas.

```bash
python -m zyntra.demo        # demostración de punta a punta
python -m unittest -v        # 48 pruebas automáticas
```

## Patrones de diseño

| Patrón | Familia | Archivo | Problema que resuelve |
| --- | --- | --- | --- |
| Factory Method | Creacional | `zyntra/creadores.py` | DT-1, DT-2, DT-6: decisión por tipo repetida, tipos como texto, datos sin validar |
| Decorator | Estructural | `zyntra/costos.py` | DT-4: una sola clase calculaba todo el costo |
| State | Comportamiento | `zyntra/estados.py` | DT-2, DT-3: estados como texto y transiciones con if anidados |
| Observer | Comportamiento | `zyntra/eventos.py` | DT-7: no había forma de avisar los cambios |

DT-5 (tarifas escritas en el código) se resuelve con `zyntra/datos/tarifas.json`.

## Estructura

```
legado/envio_legado.py   Versión original (v0.1), conservada para comparar
zyntra/
  dominio/               Usuarios, paquetes, puntos logísticos, seguro, rastreo
  tarifas.py             TipoEnvio y carga de tarifas
  envios.py              Envio y sus tres tipos
  creadores.py           Factory Method
  costos.py              Decorator
  estados.py             State
  eventos.py             Observer (bus de eventos)
  notificadores.py       Observadores concretos
  gestor.py              Capa de aplicación que une los patrones
  demo.py                Demostración
tests/                   Pruebas automáticas
docs/uml/                Diagramas UML (PlantUML) e imágenes en docs/uml/img
```

## Diagramas

Los diagramas de `docs/uml` se escribieron a partir del código. La prueba `tests/test_diagramas.py` comprueba que cada clase, atributo y método dibujado existe en el código, y que toda clase de `zyntra` aparece en algún diagrama. Si el código cambia y el diagrama no, la prueba falla.

## Versiones

- `v0.1`: versión de partida, una sola clase `Envio`.
- `v1.0`: versión refactorizada con los cuatro patrones.

Cada patrón se desarrolló en su propia rama (`feature/...`) y se unió a `main` con sus pruebas pasando. Los cambios están en [CHANGELOG.md](CHANGELOG.md) y el flujo de trabajo en [CONTRIBUTING.md](CONTRIBUTING.md).
