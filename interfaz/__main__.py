"""Arranca la aplicación: python -m interfaz

Abre el navegador en http://127.0.0.1:8000 y deja el servidor corriendo.
Para detenerlo, presione Ctrl+C en la terminal.
"""

import argparse
import threading
import webbrowser

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Interfaz web de Zyntra")
    parser.add_argument("--puerto", type=int, default=8000)
    parser.add_argument("--sin-navegador", action="store_true",
                        help="no abrir el navegador automáticamente")
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.puerto}"
    print(f"\n  Zyntra está corriendo en {url}\n  Para detenerlo presione Ctrl+C\n")
    if not args.sin_navegador:
        threading.Timer(1.5, webbrowser.open, [url]).start()
    uvicorn.run("interfaz.app:app", host="127.0.0.1", port=args.puerto, log_level="warning")


if __name__ == "__main__":
    main()
