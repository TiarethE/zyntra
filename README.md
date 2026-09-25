# Zyntra — Sistema de Gestión de Envíos

Proyecto semestral de **Ingeniería de Software II** · Universidad Anáhuac Mayab
Autora: Tiareth Estrada (529611)

Este repositorio documenta la evolución de Zyntra por entregas, cada una marcada con un tag de Git.

| Tag | Descripción |
|---|---|
| `v0.1-legacy` | Prototipo ad hoc original: una sola clase `Envio` con deuda técnica |
| `v1.0` | **Primera entrega:** refactorización con Factory Method, Decorator y State + eventos de tiempo real |

## Qué se refactorizó y con qué patrón

| Code smell en `v0.1-legacy` | Patrón | Clases | Archivo |
|---|---|---|---|
| Condicional sobre el string `tipo`, repetido 3 veces en `calcular_costo()` (CC 12) | **Factory Method** (creacional) | `EnvioCreator`, `Envio{Nacional,Internacional,Express}Creator`, `Envio{Nacional,Internacional,Express}` | `zyntra/fabrica.py`, `zyntra/envios.py` |
| Extras (seguro, manejo frágil) mezclados con el cálculo base | **Decorator** (estructural) | `CalculadoraCosto`, `CostoBase`, `DecoradorCosto`, `SeguroDecorator`, `ManejoFragilDecorator` | `zyntra/costos.py` |
| `if/elif` anidados en `cambiar_estado()` (CC 8) | **State** (comportamiento) | `EstadoEnvio`, `Recolectado`, `EnTransito`, `RetenidoEnAduana`, `Entregado`, `Cancelado` | `zyntra/estados.py` |

**Tiempo real blando:** cada transición publica un `CambioEstado` en un bus asíncrono
(`zyntra/eventos.py`, asyncio). Publicar no bloquea, cada suscriptor tiene timeout y una falla
del notificador no detiene la operación de envíos (degradación controlada).

## Estructura

```
zyntra/
├── legacy/envio_legacy.py     # v0.1-legacy congelado (referencia para pruebas de equivalencia)
├── zyntra/
│   ├── fabrica.py             # Factory Method
│   ├── envios.py              # Productos / Context
│   ├── costos.py              # Decorator
│   ├── estados.py             # State
│   └── eventos.py             # Bus de eventos asíncrono
├── tests/                     # 307 pruebas
├── docs/                      # Documento de diseño (PDF), UML (.puml + .png), guion
├── tools/benchmark.py         # Micro-benchmark legacy vs v1.0
└── demo.py                    # Demostración ejecutable
```

## Uso

```bash
python -m venv .venv && source .venv/bin/activate   # opcional
pip install -r requirements-dev.txt
pytest                      # 307 pruebas
python demo.py              # demostración de los tres patrones y de la degradación controlada
python tools/benchmark.py   # costo en tiempo del diseño
```

```python
from zyntra.fabrica import crear_envio_por_tipo

envio = crear_envio_por_tipo("express", "ZY-003", "CDMX", 2.5,
                             fragil=True, asegurado=True, valor_declarado=1000)
envio.calcular_costo()              # 270
envio.cambiar_estado("En tránsito") # True
envio.cambiar_estado("Cancelado")   # False (transición inválida)
```

Requiere Python 3.10 o superior. No tiene dependencias en tiempo de ejecución.

## Verificación de que el comportamiento no cambió

`tests/test_equivalencia.py` compara el código refactorizado con el legacy sobre 240 combinaciones de
costo (tipo × peso × frágil × asegurado × valor) y sobre **todas** las secuencias de hasta 4 cambios
de estado (incluyendo transiciones inválidas). `tests/test_caracterizacion_legacy.py` fija el
comportamiento original.

## Documentación

* Documento de diseño: [`docs/Zyntra_Documento_de_Diseno.pdf`](docs/Zyntra_Documento_de_Diseno.pdf)
* Diagramas UML (código PlantUML y PNG): [`docs/uml/`](docs/uml)
* Guion de presentación: [`docs/guion_presentacion.md`](docs/guion_presentacion.md)

Para regenerar los diagramas: `java -jar plantuml.jar -tpng docs/uml/*.puml`.

## Flujo de trabajo

Una rama por cambio (`refactor/factory-method`, `refactor/decorator`, `refactor/state`,
`feature/eventos-tiempo-real`, `docs/documentacion`), integradas a `main` con `merge --no-ff`.
Mensajes de commit con formato *Conventional Commits* en español. Ver [`CHANGELOG.md`](CHANGELOG.md).
