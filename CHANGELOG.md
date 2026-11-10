# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado semántico.

## [Sin publicar]

### Agregado
- Estrategia de ramas y flujo de revisión en `CONTRIBUTING.md`, plantilla de pull request y pruebas automáticas con GitHub Actions (#1).
- Reintentos de notificaciones con espera exponencial y cola de fallidos que se puede reprocesar (#2).
- Circuit breaker por suscriptor: tras 5 fallos seguidos deja de llamar al servicio durante 30 s y luego prueba una llamada (#3).
- Cuatro trabajadores entregan eventos en paralelo; los de una misma guía siempre van al mismo trabajador para conservar su orden (#4).
- Cambios de estado simultáneos sobre un mismo envío desde varios hilos: un candado por guía evita estados corruptos y `publicar()` se puede llamar desde otro hilo (#5).
- Outbox en disco (JSON Lines): los avisos pendientes sobreviven a un reinicio y al arrancar solo se reenvían a los suscriptores que no los recibieron (#6).
- Métricas de latencia de entrega (promedio, p95 y máxima en ms) en `estadisticas` y método `salud()` que reporta «degradado» si algún circuito está abierto; la demostración las imprime (#7).

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
