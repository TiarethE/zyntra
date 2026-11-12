# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado semántico.

## [Sin publicar]

### Cambiado
- Interfaz web rehecha: barra lateral con secciones, panel con indicadores y gráficas de la última semana, tabla de envíos con filtros y detalle en panel lateral, nuevo envío en 5 pasos con etiqueta imprimible (código de barras Code 39), monitor de latencia en vivo, buscador rápido (`Ctrl K`), campana de movimientos y modo oscuro. 24 envíos de ejemplo repartidos en 7 días (#24).
- Interfaz web: logo nuevo (la Z es una ruta que termina en una estrella de la bandera), tipografía Archivo incluida en el proyecto, mapa de Honduras con los envíos en camino, ilustraciones de vehículos por tipo de envío, caja en perspectiva que cambia con las medidas, vehículo que avanza en el rastreo, contadores animados y cinco estrellas al entregar un envío. Respeta la opción de reducir movimiento del sistema (#22).

### Agregado
- Interfaz web (`python -m interfaz`, FastAPI): panel de envíos, nuevo envío con cotización en vivo, rastreo, detalle con cambios de estado y simulación de recorrido, y monitor del módulo de respuesta con simulación de caída del servicio de SMS (#20).
- Suscriptor `TransmisorEnVivo`: reenvía cada cambio de estado a las pantallas abiertas por WebSocket.
- `GestorEnvios.listar()` para mostrar todos los envíos.
- `requirements.txt` (solo para la interfaz) y 12 pruebas nuevas en `tests/test_interfaz.py`; GitHub Actions instala las dependencias.

## [2.0.0] - 2026-11-10

Segundo Parcial: módulo de respuesta en tiempo real y gestión de configuración.

### Agregado
- Estrategia de ramas y flujo de revisión en `CONTRIBUTING.md`, plantilla de pull request y pruebas automáticas con GitHub Actions (#1).
- Reintentos de notificaciones con espera exponencial y cola de fallidos que se puede reprocesar (#2).
- Circuit breaker por suscriptor: tras 5 fallos seguidos deja de llamar al servicio durante 30 s y luego prueba una llamada (#3).
- Cuatro trabajadores entregan eventos en paralelo; los de una misma guía siempre van al mismo trabajador para conservar su orden (#4).
- Cambios de estado simultáneos sobre un mismo envío desde varios hilos: un candado por guía evita estados corruptos y `publicar()` se puede llamar desde otro hilo (#5).
- Outbox en disco (JSON Lines): los avisos pendientes sobreviven a un reinicio y al arrancar solo se reenvían a los suscriptores que no los recibieron (#6).
- Métricas de latencia de entrega (promedio, p95 y máxima en ms) en `estadisticas` y método `salud()` que reporta «degradado» si algún circuito está abierto; la demostración las imprime (#7).
- Regla para pull requests apilados en `CONTRIBUTING.md` (#16).

### Cambiado
- `CambioEstado` tiene un `id` único, que usa el outbox para anotar entregas (#6).
- 78 pruebas automáticas, que corren en Python 3.11 y 3.13.

### Corregido
- La prueba del circuit breaker en el bus fallaba en Python 3.11 con varios trabajadores; ahora fija un trabajador porque cuenta llamadas exactas (#4, commit 396794f).
- Los PR apilados #8 a #14 se unieron de arriba hacia abajo y el módulo no llegó a `main`; los issues #2 a #7 se reabrieron y el PR #15 lo integró (#16 agrega la regla para que no se repita).

## [1.0.0] - 2026-11-04

### Agregado
- Clases del dominio: Usuario, Cliente, Empleado con roles, Paquete, Seguro, RegistroRastreo, ServicioExterno, Sucursal, Bodega y Vehiculo.
- Tarifas en `zyntra/datos/tarifas.json`, en lempiras (HNL), con `Decimal`.
- Factory Method: un creador por tipo de envío que valida los datos antes de crearlo.
- Decorator: costo base más capas de seguro y manejo frágil.
- State: una clase por estado del envío, incluido «Retenido en aduana» solo para internacionales.
- Observer: bus de eventos asíncrono con cola limitada y tiempo límite por suscriptor.
- GestorEnvios como punto de entrada que une los patrones.
- Demostración ejecutable y 48 pruebas automáticas.
- Diagramas UML en `docs/uml` (antes, dominio, cada patrón, estados, secuencia, después y arquitectura) y una prueba que verifica que coinciden con el código.

### Cambiado
- La clase original se movió a `legado/` y sus pruebas de caracterización confirman que la v1.0 da los mismos costos y transiciones.
- El peso del envío es la suma de sus paquetes y se cobra el peso volumétrico cuando es mayor.
- El recargo frágil se cobra por cada paquete frágil.

### Corregido
- El costo ya no pierde los centavos (la v0.1 los truncaba con `int`).
- Un tipo o estado mal escrito ya no pasa en silencio: son enums.
- No se pueden crear envíos con peso negativo, sin paquetes o sin número de guía.

## [0.1.0] - 2026-11-04

### Agregado
- Versión inicial: clase `Envio` con datos, cálculo de costo y cambios de estado.
