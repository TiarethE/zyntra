# Zyntra

Sistema de gestión de envíos de una paquetería con sede en Tegucigalpa, Honduras. Registra envíos nacionales, internacionales y express, calcula su costo en lempiras, controla su ciclo de vida y avisa al cliente cada vez que su paquete cambia de estado.

Proyecto integrador de Ingeniería de Software II, Universidad Anáhuac Mayab.

## Cómo ejecutarlo

Requiere Python 3.11 o superior. No usa librerías externas.

```bash
python -m zyntra.demo        # demostración de punta a punta
python -m unittest -v        # 78 pruebas automáticas
```

## Patrones de diseño

| Patrón | Familia | Archivo | Problema que resuelve |
| --- | --- | --- | --- |
| Factory Method | Creacional | `zyntra/creadores.py` | DT-1, DT-2, DT-6: decisión por tipo repetida, tipos como texto, datos sin validar |
| Decorator | Estructural | `zyntra/costos.py` | DT-4: una sola clase calculaba todo el costo |
| State | Comportamiento | `zyntra/estados.py` | DT-2, DT-3: estados como texto y transiciones con if anidados |
| Observer | Comportamiento | `zyntra/eventos.py` | DT-7: no había forma de avisar los cambios |

DT-5 (tarifas escritas en el código) se resuelve con `zyntra/datos/tarifas.json`.

## Módulo de respuesta (v2.0)

El bus de eventos atiende avisos concurrentes sin bloquear el registro de envíos y sigue funcionando cuando un servicio externo falla.

| Mecanismo | Archivo | Qué garantiza | Issue |
| --- | --- | --- | --- |
| Reintentos con espera exponencial y cola de fallidos | `zyntra/eventos.py` | Un fallo pasajero no pierde el aviso; uno persistente queda para reprocesar | #2 |
| Circuit breaker por suscriptor | `zyntra/circuito.py` | Tras 5 fallos seguidos no se llama al servicio caído durante 30 s | #3 |
| 4 trabajadores con partición por guía | `zyntra/eventos.py` | Avisos en paralelo, en orden para cada envío | #4 |
| Candado por envío y publicación segura entre hilos | `zyntra/gestor.py` | Dos escaneos simultáneos no corrompen el estado | #5 |
| Outbox en disco (JSON Lines) | `zyntra/outbox.py` | Los avisos pendientes sobreviven a un reinicio sin duplicarse | #6 |
| Latencia (promedio, p95, máx.) y `salud()` | `zyntra/eventos.py` | Se mide el tiempo real y se detecta un servicio degradado | #7 |

La sección 6 de `python -m zyntra.demo` muestra las métricas con un servicio caído simulado. Las pruebas del módulo están en `tests/test_respuesta.py`; las de concurrencia se verificaron fallando contra el código anterior antes de aplicar cada cambio.

Límite conocido: como los avisos de un mismo envío se entregan en orden, un servicio caído retrasa los siguientes de ese envío hasta que su circuito se abre (~1.1 s de latencia promedio en la demo).

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
  eventos.py             Observer (bus de eventos) con reintentos, trabajadores y métricas
  circuito.py            Circuit breaker
  outbox.py              Registro de avisos en disco
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
- `v1.0`: versión refactorizada con los cuatro patrones (Primer Parcial).
- `v2.0`: módulo de respuesta en tiempo real y gestión de configuración (Segundo Parcial).

En la v1.0 cada patrón se desarrolló en su propia rama (`feature/...`). Desde la v2.0 cada cambio tiene un issue y un pull request revisado, y GitHub Actions corre las pruebas en Python 3.11 y 3.13. Los cambios están en [CHANGELOG.md](CHANGELOG.md) y el flujo de trabajo en [CONTRIBUTING.md](CONTRIBUTING.md).
