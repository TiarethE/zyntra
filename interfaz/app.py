"""API web de Zyntra (FastAPI).

Rutas:
  GET  /                              la aplicación (HTML)
  GET  /api/catalogo                  sucursales, tipos de envío y tarifas
  POST /api/cotizar                   costo con desglose, sin registrar
  GET  /api/envios                    lista de envíos
  POST /api/envios                    registra un envío
  GET  /api/envios/{guia}             detalle, rastreo y notificaciones
  POST /api/envios/{guia}/estado      cambia el estado (State)
  POST /api/envios/{guia}/simular     avanza el envío solo, paso a paso
  GET  /api/sistema                   métricas y salud del bus de eventos
  POST /api/sistema/sms               simula la caída del servicio de SMS
  POST /api/sistema/reprocesar        reintenta la cola de fallidos
  WS   /ws                            cambios de estado en tiempo real (Observer)
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from interfaz.servicio import DatosInvalidos, ServicioZyntra
from zyntra.estados import TransicionInvalida
from zyntra.gestor import EnvioNoEncontrado

ESTATICO = Path(__file__).parent / "estatico"


def crear_app(con_ejemplos: bool = True) -> FastAPI:
    servicio = ServicioZyntra()

    @asynccontextmanager
    async def ciclo(_: FastAPI):
        await servicio.iniciar(con_ejemplos)
        yield
        await servicio.detener()

    app = FastAPI(title="Zyntra", lifespan=ciclo)
    app.state.servicio = servicio

    @app.exception_handler(DatosInvalidos)
    async def _datos_invalidos(_: Request, error: DatosInvalidos):
        return JSONResponse({"error": str(error)}, status_code=422)

    @app.exception_handler(TransicionInvalida)
    async def _transicion(_: Request, error: TransicionInvalida):
        return JSONResponse({"error": str(error)}, status_code=409)

    @app.exception_handler(EnvioNoEncontrado)
    async def _no_encontrado(_: Request, error: EnvioNoEncontrado):
        return JSONResponse({"error": f"No existe un envío con la guía {error.args[0]}"},
                            status_code=404)

    @app.get("/", include_in_schema=False)
    async def inicio():
        return FileResponse(ESTATICO / "index.html")

    @app.get("/api/catalogo")
    async def catalogo():
        return servicio.catalogo()

    @app.post("/api/cotizar")
    async def cotizar(datos: dict[str, Any] = Body(...)):
        return servicio.cotizar(datos)

    @app.get("/api/envios")
    async def listar():
        return servicio.listar()

    @app.post("/api/envios", status_code=201)
    async def registrar(datos: dict[str, Any] = Body(...)):
        return servicio.registrar(datos)

    @app.get("/api/envios/{guia}")
    async def detalle(guia: str):
        return servicio.detalle(guia)

    @app.post("/api/envios/{guia}/estado")
    async def cambiar_estado(guia: str, datos: dict[str, Any] = Body(...)):
        return servicio.cambiar_estado(guia, str(datos.get("destino", "")),
                                       str(datos.get("descripcion", "")))

    @app.post("/api/envios/{guia}/simular")
    async def simular(guia: str):
        return servicio.simular(guia)

    @app.get("/api/sistema")
    async def sistema():
        return servicio.sistema()

    @app.post("/api/sistema/sms")
    async def tirar_sms(datos: dict[str, Any] = Body(...)):
        return servicio.tirar_sms(bool(datos.get("caido")))

    @app.post("/api/sistema/reprocesar")
    async def reprocesar():
        return await servicio.reprocesar()

    @app.websocket("/ws")
    async def en_vivo(ws: WebSocket):
        """Cada pantalla abierta recibe los cambios de estado al momento."""
        await ws.accept()
        cola = servicio.transmisor.conectar()
        recibir = asyncio.create_task(ws.receive_text())  # detecta cuando se cierra
        try:
            while True:
                siguiente = asyncio.create_task(cola.get())
                hechas, _ = await asyncio.wait({siguiente, recibir},
                                               return_when=asyncio.FIRST_COMPLETED)
                if recibir in hechas:
                    siguiente.cancel()
                    recibir.result()  # lanza WebSocketDisconnect si se cerró
                    recibir = asyncio.create_task(ws.receive_text())
                    continue
                evento = siguiente.result()
                await ws.send_json({"guia": evento.numero_guia,
                                    "anterior": evento.anterior.value,
                                    "nuevo": evento.nuevo.value,
                                    "descripcion": evento.descripcion,
                                    "hora": evento.marca_tiempo.isoformat(timespec="seconds")})
        except WebSocketDisconnect:
            pass
        finally:
            recibir.cancel()
            servicio.transmisor.desconectar(cola)

    app.mount("/estatico", StaticFiles(directory=ESTATICO), name="estatico")
    return app


app = crear_app()
