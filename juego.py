"""Interfaz gráfica del simulador y del laboratorio de análisis."""

import random
import sys
import os
import math

import numpy as np
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
from matplotlib.backends.backend_agg import FigureCanvasAgg

import analisis
from escenarios import listar_escenarios, obtener_escenario
from simulacion import temperatura, tasa_cambio, tiempo_para_alcanzar

ANCHO, ALTO = 1180, 760
FPS = 60
VELOCIDAD_INICIAL = 5.0
INTERVALO_MUESTRA = 2.0
FONDO = (20, 28, 42)
PANEL = (30, 41, 59)
BORDE = (58, 77, 101)
ACENTO = (75, 190, 210)
AMBAR = (255, 186, 92)
SUPERFICIE = (25, 39, 58)
TEXTO = (238, 243, 250)
SECUNDARIO = (173, 188, 207)
AZUL = (51, 121, 174)
AZUL_HOVER = (71, 151, 207)
ROJO = (178, 72, 74)
VERDE = (62, 145, 105)

_FUENTE = None
_FUENTE_CHICA = None
_FUENTE_TITULO = None
_FUENTE_MICRO = None
_FONDO_CACHE = None


class CampoTexto:
    """Campo de texto Pygame; usa TEXTINPUT para admitir escritura natural."""

    def __init__(self, rect, texto="", multilinea=False, limite=1800):
        self.rect = pygame.Rect(rect)
        self.texto = texto
        self.multilinea = multilinea
        self.limite = limite
        self.activo = False
        self.seleccionado = False

    def manejar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self.activo = self.rect.collidepoint(evento.pos)
            self.seleccionado = False
        elif self.activo and evento.type == pygame.TEXTINPUT:
            base = "" if self.seleccionado else self.texto
            if len(base) + len(evento.text) <= self.limite:
                self.texto = base + evento.text
                self.seleccionado = False
        elif self.activo and evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_a and evento.mod & pygame.KMOD_CTRL:
                self.seleccionado = True
            elif evento.key == pygame.K_BACKSPACE:
                if self.seleccionado:
                    self.texto = ""
                    self.seleccionado = False
                else:
                    self.texto = self.texto[:-1]
            elif evento.key == pygame.K_RETURN and self.multilinea:
                self.texto += "\n"

    def dibujar(self, pantalla, etiqueta, marcador=""):
        color_borde = AZUL_HOVER if self.activo else (104, 123, 147)
        pygame.draw.rect(pantalla, (13, 19, 30), self.rect, border_radius=6)
        pygame.draw.rect(pantalla, color_borde, self.rect, 2, border_radius=6)
        rotulo = _FUENTE_CHICA.render(etiqueta, True, TEXTO)
        pantalla.blit(rotulo, (self.rect.x, self.rect.y - 24))

        contenido = self.texto if self.texto else marcador
        lineas = contenido.splitlines() or [""]
        if not self.multilinea:
            mostrado = lineas[-1]
            while mostrado and _FUENTE_CHICA.size(mostrado)[0] > self.rect.width - 18:
                mostrado = mostrado[1:]
            imagen = _FUENTE_CHICA.render(mostrado, True, TEXTO if self.texto else SECUNDARIO)
            pantalla.blit(imagen, (self.rect.x + 9, self.rect.y + 8))
            if self.activo and pygame.time.get_ticks() % 1000 < 500:
                x = self.rect.x + 10 + _FUENTE_CHICA.size(mostrado)[0]
                pygame.draw.line(pantalla, TEXTO, (x, self.rect.y + 7), (x, self.rect.bottom - 7), 1)
            return

        # Se muestran las últimas filas para que el campo multilinea siga visible al crecer.
        max_lineas = max(1, (self.rect.height - 14) // 22)
        clip_anterior = pantalla.get_clip()
        pantalla.set_clip(self.rect.inflate(-8, -6))
        for indice, linea in enumerate(lineas[-max_lineas:]):
            imagen = _FUENTE_CHICA.render(linea, True, TEXTO if self.texto else SECUNDARIO)
            pantalla.blit(imagen, (self.rect.x + 9, self.rect.y + 7 + indice * 22))
        pantalla.set_clip(clip_anterior)


def _texto(pantalla, contenido, posicion, fuente=None, color=TEXTO, centro=False):
    fuente = fuente or _FUENTE
    imagen = fuente.render(str(contenido), True, color)
    destino = imagen.get_rect(center=posicion) if centro else imagen.get_rect(topleft=posicion)
    pantalla.blit(imagen, destino)


def _texto_ajustado(pantalla, contenido, posicion, ancho, fuente=None, color=TEXTO,
                     max_lineas=None, alto_linea=None):
    """Envuelve texto por palabras para mantenerlo dentro de su panel."""
    fuente = fuente or _FUENTE
    alto_linea = alto_linea or fuente.get_linesize()
    lineas = []
    actual = ""
    for palabra in str(contenido).split():
        candidata = f"{actual} {palabra}".strip()
        if actual and fuente.size(candidata)[0] > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = candidata
    if actual:
        lineas.append(actual)
    if max_lineas and len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        ultima = lineas[-1]
        while ultima and fuente.size(ultima + "…")[0] > ancho:
            ultima = ultima.rsplit(" ", 1)[0] if " " in ultima else ultima[:-1]
        lineas[-1] = ultima.rstrip() + "…"
    for indice, linea in enumerate(lineas):
        _texto(pantalla, linea, (posicion[0], posicion[1] + indice * alto_linea), fuente, color)
    return len(lineas)


def _boton(pantalla, rect, texto, mouse, deshabilitado=False, color=AZUL):
    rect = pygame.Rect(rect)
    hover = rect.collidepoint(mouse) and not deshabilitado
    fondo = (55, 64, 77) if deshabilitado else (AZUL_HOVER if hover else color)
    pygame.draw.rect(pantalla, (12, 19, 30), rect.move(0, 3), border_radius=11)
    pygame.draw.rect(pantalla, fondo, rect, border_radius=11)
    pygame.draw.rect(pantalla, (135, 177, 199) if hover else (91, 125, 151), rect, 1, border_radius=11)
    fuente = _FUENTE_CHICA
    while fuente.get_height() > 16 and fuente.size(texto)[0] > rect.width - 18:
        fuente = pygame.font.Font(None, fuente.get_height() - 1)
    if fuente.size(texto)[0] > rect.width - 18:
        visible = texto
        while visible and fuente.size(visible + "…")[0] > rect.width - 18:
            visible = visible[:-1]
        texto = visible.rstrip() + "…"
    imagen = fuente.render(texto, True, TEXTO)
    pantalla.blit(imagen, imagen.get_rect(center=rect.center))
    return rect


def _clic(evento, rect):
    return (
        evento.type == pygame.MOUSEBUTTONDOWN
        and evento.button == 1
        and rect.collidepoint(evento.pos)
    )


def _marco(pantalla, titulo, subtitulo=None):
    # Fondo con gradiente discreto y una cabecera común que da continuidad a las pantallas.
    global _FONDO_CACHE
    if _FONDO_CACHE is None:
        _FONDO_CACHE = pygame.Surface((ANCHO, ALTO))
        for y in range(ALTO):
            proporcion = y / max(1, ALTO - 1)
            tono = tuple(round(FONDO[i] + ((13, 20, 32)[i] - FONDO[i]) * proporcion) for i in range(3))
            pygame.draw.line(_FONDO_CACHE, tono, (0, y), (ANCHO, y))
        for x in range(38, ANCHO, 74):
            pygame.draw.line(_FONDO_CACHE, (23, 32, 46), (x, 116), (x, ALTO), 1)
        for y in range(164, ALTO, 74):
            pygame.draw.line(_FONDO_CACHE, (23, 32, 46), (0, y), (ANCHO, y), 1)
    pantalla.blit(_FONDO_CACHE, (0, 0))
    pygame.draw.rect(pantalla, (24, 36, 53), (0, 0, ANCHO, 116))
    pygame.draw.line(pantalla, BORDE, (34, 115), (ANCHO - 34, 115), 1)
    pygame.draw.rect(pantalla, ACENTO, (34, 28, 5, 48), border_radius=3)
    _texto(pantalla, titulo, (52, 25), _FUENTE_TITULO)
    pygame.draw.circle(pantalla, ACENTO, (ANCHO - 276, 43), 5)
    _texto(pantalla, "LABORATORIO TÉRMICO", (ANCHO - 260, 30), _FUENTE_CHICA, TEXTO)
    _texto(pantalla, "LEY DE NEWTON  ·  EQUILIBRIO",
           (ANCHO - 260, 57), _FUENTE_MICRO, SECUNDARIO)
    if subtitulo:
        _texto_ajustado(pantalla, subtitulo, (45, 82), ANCHO - 90,
                        _FUENTE_CHICA, SECUNDARIO, max_lineas=2, alto_linea=22)


def _panel(pantalla, rect, acento=None, color=PANEL, radio=12):
    """Tarjeta elevada con borde sutil y acento opcional."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(pantalla, (12, 19, 30), rect.move(0, 4), border_radius=radio)
    pygame.draw.rect(pantalla, color, rect, border_radius=radio)
    pygame.draw.rect(pantalla, BORDE, rect, 1, border_radius=radio)
    if acento:
        pygame.draw.rect(pantalla, acento, (rect.x, rect.y + 12, 3, rect.height - 24), border_radius=2)


def _dibujar_error(pantalla, mensaje):
    if mensaje:
        caja = pygame.Rect(42, ALTO - 58, ANCHO - 84, 48)
        pygame.draw.rect(pantalla, (93, 42, 48), caja, border_radius=6)
        _texto_ajustado(pantalla, mensaje, (54, ALTO - 52), ANCHO - 110,
                        _FUENTE_CHICA, (255, 224, 224), max_lineas=2, alto_linea=17)


def iniciar_pygame():
    """Inicializa Pygame y devuelve la ventana junto con su reloj."""
    global _FUENTE, _FUENTE_CHICA, _FUENTE_TITULO, _FUENTE_MICRO
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Laboratorio virtual | Ley de Enfriamiento de Newton")
    _FUENTE = pygame.font.Font(None, 32)
    _FUENTE_CHICA = pygame.font.Font(None, 25)
    _FUENTE_TITULO = pygame.font.Font(None, 48)
    _FUENTE_MICRO = pygame.font.Font(None, 20)
    return pantalla, pygame.time.Clock()


def dibujar_menu_principal(pantalla, puntos=0, medallas=None) -> None:
    _marco(pantalla, "Laboratorio virtual", "Explora cómo cambia la temperatura y por qué ocurre.")
    mouse = pygame.mouse.get_pos()
    hero = pygame.Rect(54, 142, 1072, 386)
    _panel(pantalla, hero, acento=ACENTO, color=SUPERFICIE, radio=20)
    pygame.draw.circle(pantalla, (32, 52, 72), (850, 337), 165)
    pygame.draw.circle(pantalla, (54, 81, 103), (850, 337), 165, 1)
    pygame.draw.circle(pantalla, (48, 69, 90), (850, 337), 132, 1)
    _texto(pantalla, "EXPERIMENTO INTERACTIVO", (92, 174), _FUENTE_CHICA, ACENTO)
    _texto_ajustado(pantalla, "El calor siempre busca el equilibrio.",
                    (92, 218), 510, _FUENTE_TITULO, TEXTO,
                    max_lineas=2, alto_linea=46)
    _texto_ajustado(pantalla,
                    "Observa cómo el objeto se acerca a la temperatura ambiente y descubre qué determina la rapidez del cambio.",
                    (94, 316), 475, _FUENTE_CHICA, SECUNDARIO,
                    max_lineas=3, alto_linea=25)
    ecuacion = pygame.Rect(90, 409, 488, 78)
    pygame.draw.rect(pantalla, (17, 29, 44), ecuacion, border_radius=12)
    pygame.draw.rect(pantalla, (52, 76, 99), ecuacion, 1, border_radius=12)
    _texto(pantalla, "MODELO DE NEWTON", (108, 419), _FUENTE_MICRO, AMBAR)
    _texto(pantalla, "dT/dt = −k(T − T_amb)", (108, 439), _FUENTE, TEXTO)
    cafe = obtener_escenario("cafe")
    dibujar_objeto(
        pantalla, 90.0, cafe, 90.0, "cafe",
        pygame.time.get_ticks() / 1000.0, centro=(850, 342),
    )

    _texto(pantalla, "ELIGE CÓMO EXPLORAR", (70, 548), _FUENTE_MICRO, SECUNDARIO)
    botones_menu = (
        ((70, 572, 320, 82), "Modo Juego", AZUL),
        ((430, 572, 320, 82), "Modo Análisis", (79, 105, 133)),
        ((790, 572, 320, 82), "Aprender el cálculo", (67, 128, 113)),
    )
    for rect, label, color in botones_menu:
        _boton(pantalla, rect, label, mouse, color=color)
    medallas = medallas or {"Oro": 0, "Plata": 0, "Bronce": 0}
    _texto(pantalla, f"PUNTOS  {puntos:04d}    ·    ORO {medallas['Oro']}   PLATA {medallas['Plata']}   BRONCE {medallas['Bronce']}",
           (72, 688), _FUENTE_CHICA, AMBAR)
    _texto(pantalla, "ESC  ·  SALIR", (ANCHO - 170, 688), _FUENTE_CHICA, SECUNDARIO)


def dibujar_menu_escenarios(pantalla, puntos=0) -> None:
    _marco(pantalla, "Elige un escenario", "Cada escenario tiene un ambiente y parámetros propios.")
    mouse = pygame.mouse.get_pos()
    for indice, (clave, nombre) in enumerate(listar_escenarios()):
        escenario = obtener_escenario(clave)
        x, y = 100 + (indice % 2) * 500, 155 + (indice // 2) * 220
        rect = pygame.Rect(x, y, 450, 180)
        _panel(pantalla, rect, acento=escenario["color_calido"])
        if rect.collidepoint(mouse):
            pygame.draw.rect(pantalla, AZUL_HOVER, rect, 2, border_radius=12)
        pygame.draw.circle(pantalla, escenario["color_calido"], (x + 51, y + 50), 24)
        _texto(pantalla, nombre, (x + 91, y + 32), _FUENTE)
        _texto_ajustado(pantalla, escenario["descripcion"], (x + 25, y + 73),
                        400, _FUENTE_CHICA, SECUNDARIO, max_lineas=2, alto_linea=21)
        badge_amb = pygame.Rect(x + 25, y + 121, 170, 27)
        badge_k = pygame.Rect(x + 205, y + 121, 215, 27)
        pygame.draw.rect(pantalla, (20, 31, 46), badge_amb, border_radius=7)
        pygame.draw.rect(pantalla, (20, 31, 46), badge_k, border_radius=7)
        _texto(pantalla, f"AMBIENTE  {escenario['T_amb']:.1f} °C",
               (badge_amb.x + 8, badge_amb.y + 3), _FUENTE_MICRO, TEXTO)
        _texto(pantalla, f"k  {escenario['k_rango'][0]}–{escenario['k_rango'][1]} 1/s",
               (badge_k.x + 8, badge_k.y + 3), _FUENTE_MICRO, TEXTO)
        _texto(pantalla, f"META  {escenario['meta']:.1f} °C",
               (x + 25, y + 153), _FUENTE_MICRO, AMBAR)
    personalizado = pygame.Rect(300, 590, 580, 70)
    _panel(pantalla, personalizado, acento=ACENTO)
    if personalizado.collidepoint(mouse):
        pygame.draw.rect(pantalla, AZUL_HOVER, personalizado, 2, border_radius=12)
    _texto(pantalla, "Crear objeto personalizado", (ANCHO // 2, 610), _FUENTE, TEXTO, centro=True)
    _texto(pantalla, "Define sus temperaturas, constante k y meta", (ANCHO // 2, 640),
           _FUENTE_CHICA, SECUNDARIO, centro=True)
    _texto(pantalla, "Esc: volver", (ANCHO - 135, ALTO - 42), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"Puntaje acumulado: {puntos}", (42, ALTO - 42), _FUENTE_CHICA, (255, 213, 120))


def color_interpolado(temp: float, T_amb: float, T0: float,
                       color_frio: tuple, color_calido: tuple) -> tuple:
    """Normaliza la temperatura y mezcla independientemente los canales RGB."""
    proporcion = 0.0 if T0 == T_amb else (temp - T_amb) / (T0 - T_amb)
    proporcion = max(0.0, min(1.0, proporcion))
    # El factor entre 0 y 1 pondera frío y caliente sin permitir colores fuera de rango.
    return tuple(
        round(frio + (calido - frio) * proporcion)
        for frio, calido in zip(color_frio, color_calido)
    )


def dibujar_objeto(pantalla, temp: float, escenario: dict, T0: float,
                   clave: str = "cafe", tiempo: float = 0.0,
                   centro: tuple | None = None) -> None:
    """Dibuja el objeto del escenario y su calor de forma animada."""
    if T0 < escenario["T_amb"]:
        color_frio, color_calido = escenario["color_calido"], escenario["color_frio"]
    else:
        color_frio, color_calido = escenario["color_frio"], escenario["color_calido"]
    color = color_interpolado(
        temp, escenario["T_amb"], T0,
        color_frio, color_calido,
    )
    cx, cy = centro or (ANCHO // 2, 385)
    proporcion = 0.0 if T0 == escenario["T_amb"] else (
        (temp - escenario["T_amb"]) / (T0 - escenario["T_amb"])
    )
    proporcion = max(0.0, min(1.0, proporcion))

    # El resplandor y las ondas se apagan a medida que el objeto se enfría.
    halo = pygame.Surface((440, 390), pygame.SRCALPHA)
    pygame.draw.ellipse(halo, (*color, round(12 + 34 * proporcion)), (30, 55, 380, 280))
    pantalla.blit(halo, (cx - 220, cy - 205))
    pygame.draw.line(pantalla, (67, 82, 101), (cx - 190, cy + 163), (cx + 190, cy + 163), 3)
    for i in range(3):
        y = cy - 125 - i * 37
        fase = tiempo * (1.4 + i * .15) + i * 2.1
        x = cx + math.sin(fase) * (15 + i * 5)
        puntos = [(round(x + math.sin(fase + j * .65) * 9), y - j * 9) for j in range(7)]
        if proporcion > .05:
            pygame.draw.lines(pantalla, (205, 218, 229), False, puntos, max(1, round(1 + proporcion * 2)))

    if clave == "cafe":
        # Asa detrás del cuerpo: dos elipses crean un hueco limpio y legible.
        pygame.draw.ellipse(pantalla, (174, 194, 207), (cx + 73, cy - 28, 101, 104))
        pygame.draw.ellipse(pantalla, FONDO, (cx + 91, cy - 10, 66, 68))

        pygame.draw.ellipse(pantalla, (9, 14, 23), (cx - 130, cy + 104, 260, 34))
        cuerpo = [
            (cx - 101, cy - 72), (cx + 101, cy - 72),
            (cx + 82, cy + 82), (cx + 57, cy + 101),
            (cx - 57, cy + 101), (cx - 82, cy + 82),
        ]
        pygame.draw.polygon(pantalla, color, cuerpo)
        pygame.draw.ellipse(pantalla, color, (cx - 82, cy + 54, 164, 70))
        # Brillo lateral suave para dar volumen al recipiente.
        brillo = pygame.Surface((28, 120), pygame.SRCALPHA)
        pygame.draw.ellipse(brillo, (255, 255, 255, 74), (0, 0, 28, 120))
        pantalla.blit(brillo, (cx - 68, cy - 30))

        # Borde cerámico y superficie del café separados por contraste.
        pygame.draw.ellipse(pantalla, (225, 233, 239), (cx - 106, cy - 82, 212, 38))
        pygame.draw.ellipse(pantalla, (119, 137, 151), (cx - 95, cy - 76, 190, 25))
        bebida = color_interpolado(temp, escenario["T_amb"], T0, (113, 70, 43), (70, 37, 23))
        pygame.draw.ellipse(pantalla, bebida, (cx - 88, cy - 73, 176, 18))
        pygame.draw.arc(pantalla, (255, 255, 255), (cx - 104, cy - 81, 208, 36), 0.15, 2.95, 3)
        pygame.draw.line(pantalla, (255, 255, 255), (cx - 61, cy - 35), (cx - 48, cy + 48), 4)
    elif clave == "motor":
        pygame.draw.ellipse(pantalla, (9, 14, 23), (cx - 160, cy + 100, 320, 34))
        bloque = pygame.Rect(cx - 137, cy - 71, 274, 166)
        pygame.draw.rect(pantalla, color, bloque, border_radius=22)
        pygame.draw.rect(pantalla, (205, 218, 228), bloque, 3, border_radius=22)
        for x in range(cx - 91, cx + 100, 48):
            pygame.draw.rect(pantalla, (58, 70, 81), (x, cy - 100, 19, 29), border_radius=5)
            pygame.draw.line(pantalla, (212, 223, 230), (x + 9, cy - 93), (x + 9, cy + 70), 3)
        pygame.draw.circle(pantalla, (33, 46, 57), (cx, cy + 12), 39)
        pygame.draw.circle(pantalla, (217, 228, 235), (cx, cy + 12), 39, 3)
        pygame.draw.line(pantalla, (218, 228, 234), (cx - 175, cy + 74), (cx - 130, cy + 74), 12)
        pygame.draw.line(pantalla, (218, 228, 234), (cx + 137, cy - 35), (cx + 178, cy - 35), 12)
    elif clave == "horno":
        pygame.draw.ellipse(pantalla, (9, 14, 23), (cx - 166, cy + 105, 332, 34))
        pygame.draw.ellipse(pantalla, (220, 226, 230), (cx - 155, cy + 38, 310, 78))
        pygame.draw.ellipse(pantalla, (125, 137, 144), (cx - 136, cy + 45, 272, 57))
        pygame.draw.ellipse(pantalla, color, (cx - 111, cy - 68, 222, 139))
        for i in range(7):
            x = cx - 75 + (i % 4) * 47
            y = cy - 37 + (i // 4) * 48
            pygame.draw.circle(pantalla, (117, 68, 41), (x, y), 9)
        pygame.draw.ellipse(pantalla, (255, 232, 174), (cx - 71, cy - 40, 28, 10))
    elif clave == "personalizado":
        # Forma neutra para que el estudiante imagine su propio objeto.
        pygame.draw.ellipse(pantalla, (9, 14, 23), (cx - 132, cy + 102, 264, 36))
        pygame.draw.circle(pantalla, (231, 239, 246), (cx, cy + 4), 111, 3)
        pygame.draw.circle(pantalla, color, (cx, cy), 101)
        pygame.draw.ellipse(pantalla, (255, 255, 255), (cx - 55, cy - 66, 34, 17))
        pygame.draw.arc(pantalla, (245, 249, 252), (cx - 72, cy - 78, 144, 150), .5, 2.3, 3)
    else:
        # Muestra forense en una cápsula de laboratorio, sin representar un cuerpo.
        pygame.draw.ellipse(pantalla, (9, 14, 23), (cx - 137, cy + 108, 274, 34))
        pygame.draw.rect(pantalla, (189, 207, 218), (cx - 124, cy - 42, 248, 113), border_radius=48)
        pygame.draw.rect(pantalla, color, (cx - 105, cy - 24, 210, 78), border_radius=35)
        pygame.draw.line(pantalla, (235, 241, 244), (cx - 72, cy - 3), (cx + 72, cy - 3), 4)
        pygame.draw.circle(pantalla, (245, 248, 250), (cx, cy - 3), 8)
        pygame.draw.rect(pantalla, (185, 201, 213), (cx - 24, cy - 78, 48, 35), border_radius=8)

    # El flujo sale de un cuerpo más caliente y entra en uno más frío que el ambiente.
    sale_calor = T0 > escenario["T_amb"]
    color_flujo = (255, 156, 83) if sale_calor else (89, 195, 230)
    for lado in (-1, 1):
        inicio = (cx + lado * (185 if sale_calor else 225), cy + 42)
        fin = (cx + lado * (225 if sale_calor else 185), cy + 42)
        pygame.draw.line(pantalla, color_flujo, inicio, fin, 3)
        dx = fin[0] - inicio[0]
        direccion = 1 if dx > 0 else -1
        pygame.draw.line(pantalla, color_flujo, fin, (fin[0] - direccion * 10, fin[1] - 7), 3)
        pygame.draw.line(pantalla, color_flujo, fin, (fin[0] - direccion * 10, fin[1] + 7), 3)


def dibujar_hud(pantalla, t: float, temp: float, rate: float) -> None:
    panel = pygame.Rect(28, 132, 330, 125)
    _panel(pantalla, panel, acento=ACENTO, radio=10)
    _texto(pantalla, f"Tiempo: {t:7.1f} s", (48, 150), _FUENTE_CHICA)
    _texto(pantalla, f"Temperatura: {temp:6.2f} °C", (48, 186), _FUENTE_CHICA)
    _texto(pantalla, f"dT/dt: {rate: .3f} °C/s", (48, 222), _FUENTE_CHICA)


def _dibujar_panel_edo(pantalla, sim, temp, rate):
    """Conecta la ecuación diferencial con el estado y las muestras actuales."""
    escenario = sim["escenario"]
    amb = escenario["T_amb"]
    delta_temp = temp - amb
    panel = pygame.Rect(28, 278, 330, 300)
    _panel(pantalla, panel, acento=(255, 213, 120), radio=10)
    _texto(pantalla, "LA ECUACIÓN EN ESTE INSTANTE", (44, 292), _FUENTE_CHICA, (255, 213, 120))
    _texto(pantalla, "dT/dt = −k(T − T_amb)", (44, 324), _FUENTE_CHICA)
    _texto(pantalla, f"−k·ΔT = −{sim['k']:.3g}·{delta_temp:.3g}",
           (44, 352), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"Tasa actual: {rate:.4g} °C/s", (44, 379), _FUENTE_CHICA)
    _texto(pantalla, f"τ = 1/k: {1 / sim['k']:.3g} s",
           (44, 402), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"t½ = ln(2)/k: {math.log(2) / sim['k']:.3g} s",
           (44, 424), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, "Últimas mediciones", (44, 446), _FUENTE_CHICA, (255, 213, 120))
    encabezados = ((44, "t"), (100, "T (°C)"), (175, "ΔT"), (259, "dT/dt"))
    for x, texto in encabezados:
        _texto(pantalla, texto, (x, 468), _FUENTE_CHICA, SECUNDARIO)
    for fila, (ti, lectura) in enumerate(sim["datos"][-4:]):
        y = 489 + fila * 22
        diferencia = lectura - amb
        columnas = (f"{ti:.0f}", f"{lectura:.1f}", f"{diferencia:.1f}",
                    f"{-sim['k'] * diferencia:.2f}")
        for (x, _), valor in zip(encabezados, columnas):
            _texto(pantalla, valor, (x, y), _FUENTE_CHICA, TEXTO)


def _dibujar_progreso(pantalla, temp, escenario, T0, datos, tiempo):
    """Panel visual con termómetro, objetivo ambiente y últimas mediciones."""
    panel = pygame.Rect(858, 238, 292, 300)
    _panel(pantalla, panel, acento=ACENTO, color=(25, 37, 54), radio=14)
    _texto(pantalla, "CAMBIO HACIA EL EQUILIBRIO", (878, 257), _FUENTE_CHICA)
    amb, inicial = escenario["T_amb"], T0
    proporcion = 0 if inicial == amb else max(0, min(1, (temp - amb) / (inicial - amb)))
    # Termómetro vertical; el marcador se desplaza desde el inicio hasta el ambiente.
    x, top, bottom = 902, 315, 468
    pygame.draw.line(pantalla, (104, 122, 143), (x, top), (x, bottom), 15)
    pygame.draw.circle(pantalla, (104, 122, 143), (x, bottom + 6), 17)
    y = round(bottom - proporcion * (bottom - top))
    colores_termometro = ((244, 112, 62), (63, 182, 201)) if inicial < amb else ((63, 182, 201), (244, 112, 62))
    color_termometro = color_interpolado(temp, amb, inicial, *colores_termometro)
    pygame.draw.line(pantalla, color_termometro, (x, y), (x, bottom), 8)
    pygame.draw.circle(pantalla, color_termometro, (x, bottom + 6), 12)
    pygame.draw.line(pantalla, (223, 232, 239), (x + 15, top), (x + 25, top), 2)
    pygame.draw.line(pantalla, (223, 232, 239), (x + 15, bottom), (x + 25, bottom), 2)
    _texto(pantalla, f"T0 {inicial:.1f}°", (x + 34, top - 10), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"{amb:.1f}° ambiente", (x + 34, bottom - 4), _FUENTE_CHICA, SECUNDARIO)
    etiqueta_y = max(top + 18, min(bottom - 33, y - 9))
    _texto(pantalla, f"{temp:.1f} °C", (x + 34, etiqueta_y), _FUENTE_CHICA, TEXTO)
    _texto(pantalla, f"{round((1 - proporcion) * 100)}% hacia el equilibrio", (878, 499), _FUENTE_CHICA, SECUNDARIO)
    # Trazado en vivo de las muestras ya tomadas.
    gx, gy, gw, gh = 1015, 330, 112, 125
    pygame.draw.rect(pantalla, (15, 23, 35), (gx, gy, gw, gh), border_radius=6)
    pygame.draw.line(pantalla, (80, 99, 120), (gx + 7, gy + gh - 10), (gx + gw - 6, gy + gh - 10), 1)
    puntos = []
    for instante, lectura in datos[-30:]:
        px = gx + 8 + (instante / max(tiempo, 1)) * (gw - 16)
        py = gy + 8 + (1 - max(0, min(1, (lectura - amb) / max(inicial - amb, .001)))) * (gh - 20)
        puntos.append((round(px), round(py)))
    if len(puntos) > 1:
        pygame.draw.lines(pantalla, (107, 194, 220), False, puntos, 2)
    for punto in puntos:
        pygame.draw.circle(pantalla, (231, 244, 248), punto, 3)
    _texto(pantalla, "T(t)", (gx + 8, gy - 24), _FUENTE_CHICA, SECUNDARIO)


def _sim_nuevo(escenario, clave):
    T0 = random.uniform(*escenario["T0_rango"])
    k = random.uniform(*escenario["k_rango"])
    return {
        "clave": clave, "escenario": escenario, "T0": T0, "k": k, "k_base": k,
        "t": 0.0, "pausada": True, "velocidad": VELOCIDAD_INICIAL,
        "siguiente_muestra": 0.0, "datos": [], "reto": None,
        "ruido_std": float(escenario.get("ruido_std", 0.3)),
        "condicion": 0, "completada": False, "puntos": 0, "medalla": None,
    }


def _medir(sim, hasta):
    while sim["siguiente_muestra"] <= hasta:
        instante = sim["siguiente_muestra"]
        lectura = temperatura(instante, sim["T0"], sim["escenario"]["T_amb"], sim["k"])
        sim["datos"].append((instante, lectura + random.gauss(0, sim["ruido_std"])))
        sim["siguiente_muestra"] += INTERVALO_MUESTRA


def _dibujar_simulacion(pantalla, sim, mouse, botones):
    escenario = sim["escenario"]
    _marco(pantalla, escenario["nombre"], escenario["descripcion"])
    pygame.draw.ellipse(pantalla, (23, 35, 51), (372, 222, 436, 326))
    pygame.draw.ellipse(pantalla, (48, 70, 92), (386, 232, 408, 306), 1)
    pygame.draw.ellipse(pantalla, (38, 56, 76), (405, 247, 370, 276), 1)
    t = sim["t"]
    temp = temperatura(t, sim["T0"], escenario["T_amb"], sim["k"])
    dibujar_objeto(pantalla, temp, escenario, sim["T0"], sim["clave"], t)
    dibujar_hud(pantalla, t, temp, tasa_cambio(t, sim["T0"], escenario["T_amb"], sim["k"]))
    _dibujar_panel_edo(
        pantalla, sim, temp,
        tasa_cambio(t, sim["T0"], escenario["T_amb"], sim["k"]),
    )
    _dibujar_progreso(pantalla, temp, escenario, sim["T0"], sim["datos"], t)
    estado = (
        "Elige una condición y pulsa Reanudar" if sim["t"] == 0 and sim["pausada"]
        else "PAUSADA" if sim["pausada"]
        else f"Velocidad ×{sim['velocidad'] / VELOCIDAD_INICIAL:g}"
    )
    _texto(pantalla, estado, (ANCHO // 2, 525), _FUENTE_CHICA, SECUNDARIO, centro=True)
    labels = (
        "Reanudar" if sim["pausada"] else "Pausar",
        "− Velocidad", "+ Velocidad", "Reiniciar", "Predecir meta", "Terminar",
    )
    rects = (
        (30, 640, 165, 56), (210, 640, 165, 56), (390, 640, 165, 56),
        (570, 640, 165, 56), (750, 640, 165, 56), (930, 640, 210, 56),
    )
    for indice, (rect, label) in enumerate(zip(rects, labels)):
        _boton(
            pantalla, rect, label, mouse,
            deshabilitado=(indice == 5 and len(sim["datos"]) < 2),
            color=ROJO if indice == 5 else AZUL,
        )
        botones.append(pygame.Rect(rect))
    _texto(pantalla, f"Mediciones guardadas: {len(sim['datos'])}",
           (ANCHO - 300, 142), _FUENTE_CHICA, SECUNDARIO)
    if sim["reto"]:
        reto = sim["reto"]
        estado_reto = "Reto registrado" if reto.get("real") is not None else "Reto configurado"
        _texto(pantalla, f"{estado_reto}: objetivo {reto['objetivo']:.1f} °C",
               (ANCHO - 350, 185), _FUENTE_CHICA, SECUNDARIO)
    condicion, _ = escenario["condiciones"][sim["condicion"]]
    direccion = "enfriamiento" if sim["T0"] > escenario["T_amb"] else "calentamiento"
    _texto(pantalla, f"META · {direccion}: {escenario['meta']:.1f} °C", (ANCHO // 2, 565),
           _FUENTE_CHICA, (119, 224, 177) if sim["completada"] else (255, 213, 120), centro=True)
    if sim["completada"]:
        _texto(pantalla, f"Meta cumplida · +{sim['puntos']} puntos · Medalla {sim['medalla']}",
               (ANCHO // 2, 606), _FUENTE_CHICA, (119, 224, 177), centro=True)
    else:
        botones.append(_boton(
            pantalla, (ANCHO // 2 - 180, 585, 360, 42),
            f"Condición: {condicion} · cambiar", mouse,
            deshabilitado=sim["t"] > 0, color=(94, 99, 147),
        ))


def correr_simulacion(pantalla, reloj, clave_escenario: str, escenario=None) -> dict:
    """Corre una partida y devuelve las mediciones, puntos y medalla obtenida."""
    escenario = escenario or obtener_escenario(clave_escenario)
    sim = _sim_nuevo(escenario, clave_escenario)
    reto_campo = CampoTexto((ANCHO // 2 - 135, ALTO // 2 + 15, 270, 48))
    en_reto = False
    prediccion_reto = None
    error = ""

    while True:
        delta = reloj.tick(FPS) / 1000.0
        if not sim["pausada"] and not sim["completada"] and not en_reto:
            sim["t"] += delta * sim["velocidad"]
            _medir(sim, sim["t"])
            temp_actual = temperatura(sim["t"], sim["T0"], sim["escenario"]["T_amb"], sim["k"])
            meta_alcanzada = (
                temp_actual <= sim["escenario"]["meta"]
                if sim["T0"] > sim["escenario"]["T_amb"]
                else temp_actual >= sim["escenario"]["meta"]
            )
            if meta_alcanzada:
                if len(sim["datos"]) < 2:
                    tiempo_meta = tiempo_para_alcanzar(
                        sim["escenario"]["meta"], sim["T0"],
                        sim["escenario"]["T_amb"], sim["k"],
                    )
                    lectura_meta = sim["escenario"]["meta"] + random.gauss(0, sim["ruido_std"])
                    sim["datos"].append((tiempo_meta, lectura_meta))
                sim["completada"] = True
                sim["pausada"] = True
                sim["puntos"] = 100
                if sim["reto"] and sim["reto"].get("prediccion") is not None:
                    diferencia = abs(sim["reto"]["prediccion"] - sim["reto"]["real"])
                    margen = max(1.0, sim["reto"]["real"] * 0.15)
                    precision = max(0.0, 1.0 - diferencia / margen)
                    sim["puntos"] += round(50 * precision)
                sim["medalla"] = "Oro" if sim["puntos"] >= 145 else "Plata" if sim["puntos"] >= 125 else "Bronce"

        mouse = pygame.mouse.get_pos()
        botones = []
        _dibujar_simulacion(pantalla, sim, mouse, botones)
        if not en_reto:
            _dibujar_error(pantalla, error)
        if en_reto:
            botones = []
            overlay = pygame.Rect(ANCHO // 2 - 260, ALTO // 2 - 120, 520, 280)
            pygame.draw.rect(pantalla, PANEL, overlay, border_radius=12)
            pygame.draw.rect(pantalla, AZUL_HOVER, overlay, 2, border_radius=12)
            _texto(pantalla, "Reto: predice el tiempo", (ANCHO // 2, overlay.y + 42),
                   _FUENTE, centro=True)
            if prediccion_reto is None:
                _texto(pantalla, f"¿Cuándo llegará a {sim['reto']['objetivo']:.1f} °C?",
                       (ANCHO // 2, overlay.y + 88), _FUENTE_CHICA, centro=True)
                reto_campo.dibujar(pantalla, "Tu predicción (segundos)")
                botones.append(_boton(
                    pantalla, (overlay.x + 110, overlay.y + 205, 180, 48),
                    "Comprobar", mouse,
                ))
                botones.append(_boton(
                    pantalla, (overlay.x + 310, overlay.y + 205, 130, 48),
                    "Cancelar", mouse, color=ROJO,
                ))
            else:
                real = sim["reto"]["real"]
                _texto(pantalla, f"Tu predicción: {prediccion_reto:.2f} s",
                       (ANCHO // 2, overlay.y + 102), _FUENTE_CHICA, centro=True)
                _texto(pantalla, f"Modelo: {real:.2f} s  |  Diferencia: {abs(real - prediccion_reto):.2f} s",
                       (ANCHO // 2, overlay.y + 144), _FUENTE_CHICA, centro=True)
                botones.append(_boton(
                    pantalla, (ANCHO // 2 - 85, overlay.y + 205, 170, 48),
                    "Volver al juego", mouse,
                ))
            _dibujar_error(pantalla, error)
        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if en_reto and prediccion_reto is None:
                reto_campo.manejar_evento(evento)
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                if en_reto:
                    en_reto = False
                    error = ""
                else:
                    _medir(sim, sim["t"])
                    return {"datos": list(sim["datos"]), "puntos": sim["puntos"], "medalla": sim["medalla"]}
            if evento.type == pygame.KEYDOWN and not en_reto:
                if evento.key == pygame.K_SPACE:
                    sim["pausada"] = not sim["pausada"]
                elif evento.key == pygame.K_r:
                    sim = _sim_nuevo(sim["escenario"], sim["clave"])
                elif evento.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    sim["velocidad"] = min(80.0, sim["velocidad"] * 2)
                elif evento.key == pygame.K_MINUS:
                    sim["velocidad"] = max(1.25, sim["velocidad"] / 2)
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if en_reto:
                    if prediccion_reto is None and botones[0].collidepoint(evento.pos):
                        try:
                            prediccion_reto = float(reto_campo.texto.strip())
                            if prediccion_reto < 0:
                                raise ValueError("El tiempo debe ser positivo.")
                            real = tiempo_para_alcanzar(
                                sim["reto"]["objetivo"], sim["T0"],
                                sim["escenario"]["T_amb"], sim["k"],
                            )
                            sim["reto"].update(prediccion=prediccion_reto, real=real)
                            error = ""
                        except ValueError as excepcion:
                            prediccion_reto = None
                            error = str(excepcion) or "Escribe un número válido."
                    elif botones[-1].collidepoint(evento.pos):
                        if prediccion_reto is None:
                            en_reto = False
                            error = ""
                        else:
                            en_reto = False
                elif any(rect.collidepoint(evento.pos) for rect in botones):
                    indice = next(i for i, rect in enumerate(botones) if rect.collidepoint(evento.pos))
                    if indice == 0:
                        sim["pausada"] = not sim["pausada"]
                    elif indice == 1:
                        sim["velocidad"] = max(1.25, sim["velocidad"] / 2)
                    elif indice == 2:
                        sim["velocidad"] = min(80.0, sim["velocidad"] * 2)
                    elif indice == 3:
                        sim = _sim_nuevo(sim["escenario"], sim["clave"])
                    elif indice == 4:
                        objetivo = sim["escenario"]["meta"]
                        sim["reto"] = {"objetivo": objetivo, "real": None}
                        reto_campo.texto = ""
                        reto_campo.activo = True
                        prediccion_reto = None
                        en_reto = True
                    elif indice == 5:
                        if len(sim["datos"]) < 2:
                            error = "Espera a que se guarden al menos dos mediciones para analizar."
                        else:
                            _medir(sim, sim["t"])
                            return {"datos": list(sim["datos"]), "puntos": sim["puntos"], "medalla": sim["medalla"]}
                    elif indice == 6 and not sim["completada"] and sim["t"] == 0:
                        sim["condicion"] = (sim["condicion"] + 1) % len(sim["escenario"]["condiciones"])
                        _, factor = sim["escenario"]["condiciones"][sim["condicion"]]
                        sim["k"] = sim["k_base"] * factor


def _crear_figura_superficie(t, T, T_amb, resultado, r2, comparaciones):
    figura = analisis.graficar_resultado(
        t, T, T_amb, resultado, r2, comparaciones=comparaciones
    )
    canvas = FigureCanvasAgg(figura)
    canvas.draw()
    ancho, alto = canvas.get_width_height()
    superficie = pygame.image.frombuffer(canvas.buffer_rgba(), (ancho, alto), "RGBA").copy()
    pygame.display.flip()
    return superficie


def _analizar(t, T, T_amb):
    resultado = analisis.ajustar_modelo(t, T, T_amb)
    r2 = analisis.calcular_r2(t, T, T_amb, resultado["k"], resultado["T0"])
    temps = np.asarray(T, dtype=float)
    tiempos = np.asarray(t, dtype=float)
    validos = np.isfinite(temps) & np.isfinite(tiempos) & (np.abs(temps - T_amb) > 0)
    predichas = T_amb + (resultado["T0"] - T_amb) * np.exp(
        -resultado["k"] * tiempos[validos]
    )
    residuos = temps[validos] - predichas
    return resultado, r2, residuos, validos


def _datos_manuales(texto):
    filas = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.strip()
        if not linea:
            continue
        partes = linea.replace(";", ",").split(",") if ("," in linea or ";" in linea) else linea.split()
        if len(partes) != 2:
            raise ValueError(f"Fila {numero}: escribe tiempo y temperatura separados por coma.")
        try:
            filas.append((float(partes[0]), float(partes[1])))
        except ValueError as error:
            raise ValueError(f"Fila {numero}: ambos valores deben ser números.") from error
    if len(filas) < 2:
        raise ValueError("Ingresa al menos dos pares de datos.")
    datos = np.asarray(filas, dtype=float)
    return datos[:, 0], datos[:, 1]


def _hacer_analisis(t, T, T_amb, etiqueta, comparaciones):
    resultado, r2, residuos, validos = _analizar(t, T, T_amb)
    comparacion = {
        "t": np.asarray(t)[validos].copy(),
        "T": np.asarray(T)[validos].copy(),
        "T_amb": T_amb,
        "resultado": resultado,
        "r2": r2,
        "etiqueta": etiqueta,
    }
    anteriores = list(comparaciones)
    figura = _crear_figura_superficie(t, T, T_amb, resultado, r2, anteriores)
    return {
        "t": np.asarray(t), "T": np.asarray(T), "T_amb": T_amb,
        "resultado": resultado, "r2": r2, "residuos": residuos,
        "comparaciones": anteriores + [comparacion], "figura": figura,
        "etiqueta": etiqueta,
    }


def _dibujar_analisis(pantalla, mouse, campo_amb, campo_datos, error, hay_datos):
    _marco(pantalla, "Laboratorio de análisis", "Ajusta datos del juego o ingresa mediciones experimentales.")
    _panel(pantalla, pygame.Rect(38, 142, 1104, 425), acento=ACENTO,
           color=SUPERFICIE, radio=18)
    campo_amb.dibujar(pantalla, "T ambiente (°C)")
    campo_datos.dibujar(pantalla, "Datos experimentales", "Ejemplo: 0, 90.0")
    rects = [
        _boton(pantalla, (25, 600, 250, 58), "Analizar datos escritos", mouse),
        _boton(pantalla, (310, 600, 250, 58), "Usar última simulación", mouse,
               deshabilitado=not hay_datos),
        _boton(pantalla, (595, 600, 250, 58), "Limpiar comparaciones", mouse, color=ROJO),
        _boton(pantalla, (880, 600, 250, 58), "Volver al menú", mouse),
    ]
    _dibujar_error(pantalla, error)
    return rects


def _dibujar_personalizado(pantalla, mouse, campos, error, ruido_std,
                           campo_tau, modo_k_fisico):
    subtitulo = "Define el objeto y explora cómo cambia su temperatura."
    _marco(pantalla, "Crea tu objeto", subtitulo)
    panel = pygame.Rect(75, 145, 1030, 465)
    _panel(pantalla, panel, acento=ACENTO, radio=14)
    boton_directa = _boton(pantalla, (330, 155, 235, 42), "Ingresar k", mouse,
                           color=(86, 112, 91) if not modo_k_fisico else AZUL)
    boton_fisica = _boton(pantalla, (585, 155, 265, 42), "Calcular k desde τ", mouse,
                          color=(86, 112, 91) if modo_k_fisico else AZUL)
    campos[4].rect.topleft = (700, 350) if modo_k_fisico else (140, 455)
    campos[0].dibujar(pantalla, "Nombre o descripción del objeto")
    if not modo_k_fisico:
        campos[1].dibujar(pantalla, "T inicial T0 (°C)")
        campos[2].dibujar(pantalla, "T ambiente (°C)")
        campos[3].dibujar(pantalla, "k (1/s)")
        campos[4].dibujar(pantalla, "Meta (°C)")
    else:
        campos[1].dibujar(pantalla, "T inicial T0 (°C)")
        campos[2].dibujar(pantalla, "T ambiente (°C)")
        campos[4].dibujar(pantalla, "Meta (°C)")
        campo_tau.dibujar(pantalla, "Tiempo característico τ (s)")
        try:
            tau = float(campo_tau.texto.strip())
            if not math.isfinite(tau) or tau <= 0:
                raise ValueError
            k_calculada = 1 / tau
            _texto(pantalla, f"k = 1/τ = 1/{tau:g} = {k_calculada:.6g} 1/s",
                   (430, 480), _FUENTE_CHICA, (119, 224, 177))
        except ValueError:
            _texto(pantalla, "τ debe ser un número positivo; k se expresa en 1/s.",
                   (430, 480), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"Ruido de medición σ: {ruido_std:.1f} °C", (425, 445 if not modo_k_fisico else 515), _FUENTE_CHICA)
    pista = pygame.Rect(430, 478 if not modo_k_fisico else 548, 540, 8)
    pygame.draw.rect(pantalla, (82, 101, 123), pista, border_radius=4)
    avance = (ruido_std / 2.0) * pista.width
    pygame.draw.rect(pantalla, AZUL_HOVER, (pista.x, pista.y, avance, pista.height), border_radius=4)
    pygame.draw.circle(pantalla, TEXTO, (round(pista.x + avance), pista.centery), 10)
    _texto(pantalla, "0 °C", (425, pista.y + 12), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, "2 °C", (935, pista.y + 12), _FUENTE_CHICA, SECUNDARIO)
    nota = (
        "τ resume la rapidez térmica del objeto y su entorno; k = 1/τ."
        if modo_k_fisico else
        "Un k mayor significa un cambio térmico más rápido. σ representa el ruido del termómetro."
    )
    _texto_ajustado(
        pantalla, nota, (130, 580), 920, _FUENTE_CHICA, SECUNDARIO,
        max_lineas=1, alto_linea=20,
    )
    rects = [
        boton_directa, boton_fisica,
        _boton(pantalla, (330, 625, 250, 56), "Iniciar simulación", mouse, color=VERDE),
        _boton(pantalla, (610, 625, 240, 56), "Volver a escenarios", mouse, color=ROJO),
    ]
    _dibujar_error(pantalla, error)
    return rects


def _escenario_personalizado(campos, ruido_std=0.3, modo_k_fisico=False, campo_tau=None):
    nombre = campos[0].texto.strip()
    if not nombre:
        raise ValueError("Escribe un nombre para el objeto.")
    try:
        T0, T_amb = (float(campo.texto.strip()) for campo in campos[1:3])
        meta = float(campos[4].texto.strip())
    except ValueError as excepcion:
        raise ValueError("Las temperaturas y la meta deben ser números válidos.") from excepcion
    if modo_k_fisico:
        try:
            tau = float(campo_tau.texto.strip())
        except ValueError as excepcion:
            raise ValueError("El tiempo característico τ debe ser un número válido.") from excepcion
        if not math.isfinite(tau) or tau <= 0:
            raise ValueError("El tiempo característico τ debe ser mayor que cero.")
        k = 1 / tau
    else:
        try:
            k = float(campos[3].texto.strip())
        except ValueError as excepcion:
            raise ValueError("k debe ser un número válido.") from excepcion
    if not all(math.isfinite(valor) for valor in (T0, T_amb, k, meta)):
        raise ValueError("Los valores deben ser números finitos.")
    if math.isclose(T0, T_amb):
        raise ValueError("T0 debe diferir de la temperatura ambiente para iniciar un cambio térmico.")
    if k <= 0:
        raise ValueError("k debe ser mayor que cero.")
    if not min(T0, T_amb) < meta < max(T0, T_amb):
        raise ValueError("La meta debe quedar entre T0 y la temperatura ambiente, sin incluirlos.")
    return {
        "nombre": nombre, "T0_rango": (T0, T0), "T_amb": T_amb,
        "k_rango": (k, k), "meta": meta,
        "ruido_std": ruido_std,
        "color_frio": (63, 182, 201), "color_calido": (232, 135, 58),
        "descripcion": "Objeto definido por el usuario.",
        "condiciones": [("Sin intervención", 1.0), ("Ventilador", 1.7), ("Aislante", 0.55)],
    }


def _dibujar_guia(pantalla, resultado, mouse):
    if resultado is None:
        T_amb, T0, k = 22.0, 90.0, 0.04
        tiempos = np.arange(0.0, 25.0, 5.0)
        temperaturas = T_amb + (T0 - T_amb) * np.exp(-k * tiempos)
        ajuste = analisis.ajustar_modelo(tiempos, temperaturas, T_amb)
        r2 = analisis.calcular_r2(tiempos, temperaturas, T_amb, ajuste["k"], ajuste["T0"])
        etiqueta = "Ejemplo guiado"
    else:
        T_amb = float(resultado["T_amb"])
        tiempos = np.asarray(resultado["t"], dtype=float)
        temperaturas = np.asarray(resultado["T"], dtype=float)
        ajuste = resultado["resultado"]
        r2 = float(resultado["r2"])
        etiqueta = resultado["etiqueta"]

    validos = (np.isfinite(tiempos) & np.isfinite(temperaturas)
               & (np.abs(temperaturas - T_amb) > 0))
    t, T = tiempos[validos], temperaturas[validos]
    deltas = T - T_amb
    logs = np.log(np.abs(deltas))
    predichas = T_amb + (ajuste["T0"] - T_amb) * np.exp(-ajuste["k"] * t)
    residuos = T - predichas
    m, b = ajuste["pendiente"], ajuste["intercepto"]
    _marco(pantalla, "Cálculo paso a paso", f"{etiqueta} · calentamiento o enfriamiento · ajuste de k y T0")

    panel = pygame.Rect(40, 130, 1100, 62)
    _panel(pantalla, panel, acento=ACENTO, radio=10)
    _texto(pantalla, "1 · Modelo de Newton", (58, 141), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, "T(t) = T_amb + (T0 − T_amb) · e^(−k·t)", (58, 165), _FUENTE, TEXTO)

    if len(t):
        delta_ejemplo = deltas[0]
        log_ejemplo = logs[0]
        temp_ejemplo = T[0]
        tiempo_ejemplo = t[0]
    else:
        delta_ejemplo = log_ejemplo = temp_ejemplo = tiempo_ejemplo = 0.0
    pasos = [
        ("2 · Restar el ambiente", f"ΔT = T − T_amb\n{temp_ejemplo:.2f} − {T_amb:.2f} = {delta_ejemplo:.3f} °C"),
        ("3 · Aplicar logaritmo", f"y = ln(|ΔT|)\nln({abs(delta_ejemplo):.3f}) = {log_ejemplo:.4f}"),
        ("4 · Ajustar una recta", "y = b + m·t\nla pendiente m representa −k"),
    ]
    for indice, (titulo, detalle) in enumerate(pasos):
        x = 40 + indice * 370
        caja = pygame.Rect(x, 205, 350, 100)
        _panel(pantalla, caja, acento=(255, 213, 120), radio=10)
        _texto(pantalla, titulo, (x + 16, 218), _FUENTE_CHICA, (255, 213, 120))
        for fila, linea in enumerate(detalle.split("\n")):
            _texto(pantalla, linea, (x + 16, 250 + fila * 25), _FUENTE_CHICA)

    caja = pygame.Rect(40, 318, 1100, 80)
    _panel(pantalla, caja, acento=ACENTO, radio=10)
    _texto(pantalla, f"5 · Recuperar los parámetros  |  m = {m:.6f},  b = {b:.6f}",
           (58, 330), _FUENTE_CHICA, SECUNDARIO)
    signo = "+" if ajuste["T0"] >= T_amb else "−"
    _texto_ajustado(pantalla,
        f"k = −m = {ajuste['k']:.6f} 1/s · T0 = T_amb {signo} e^b = {ajuste['T0']:.3f} °C",
        (58, 356), 1050, _FUENTE_CHICA, max_lineas=2, alto_linea=22)

    tabla = pygame.Rect(40, 410, 1100, 180)
    _panel(pantalla, tabla, radio=10)
    columnas = [(58, "t (s)"), (180, "T medida"), (310, "ΔT"),
                (440, "ln(|ΔT|)"), (575, "T modelo"), (740, "Residuo")]
    for x, titulo in columnas:
        _texto(pantalla, titulo, (x, 425), _FUENTE_CHICA, (255, 213, 120))
    for fila, indice in enumerate(range(min(5, len(t)))):
        y = 454 + fila * 25
        valores = (f"{t[indice]:.2f}", f"{T[indice]:.3f}", f"{deltas[indice]:.3f}",
                   f"{logs[indice]:.4f}", f"{predichas[indice]:.3f}", f"{residuos[indice]:+.3f} °C")
        for (x, _), valor in zip(columnas, valores):
            _texto(pantalla, valor, (x, y), _FUENTE_CHICA, SECUNDARIO)

    _texto_ajustado(pantalla,
        f"6 · R² = 1 − Σ(Tobs−Tmodelo)² / Σ(Tobs−Tmedia)² = {r2:.4f}",
        (50, 600), ANCHO - 100, _FUENTE_CHICA, SECUNDARIO, max_lineas=2, alto_linea=22)
    if r2 >= 0.9:
        interpretacion = "R² alto: la curva sigue de cerca los datos."
    elif r2 >= 0:
        interpretacion = "R² bajo: hay diferencias entre el modelo y las mediciones."
    else:
        interpretacion = "R² negativo: el ajuste predice peor que usar la temperatura media."
    _texto_ajustado(pantalla,
        f"Residuos = T medida − T modelo. {interpretacion} ln(|T−T_amb|) requiere T distinta del ambiente.",
        (50, 648), ANCHO - 100, _FUENTE_CHICA, SECUNDARIO, max_lineas=2, alto_linea=20)
    return [
        _boton(pantalla, (ANCHO // 2 - 250, 704, 210, 46), "Volver", mouse),
        _boton(pantalla, (ANCHO // 2 + 40, 704, 210, 46), "Quiz rápido", mouse, color=(86, 112, 91)),
    ]


_PREGUNTAS_QUIZ = [
    ("Si duplicas k y mantienes T y T_amb, ¿qué pasa con |dT/dt|?",
     ["Se duplica", "Se reduce a la mitad", "No cambia"], 0,
     "dT/dt = −k(T−T_amb). Con la misma diferencia de temperatura, duplicar k duplica la rapidez del cambio."),
    ("¿Qué ocurre cuando T = T_amb?",
     ["La tasa es cero", "La temperatura sigue bajando igual", "La tasa es −k"], 0,
     "La diferencia T−T_amb vale cero, así que dT/dt también. El objeto se aproxima al ambiente de forma asintótica."),
    ("Si T está por debajo del ambiente, ¿qué signo tiene dT/dt?",
     ["Negativo: se enfría", "Positivo: se calienta", "Cero siempre"], 1,
     "T−T_amb es negativo; al multiplicar por −k, la tasa queda positiva. El mismo modelo describe calentamiento hacia el ambiente."),
]


def _dibujar_quiz(pantalla, mouse, indice, seleccion, aciertos):
    _marco(pantalla, "¿Qué pasaría si...?", "Usa la ecuación para predecir antes de mirar la explicación.")
    panel = pygame.Rect(100, 145, 980, 485)
    _panel(pantalla, panel, acento=(255, 213, 120), radio=14)
    if indice >= len(_PREGUNTAS_QUIZ):
        _texto(pantalla, f"Resultado: {aciertos} de {len(_PREGUNTAS_QUIZ)} correctas",
               (ANCHO // 2, 270), _FUENTE_TITULO, centro=True)
        _texto_ajustado(pantalla, "Revisa las explicaciones en la guía y prueba el cambio de parámetros en una corrida.",
                        (180, 350), 820, _FUENTE, SECUNDARIO, max_lineas=2, alto_linea=34)
        return [_boton(pantalla, (ANCHO // 2 - 120, 550, 240, 54), "Volver a la guía", mouse)]

    pregunta, opciones, correcta, explicacion = _PREGUNTAS_QUIZ[indice]
    _texto(pantalla, f"Pregunta {indice + 1} de {len(_PREGUNTAS_QUIZ)}", (150, 175), _FUENTE_CHICA, (255, 213, 120))
    _texto_ajustado(pantalla, pregunta, (150, 220), 850, _FUENTE, TEXTO, max_lineas=2, alto_linea=34)
    if seleccion is None:
        rects = []
        for i, opcion in enumerate(opciones):
            rects.append(_boton(pantalla, (230, 330 + i * 75, 720, 58), opcion, mouse))
        return rects

    correcto = seleccion == correcta
    _texto(pantalla, "Correcto" if correcto else f"La respuesta correcta es: {opciones[correcta]}",
           (150, 350), _FUENTE, (119, 224, 177) if correcto else (255, 170, 150))
    _texto_ajustado(pantalla, explicacion, (150, 405), 850, _FUENTE_CHICA, SECUNDARIO,
                    max_lineas=3, alto_linea=28)
    siguiente = "Ver resultado" if indice == len(_PREGUNTAS_QUIZ) - 1 else "Siguiente"
    return [_boton(pantalla, (ANCHO // 2 - 110, 550, 220, 54), siguiente, mouse)]


def _dibujar_resultados(pantalla, resultado, mouse, scroll):
    _marco(pantalla, "Resultados del análisis", "La gráfica está integrada en esta misma ventana.")
    grafica = pygame.transform.smoothscale(resultado["figura"], (730, 500))
    pantalla.blit(grafica, (28, 130))
    panel = pygame.Rect(780, 132, 370, 470)
    _panel(pantalla, panel, acento=ACENTO, radio=10)
    ajuste = resultado["resultado"]
    _texto(pantalla, resultado["etiqueta"], (802, 154), _FUENTE)
    _texto(pantalla, f"k estimada: {ajuste['k']:.6f} 1/s", (802, 204), _FUENTE_CHICA)
    _texto(pantalla, f"T0 estimada: {ajuste['T0']:.3f} °C", (802, 238), _FUENTE_CHICA)
    _texto(pantalla, f"R²: {resultado['r2']:.5f}", (802, 272), _FUENTE_CHICA)
    _texto(pantalla, "Residuos (T real − T modelo):", (802, 324), _FUENTE_CHICA)
    residuos = resultado["residuos"]
    inicio = max(0, min(scroll, max(0, len(residuos) - 9)))
    for indice, residuo in enumerate(residuos[inicio:inicio + 9], start=inicio):
        _texto(pantalla, f"{indice + 1:02d}: {residuo:+.4f} °C",
               (808, 360 + (indice - inicio) * 23), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"Curvas en comparación: {len(resultado['comparaciones'])}",
           (802, 570), _FUENTE_CHICA, SECUNDARIO)
    rects = [
        _boton(pantalla, (20, 650, 185, 58), "Analizar otra corrida", mouse),
        _boton(pantalla, (305, 650, 190, 58), "Limpiar comparaciones", mouse, color=ROJO),
        _boton(pantalla, (595, 650, 245, 58), "Explicar cálculo", mouse, color=(86, 112, 91)),
        _boton(pantalla, (940, 650, 220, 58), "Volver al menú", mouse),
    ]
    _texto(pantalla, "↑/↓: recorrer residuos", (795, 620), _FUENTE_CHICA, SECUNDARIO)
    return rects


def main():
    """Bucle de pantallas; todos los eventos y textos permanecen en Pygame."""
    pantalla, reloj = iniciar_pygame()
    pantalla_actual = "menu"
    error = ""
    datos_juego = None
    T_amb_juego = None
    comparaciones = []
    resultado_actual = None
    scroll_residuos = 0
    puntos_total = 0
    medallas = {"Oro": 0, "Plata": 0, "Bronce": 0}
    quiz_indice = 0
    quiz_seleccion = None
    quiz_aciertos = 0
    ruido_personalizado = 0.3
    modo_k_fisico = False
    campo_amb = CampoTexto((62, 190, 230, 42), "22")
    campo_datos = CampoTexto((62, 286, 720, 270), multilinea=True)
    campos_personalizados = [
        CampoTexto((140, 245, 700, 44), "Mi objeto", limite=36),
        CampoTexto((140, 350, 210, 42), "90"),
        CampoTexto((420, 350, 210, 42), "22"),
        CampoTexto((700, 350, 210, 42), "0.04"),
        CampoTexto((140, 455, 210, 42), "60"),
    ]
    campo_tau = CampoTexto((140, 455, 240, 42), "65")
    pygame.key.start_text_input()

    while True:
        delta_real = reloj.tick(FPS) / 1000.0
        mouse = pygame.mouse.get_pos()
        rects = []

        if pantalla_actual == "menu":
            dibujar_menu_principal(pantalla, puntos_total, medallas)
            rects = [pygame.Rect(70, 572, 320, 82), pygame.Rect(430, 572, 320, 82),
                     pygame.Rect(790, 572, 320, 82)]
        elif pantalla_actual == "escenarios":
            dibujar_menu_escenarios(pantalla, puntos_total)
        elif pantalla_actual == "personalizado":
            rects = _dibujar_personalizado(
                pantalla, mouse, campos_personalizados, error, ruido_personalizado,
                campo_tau, modo_k_fisico,
            )
        elif pantalla_actual == "analisis":
            rects = _dibujar_analisis(
                pantalla, mouse, campo_amb, campo_datos, error,
                datos_juego is not None and len(datos_juego) >= 2,
            )
        elif pantalla_actual == "resultados":
            rects = _dibujar_resultados(pantalla, resultado_actual, mouse, scroll_residuos)
        elif pantalla_actual == "guia":
            rects = _dibujar_guia(pantalla, resultado_actual, mouse)
        elif pantalla_actual == "quiz":
            rects = _dibujar_quiz(pantalla, mouse, quiz_indice, quiz_seleccion, quiz_aciertos)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                return
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                if pantalla_actual == "menu":
                    pygame.quit()
                    return
                if pantalla_actual == "guia":
                    pantalla_actual = "resultados" if resultado_actual is not None else "menu"
                elif pantalla_actual == "quiz":
                    pantalla_actual = "guia"
                elif pantalla_actual == "personalizado":
                    pantalla_actual = "escenarios"
                else:
                    pantalla_actual = "menu"
                error = ""
                continue

            if pantalla_actual == "analisis":
                campo_amb.manejar_evento(evento)
                campo_datos.manejar_evento(evento)
            elif pantalla_actual == "personalizado":
                campos_visibles = (
                    [campos_personalizados[0], campos_personalizados[1],
                     campos_personalizados[2], campos_personalizados[4], campo_tau]
                    if modo_k_fisico else campos_personalizados
                )
                for campo in campos_visibles:
                    campo.manejar_evento(evento)

            if evento.type == pygame.KEYDOWN:
                if pantalla_actual == "menu":
                    if evento.key in (pygame.K_RETURN, pygame.K_1):
                        pantalla_actual = "escenarios"
                    elif evento.key == pygame.K_2:
                        pantalla_actual = "analisis"
                    elif evento.key == pygame.K_3:
                        pantalla_actual = "guia"
                elif pantalla_actual == "resultados":
                    if evento.key == pygame.K_DOWN:
                        scroll_residuos += 1
                    elif evento.key == pygame.K_UP:
                        scroll_residuos = max(0, scroll_residuos - 1)

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if pantalla_actual == "menu":
                    if rects[0].collidepoint(evento.pos):
                        pantalla_actual = "escenarios"
                    elif rects[1].collidepoint(evento.pos):
                        pantalla_actual = "analisis"
                    elif rects[2].collidepoint(evento.pos):
                        pantalla_actual = "guia"
                elif pantalla_actual == "escenarios":
                    for indice, (clave, _) in enumerate(listar_escenarios()):
                        x, y = 100 + (indice % 2) * 500, 155 + (indice // 2) * 220
                        if pygame.Rect(x, y, 450, 180).collidepoint(evento.pos):
                            escenario = obtener_escenario(clave)
                            partida = correr_simulacion(pantalla, reloj, clave)
                            datos_juego = partida["datos"]
                            puntos_total += partida["puntos"]
                            if partida["medalla"]:
                                medallas[partida["medalla"]] += 1
                            T_amb_juego = escenario["T_amb"]
                            pantalla_actual = "analisis"
                            break
                    if pygame.Rect(300, 590, 580, 70).collidepoint(evento.pos):
                        pantalla_actual = "personalizado"
                        error = ""
                elif pantalla_actual == "personalizado":
                    if rects[0].collidepoint(evento.pos):
                        modo_k_fisico = False
                        campo_tau.activo = False
                        error = ""
                    elif rects[1].collidepoint(evento.pos):
                        modo_k_fisico = True
                        campos_personalizados[3].activo = False
                        error = ""
                    elif rects[2].collidepoint(evento.pos):
                        try:
                            escenario = _escenario_personalizado(
                                campos_personalizados, ruido_personalizado,
                                modo_k_fisico, campo_tau,
                            )
                            partida = correr_simulacion(pantalla, reloj, "personalizado", escenario)
                            datos_juego = partida["datos"]
                            puntos_total += partida["puntos"]
                            if partida["medalla"]:
                                medallas[partida["medalla"]] += 1
                            T_amb_juego = escenario["T_amb"]
                            pantalla_actual = "analisis"
                            error = ""
                        except ValueError as excepcion:
                            error = str(excepcion)
                    elif rects[3].collidepoint(evento.pos):
                        pantalla_actual = "escenarios"
                        error = ""
                    elif pygame.Rect(420, 462 if not modo_k_fisico else 532, 565, 42).collidepoint(evento.pos):
                        ruido_personalizado = max(0.0, min(2.0, (evento.pos[0] - 430) / 540 * 2.0))
                elif pantalla_actual == "analisis":
                    if rects[0].collidepoint(evento.pos):
                        try:
                            tiempos, temperaturas = _datos_manuales(campo_datos.texto)
                            T_amb = float(campo_amb.texto.strip())
                            resultado_actual = _hacer_analisis(
                                tiempos, temperaturas, T_amb,
                                f"Dataset {len(comparaciones) + 1}", comparaciones,
                            )
                            comparaciones = resultado_actual["comparaciones"]
                            pantalla_actual = "resultados"
                            error = ""
                        except ValueError as excepcion:
                            error = str(excepcion)
                    elif (
                        rects[1].collidepoint(evento.pos)
                        and datos_juego is not None
                        and len(datos_juego) >= 2
                    ):
                        try:
                            datos = np.asarray(datos_juego, dtype=float)
                            resultado_actual = _hacer_analisis(
                                datos[:, 0], datos[:, 1], T_amb_juego,
                                f"Simulación {len(comparaciones) + 1}", comparaciones,
                            )
                            comparaciones = resultado_actual["comparaciones"]
                            pantalla_actual = "resultados"
                            error = ""
                        except ValueError as excepcion:
                            error = str(excepcion)
                    elif rects[2].collidepoint(evento.pos):
                        comparaciones = []
                        error = "Se limpiaron las curvas guardadas para comparar."
                    elif rects[3].collidepoint(evento.pos):
                        pantalla_actual = "menu"
                        error = ""
                elif pantalla_actual == "resultados":
                    if rects[0].collidepoint(evento.pos):
                        pantalla_actual = "analisis"
                        campo_datos.texto = ""
                        error = ""
                    elif rects[1].collidepoint(evento.pos):
                        comparaciones = []
                        # Mantiene visible el análisis actual, pero sin corridas anteriores.
                        actual = resultado_actual["comparaciones"][-1]
                        comparaciones.append(actual)
                        resultado_actual = _hacer_analisis(
                            resultado_actual["t"], resultado_actual["T"],
                            resultado_actual["T_amb"], resultado_actual["etiqueta"], [],
                        )
                        comparaciones = resultado_actual["comparaciones"]
                    elif rects[2].collidepoint(evento.pos):
                        pantalla_actual = "guia"
                    elif rects[3].collidepoint(evento.pos):
                        pantalla_actual = "menu"

                elif pantalla_actual == "guia":
                    if rects and rects[0].collidepoint(evento.pos):
                        pantalla_actual = "resultados" if resultado_actual is not None else "menu"
                    elif len(rects) > 1 and rects[1].collidepoint(evento.pos):
                        quiz_indice = 0
                        quiz_seleccion = None
                        quiz_aciertos = 0
                        pantalla_actual = "quiz"
                elif pantalla_actual == "quiz":
                    if quiz_indice < len(_PREGUNTAS_QUIZ) and quiz_seleccion is None:
                        for indice_opcion, rect in enumerate(rects):
                            if rect.collidepoint(evento.pos):
                                quiz_seleccion = indice_opcion
                                if indice_opcion == _PREGUNTAS_QUIZ[quiz_indice][2]:
                                    quiz_aciertos += 1
                                break
                    elif rects and rects[0].collidepoint(evento.pos):
                        if quiz_indice >= len(_PREGUNTAS_QUIZ):
                            pantalla_actual = "guia"
                        elif quiz_indice == len(_PREGUNTAS_QUIZ) - 1:
                            quiz_indice += 1
                            quiz_seleccion = None
                        else:
                            quiz_indice += 1
                            quiz_seleccion = None

        pygame.display.flip()


if __name__ == "__main__":
    main()
