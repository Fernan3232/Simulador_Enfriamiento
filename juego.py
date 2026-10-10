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
TEXTO = (238, 243, 250)
SECUNDARIO = (173, 188, 207)
AZUL = (51, 121, 174)
AZUL_HOVER = (71, 151, 207)
ROJO = (178, 72, 74)
VERDE = (62, 145, 105)

_FUENTE = None
_FUENTE_CHICA = None
_FUENTE_TITULO = None


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
    fondo = (69, 75, 86) if deshabilitado else (AZUL_HOVER if hover else color)
    pygame.draw.rect(pantalla, fondo, rect, border_radius=9)
    pygame.draw.rect(pantalla, (116, 143, 170), rect, 1, border_radius=9)
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
    pantalla.fill(FONDO)
    _texto(pantalla, titulo, (42, 28), _FUENTE_TITULO)
    if subtitulo:
        _texto(pantalla, subtitulo, (45, 86), _FUENTE_CHICA, SECUNDARIO)


def _dibujar_error(pantalla, mensaje):
    if mensaje:
        caja = pygame.Rect(42, ALTO - 58, ANCHO - 84, 48)
        pygame.draw.rect(pantalla, (93, 42, 48), caja, border_radius=6)
        _texto_ajustado(pantalla, mensaje, (54, ALTO - 52), ANCHO - 110,
                        _FUENTE_CHICA, (255, 224, 224), max_lineas=2, alto_linea=17)


def iniciar_pygame():
    """Inicializa Pygame y devuelve la ventana junto con su reloj."""
    global _FUENTE, _FUENTE_CHICA, _FUENTE_TITULO
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Laboratorio virtual | Ley de Enfriamiento de Newton")
    _FUENTE = pygame.font.Font(None, 32)
    _FUENTE_CHICA = pygame.font.Font(None, 25)
    _FUENTE_TITULO = pygame.font.Font(None, 48)
    return pantalla, pygame.time.Clock()


def dibujar_menu_principal(pantalla, puntos=0, medallas=None) -> None:
    _marco(pantalla, "Laboratorio virtual", "Ley de Enfriamiento de Newton")
    _texto(pantalla, "Explora el modelo, toma mediciones y compara resultados.",
           (ANCHO // 2, 185), _FUENTE, SECUNDARIO, centro=True)
    mouse = pygame.mouse.get_pos()
    _boton(pantalla, (300, 280, 270, 94), "Modo Juego", mouse)
    _boton(pantalla, (610, 280, 270, 94), "Modo Análisis", mouse)
    _boton(pantalla, (455, 410, 270, 74), "Aprender el cálculo", mouse, color=(86, 112, 91))
    _texto(pantalla, "Toda la interacción ocurre en esta ventana.",
           (ANCHO // 2, 520), _FUENTE_CHICA, SECUNDARIO, centro=True)
    medallas = medallas or {"Oro": 0, "Plata": 0, "Bronce": 0}
    _texto(pantalla, f"Puntos: {puntos}    Oro {medallas['Oro']}   Plata {medallas['Plata']}   Bronce {medallas['Bronce']}",
           (ANCHO // 2, 575), _FUENTE_CHICA, (255, 213, 120), centro=True)
    _texto(pantalla, "Esc: salir", (ANCHO - 130, ALTO - 42), _FUENTE_CHICA, SECUNDARIO)


def dibujar_menu_escenarios(pantalla, puntos=0) -> None:
    _marco(pantalla, "Elige un escenario", "Cada escenario tiene un ambiente y parámetros propios.")
    mouse = pygame.mouse.get_pos()
    for indice, (clave, nombre) in enumerate(listar_escenarios()):
        escenario = obtener_escenario(clave)
        x, y = 100 + (indice % 2) * 500, 155 + (indice // 2) * 220
        rect = pygame.Rect(x, y, 450, 180)
        pygame.draw.rect(pantalla, PANEL, rect, border_radius=12)
        pygame.draw.rect(
            pantalla, AZUL_HOVER if rect.collidepoint(mouse) else (71, 88, 109),
            rect, 2, border_radius=12,
        )
        pygame.draw.circle(pantalla, escenario["color_calido"], (x + 51, y + 50), 24)
        _texto(pantalla, nombre, (x + 91, y + 32), _FUENTE)
        _texto_ajustado(pantalla, escenario["descripcion"], (x + 25, y + 80),
                        400, _FUENTE_CHICA, SECUNDARIO, max_lineas=2, alto_linea=22)
        _texto(pantalla, f"T ambiente: {escenario['T_amb']:.1f} °C",
               (x + 25, y + 128), _FUENTE_CHICA)
        _texto(pantalla, f"k: {escenario['k_rango'][0]}–{escenario['k_rango'][1]} 1/s",
               (x + 240, y + 128), _FUENTE_CHICA)
        _texto(pantalla, f"Objetivo: llegar a {escenario['meta']:.1f} °C",
               (x + 25, y + 157), _FUENTE_CHICA, (255, 213, 120))
    personalizado = pygame.Rect(300, 590, 580, 70)
    pygame.draw.rect(pantalla, PANEL, personalizado, border_radius=12)
    pygame.draw.rect(pantalla, AZUL_HOVER if personalizado.collidepoint(mouse) else (71, 88, 109),
                     personalizado, 2, border_radius=12)
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
                   clave: str = "cafe", tiempo: float = 0.0) -> None:
    """Dibuja el objeto del escenario y su calor de forma animada."""
    color = color_interpolado(
        temp, escenario["T_amb"], T0,
        escenario["color_frio"], escenario["color_calido"],
    )
    cx, cy = ANCHO // 2, 385
    proporcion = 0.0 if T0 == escenario["T_amb"] else (
        (temp - escenario["T_amb"]) / (T0 - escenario["T_amb"])
    )
    proporcion = max(0.0, min(1.0, proporcion))

    # El resplandor y las ondas se apagan a medida que el objeto se enfría.
    halo = pygame.Surface((440, 390), pygame.SRCALPHA)
    pygame.draw.ellipse(halo, (*color, round(12 + 34 * proporcion)), (30, 55, 380, 280))
    pantalla.blit(halo, (cx - 220, cy - 205))
    pygame.draw.line(pantalla, (67, 82, 101), (cx - 190, 548), (cx + 190, 548), 3)
    for i in range(3):
        y = cy - 125 - i * 37
        fase = tiempo * (1.4 + i * .15) + i * 2.1
        x = cx + math.sin(fase) * (15 + i * 5)
        puntos = [(round(x + math.sin(fase + j * .65) * 9), y - j * 9) for j in range(7)]
        if proporcion > .05:
            pygame.draw.lines(pantalla, (205, 218, 229), False, puntos, max(1, round(1 + proporcion * 2)))

    if clave == "cafe":
        # Taza con asa, bebida y reflejo.
        pygame.draw.ellipse(pantalla, (9, 14, 23), (cx - 126, cy + 105, 260, 35))
        pygame.draw.circle(pantalla, (190, 205, 218), (cx + 111, cy + 7), 52, 12)
        pygame.draw.ellipse(pantalla, color, (cx - 106, cy - 87, 212, 217))
        pygame.draw.rect(pantalla, color, (cx - 105, cy - 3, 210, 117))
        pygame.draw.ellipse(pantalla, (235, 239, 241), (cx - 106, cy - 91, 212, 42), 5)
        bebida = color_interpolado(temp, escenario["T_amb"], T0, (92, 57, 38), (74, 39, 22))
        pygame.draw.ellipse(pantalla, bebida, (cx - 91, cy - 81, 182, 24))
        pygame.draw.line(pantalla, (255, 255, 255), (cx - 65, cy - 39), (cx - 48, cy + 55), 5)
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


def dibujar_hud(pantalla, t: float, temp: float, rate: float) -> None:
    panel = pygame.Rect(28, 132, 330, 125)
    pygame.draw.rect(pantalla, PANEL, panel, border_radius=10)
    _texto(pantalla, f"Tiempo: {t:7.1f} s", (48, 150), _FUENTE_CHICA)
    _texto(pantalla, f"Temperatura: {temp:6.2f} °C", (48, 186), _FUENTE_CHICA)
    _texto(pantalla, f"dT/dt: {rate: .3f} °C/s", (48, 222), _FUENTE_CHICA)


def _dibujar_progreso(pantalla, temp, escenario, T0, datos, tiempo):
    """Panel visual con termómetro, objetivo ambiente y últimas mediciones."""
    panel = pygame.Rect(858, 238, 292, 300)
    pygame.draw.rect(pantalla, (25, 37, 54), panel, border_radius=14)
    pygame.draw.rect(pantalla, (71, 88, 109), panel, 2, border_radius=14)
    _texto(pantalla, "PROGRESO DEL ENFRIAMIENTO", (878, 257), _FUENTE_CHICA)
    amb, inicial = escenario["T_amb"], T0
    proporcion = 0 if inicial == amb else max(0, min(1, (temp - amb) / (inicial - amb)))
    # Termómetro vertical; el marcador se desplaza desde el inicio hasta el ambiente.
    x, top, bottom = 902, 315, 468
    pygame.draw.line(pantalla, (104, 122, 143), (x, top), (x, bottom), 15)
    pygame.draw.circle(pantalla, (104, 122, 143), (x, bottom + 6), 17)
    y = round(bottom - proporcion * (bottom - top))
    pygame.draw.line(pantalla, color_interpolado(temp, amb, inicial, (63, 182, 201), (244, 112, 62)), (x, y), (x, bottom), 8)
    pygame.draw.circle(pantalla, color_interpolado(temp, amb, inicial, (63, 182, 201), (244, 112, 62)), (x, bottom + 6), 12)
    pygame.draw.line(pantalla, (223, 232, 239), (x + 15, top), (x + 25, top), 2)
    pygame.draw.line(pantalla, (223, 232, 239), (x + 15, bottom), (x + 25, bottom), 2)
    _texto(pantalla, f"{inicial:.1f}°", (x + 34, top - 10), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"{amb:.1f}° ambiente", (x + 34, bottom - 10), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"{temp:.1f} °C", (x + 34, y - 13), _FUENTE, TEXTO)
    _texto(pantalla, f"{round((1 - proporcion) * 100)}% del enfriamiento", (878, 489), _FUENTE_CHICA, SECUNDARIO)
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
    _texto(pantalla, "mediciones", (gx + 11, gy + gh + 8), _FUENTE_CHICA, SECUNDARIO)


def _sim_nuevo(escenario, clave):
    T0 = random.uniform(*escenario["T0_rango"])
    k = random.uniform(*escenario["k_rango"])
    return {
        "clave": clave, "escenario": escenario, "T0": T0, "k": k, "k_base": k,
        "t": 0.0, "pausada": True, "velocidad": VELOCIDAD_INICIAL,
        "siguiente_muestra": 0.0, "datos": [], "reto": None,
        "condicion": 0, "completada": False, "puntos": 0, "medalla": None,
    }


def _medir(sim, hasta):
    while sim["siguiente_muestra"] <= hasta:
        instante = sim["siguiente_muestra"]
        lectura = temperatura(instante, sim["T0"], sim["escenario"]["T_amb"], sim["k"])
        sim["datos"].append((instante, lectura + random.gauss(0, 0.3)))
        sim["siguiente_muestra"] += INTERVALO_MUESTRA


def _dibujar_simulacion(pantalla, sim, mouse, botones):
    escenario = sim["escenario"]
    _marco(pantalla, escenario["nombre"], escenario["descripcion"])
    nombres_condicion = " · ".join(item[0] for item in escenario["condiciones"])
    _texto(pantalla, f"Estrategias disponibles: {nombres_condicion}",
           (420, 111), _FUENTE_CHICA, SECUNDARIO)
    t = sim["t"]
    temp = temperatura(t, sim["T0"], escenario["T_amb"], sim["k"])
    dibujar_objeto(pantalla, temp, escenario, sim["T0"], sim["clave"], t)
    dibujar_hud(pantalla, t, temp, tasa_cambio(t, sim["T0"], escenario["T_amb"], sim["k"]))
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
    _texto(pantalla, f"META: llegar a {escenario['meta']:.1f} °C", (ANCHO // 2, 565),
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
            if temp_actual <= sim["escenario"]["meta"]:
                if len(sim["datos"]) < 2:
                    tiempo_meta = tiempo_para_alcanzar(
                        sim["escenario"]["meta"], sim["T0"],
                        sim["escenario"]["T_amb"], sim["k"],
                    )
                    lectura_meta = max(
                        sim["escenario"]["T_amb"] + 0.001,
                        sim["escenario"]["meta"] + random.gauss(0, 0.3),
                    )
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
    validos = np.isfinite(temps) & np.isfinite(tiempos) & (temps > T_amb)
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
    _texto(pantalla, "Temperatura ambiente (°C)", (62, 155), _FUENTE_CHICA)
    campo_amb.dibujar(pantalla, "T ambiente (°C)")
    _texto(pantalla, "Pares tiempo,temperatura — uno por línea", (62, 252), _FUENTE_CHICA)
    campo_datos.dibujar(pantalla, "Mediciones", "Ejemplo: 0, 90.0")
    rects = []
    rects.append(_boton(pantalla, (62, 600, 220, 58), "Analizar datos escritos", mouse))
    rects.append(_boton(
        pantalla, (300, 600, 245, 58), "Usar última simulación", mouse,
        deshabilitado=not hay_datos,
    ))
    rects.append(_boton(pantalla, (565, 600, 220, 58), "Limpiar comparaciones", mouse, color=ROJO))
    rects.append(_boton(pantalla, (805, 600, 180, 58), "Volver al menú", mouse))
    _texto(pantalla, "Puedes analizar varias corridas y superponer sus curvas.",
           (62, 690), _FUENTE_CHICA, SECUNDARIO)
    _dibujar_error(pantalla, error)
    return rects


def _dibujar_personalizado(pantalla, mouse, campos, error):
    _marco(pantalla, "Crea tu objeto", "El nombre es libre; el modelo usa sus temperaturas y su constante de enfriamiento.")
    panel = pygame.Rect(75, 145, 1030, 440)
    pygame.draw.rect(pantalla, PANEL, panel, border_radius=14)
    pygame.draw.rect(pantalla, (71, 88, 109), panel, 2, border_radius=14)
    campos[0].dibujar(pantalla, "Nombre o descripción del objeto")
    campos[1].dibujar(pantalla, "Temperatura inicial T0 (°C)")
    campos[2].dibujar(pantalla, "Temperatura ambiente (°C)")
    campos[3].dibujar(pantalla, "Constante k (1/s)")
    campos[4].dibujar(pantalla, "Meta de temperatura (°C)")
    _texto_ajustado(
        pantalla,
        "Para que sea un enfriamiento, T0 debe ser mayor que el ambiente; la meta debe quedar entre ambos valores y k debe ser positiva.",
        (130, 510), 920, _FUENTE_CHICA, SECUNDARIO, max_lineas=2, alto_linea=24,
    )
    rects = [
        _boton(pantalla, (345, 610, 250, 56), "Iniciar simulación", mouse, color=VERDE),
        _boton(pantalla, (625, 610, 210, 56), "Volver a escenarios", mouse, color=ROJO),
    ]
    _dibujar_error(pantalla, error)
    return rects


def _escenario_personalizado(campos):
    nombre = campos[0].texto.strip()
    if not nombre:
        raise ValueError("Escribe un nombre para el objeto.")
    try:
        T0, T_amb, k, meta = (float(campo.texto.strip()) for campo in campos[1:])
    except ValueError as excepcion:
        raise ValueError("Temperaturas, meta y k deben ser números válidos.") from excepcion
    if not all(math.isfinite(valor) for valor in (T0, T_amb, k, meta)):
        raise ValueError("Los valores deben ser números finitos.")
    if T0 <= T_amb:
        raise ValueError("T0 debe ser mayor que la temperatura ambiente para representar enfriamiento.")
    if k <= 0:
        raise ValueError("k debe ser mayor que cero.")
    if not T_amb < meta < T0:
        raise ValueError("La meta debe quedar entre la temperatura ambiente y T0.")
    return {
        "nombre": nombre, "T0_rango": (T0, T0), "T_amb": T_amb,
        "k_rango": (k, k), "meta": meta,
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

    validos = np.isfinite(tiempos) & np.isfinite(temperaturas) & (temperaturas > T_amb)
    t, T = tiempos[validos], temperaturas[validos]
    deltas = T - T_amb
    logs = np.log(deltas)
    predichas = T_amb + (ajuste["T0"] - T_amb) * np.exp(-ajuste["k"] * t)
    residuos = T - predichas
    m, b = ajuste["pendiente"], ajuste["intercepto"]
    _marco(pantalla, "Cálculo paso a paso", f"{etiqueta} · sigue cómo las mediciones producen k y T0")

    panel = pygame.Rect(40, 130, 1100, 62)
    pygame.draw.rect(pantalla, PANEL, panel, border_radius=10)
    _texto(pantalla, "1 · Modelo de enfriamiento", (58, 141), _FUENTE_CHICA, SECUNDARIO)
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
        ("3 · Aplicar logaritmo", f"y = ln(ΔT)\nln({delta_ejemplo:.3f}) = {log_ejemplo:.4f}"),
        ("4 · Ajustar una recta", "y = b + m·t\nla pendiente m representa −k"),
    ]
    for indice, (titulo, detalle) in enumerate(pasos):
        x = 40 + indice * 370
        caja = pygame.Rect(x, 205, 350, 100)
        pygame.draw.rect(pantalla, PANEL, caja, border_radius=10)
        _texto(pantalla, titulo, (x + 16, 218), _FUENTE_CHICA, (255, 213, 120))
        for fila, linea in enumerate(detalle.split("\n")):
            _texto(pantalla, linea, (x + 16, 250 + fila * 25), _FUENTE_CHICA)

    caja = pygame.Rect(40, 318, 1100, 80)
    pygame.draw.rect(pantalla, PANEL, caja, border_radius=10)
    _texto(pantalla, f"5 · Recuperar los parámetros  |  m = {m:.6f},  b = {b:.6f}",
           (58, 330), _FUENTE_CHICA, SECUNDARIO)
    _texto(pantalla, f"k = −m = {ajuste['k']:.6f} 1/s     ·     T0 = T_amb + e^b = {T_amb:.3f} + e^{b:.3f} = {ajuste['T0']:.3f} °C",
           (58, 358), _FUENTE_CHICA)

    tabla = pygame.Rect(40, 410, 1100, 180)
    pygame.draw.rect(pantalla, PANEL, tabla, border_radius=10)
    columnas = [(58, "t (s)"), (180, "T medida"), (310, "ΔT"),
                (440, "ln(ΔT)"), (575, "T modelo"), (740, "Residuo")]
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
        f"Residuos = T medida − T modelo. {interpretacion} El logaritmo solo existe cuando T > T_amb.",
        (50, 648), ANCHO - 100, _FUENTE_CHICA, SECUNDARIO, max_lineas=2, alto_linea=20)
    return [_boton(pantalla, (ANCHO // 2 - 110, 704, 220, 46), "Volver", mouse)]


def _dibujar_resultados(pantalla, resultado, mouse, scroll):
    _marco(pantalla, "Resultados del análisis", "La gráfica está integrada en esta misma ventana.")
    grafica = pygame.transform.smoothscale(resultado["figura"], (730, 455))
    pantalla.blit(grafica, (28, 135))
    panel = pygame.Rect(780, 132, 370, 470)
    pygame.draw.rect(pantalla, PANEL, panel, border_radius=10)
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
        _boton(pantalla, (25, 650, 205, 58), "Analizar otra corrida", mouse),
        _boton(pantalla, (240, 650, 220, 58), "Limpiar comparaciones", mouse, color=ROJO),
        _boton(pantalla, (470, 650, 300, 58), "Explicar cálculo", mouse, color=(86, 112, 91)),
        _boton(pantalla, (930, 650, 220, 58), "Volver al menú", mouse),
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
    campo_amb = CampoTexto((62, 190, 230, 42), "22")
    campo_datos = CampoTexto((62, 286, 720, 270), multilinea=True)
    campos_personalizados = [
        CampoTexto((140, 245, 700, 44), "Mi objeto", limite=36),
        CampoTexto((140, 350, 210, 42), "90"),
        CampoTexto((420, 350, 210, 42), "22"),
        CampoTexto((700, 350, 210, 42), "0.04"),
        CampoTexto((140, 455, 210, 42), "60"),
    ]
    pygame.key.start_text_input()

    while True:
        delta_real = reloj.tick(FPS) / 1000.0
        mouse = pygame.mouse.get_pos()
        rects = []

        if pantalla_actual == "menu":
            dibujar_menu_principal(pantalla, puntos_total, medallas)
            rects = [pygame.Rect(300, 280, 270, 94), pygame.Rect(610, 280, 270, 94),
                     pygame.Rect(455, 410, 270, 74)]
        elif pantalla_actual == "escenarios":
            dibujar_menu_escenarios(pantalla, puntos_total)
        elif pantalla_actual == "personalizado":
            rects = _dibujar_personalizado(pantalla, mouse, campos_personalizados, error)
        elif pantalla_actual == "analisis":
            rects = _dibujar_analisis(
                pantalla, mouse, campo_amb, campo_datos, error,
                datos_juego is not None and len(datos_juego) >= 2,
            )
        elif pantalla_actual == "resultados":
            rects = _dibujar_resultados(pantalla, resultado_actual, mouse, scroll_residuos)
        elif pantalla_actual == "guia":
            rects = _dibujar_guia(pantalla, resultado_actual, mouse)
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
                for campo in campos_personalizados:
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
                        try:
                            escenario = _escenario_personalizado(campos_personalizados)
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
                    elif rects[1].collidepoint(evento.pos):
                        pantalla_actual = "escenarios"
                        error = ""
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

        pygame.display.flip()


if __name__ == "__main__":
    main()
