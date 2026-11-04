"""Zyntra v0.1: versión inicial del sistema de envíos.

Toda la lógica vive en una sola clase: datos, cálculo de costo y cambios de
estado. Esta es la versión de partida que se refactoriza en v1.0.
"""


class Envio:
    def __init__(self, numero_guia, destino, tipo, peso, fragil=False,
                 asegurado=False, valor_declarado=0):
        self.numero_guia = numero_guia
        self.destino = destino
        self.tipo = tipo                # "nacional", "internacional" o "express"
        self.peso = peso
        self.fragil = fragil
        self.asegurado = asegurado
        self.valor_declarado = valor_declarado
        self.estado = "Registrado"

    # ---------------- Cálculo de costos ----------------
    def calcular_costo(self):
        if self.tipo == "nacional":
            costo = 80 + 15 * self.peso
        elif self.tipo == "internacional":
            costo = 950 + 280 * self.peso
        elif self.tipo == "express":
            costo = 150 + 25 * self.peso
        else:
            costo = 0

        if self.asegurado:
            if self.tipo == "nacional":
                costo += self.valor_declarado * 0.03
            elif self.tipo == "internacional":
                costo += self.valor_declarado * 0.05
            elif self.tipo == "express":
                costo += self.valor_declarado * 0.04

        if self.fragil:
            if self.tipo == "nacional":
                costo += 50
            elif self.tipo == "internacional":
                costo += 200
            elif self.tipo == "express":
                costo += 100

        return int(costo)

    # ---------------- Gestión de estados ----------------
    def cambiar_estado(self, nuevo_estado):
        if self.estado == "Registrado":
            if nuevo_estado == "En transito" or nuevo_estado == "Cancelado":
                self.estado = nuevo_estado
                return True
        elif self.estado == "En transito":
            if nuevo_estado == "En reparto":
                self.estado = nuevo_estado
                return True
            elif nuevo_estado == "Retenido en aduana":
                if self.tipo == "internacional":
                    self.estado = nuevo_estado
                    return True
        elif self.estado == "Retenido en aduana":
            if nuevo_estado == "En transito":
                self.estado = nuevo_estado
                return True
        elif self.estado == "En reparto":
            if nuevo_estado == "Entregado":
                self.estado = nuevo_estado
                return True
        return False
