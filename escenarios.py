"""
escenarios.py
--------------
Define los escenarios jugables. Cada uno trae su propio T_amb (temperatura
ambiente) y un rango realista de k (constante de enfriamiento), para que
el usuario no tenga que inventar valores físicos.

Los rangos están centralizados aquí para que cada escenario pueda ajustarse
sin cambiar la lógica de simulación.
"""

# Cada escenario es un diccionario con:
#   nombre       -> texto que se muestra en el menú
#   T0_rango     -> (min, max) temperatura inicial del objeto, en °C
#   T_amb        -> temperatura ambiente fija del escenario, en °C
#   k_rango      -> (min, max) constante de enfriamiento típica
#   color_frio   -> color RGB del objeto cuando está en equilibrio
#   color_calido -> color RGB del objeto recién iniciado
#   descripcion  -> contexto que se muestra al usuario (para el "reto")

ESCENARIOS = {
    "forense": {
        "nombre": "Escena forense",
        "T0_rango": (36.0, 37.5),   # temperatura corporal normal
        "T_amb": 20.0,
        "k_rango": (0.03, 0.08),
        "color_frio": (63, 182, 201),
        "color_calido": (200, 80, 90),
        "descripcion": "Estima desde hace cuánto ocurrió el deceso a partir de la temperatura medida.",
        "meta": 30.0,
        "condiciones": [("Ambiente quieto", 1.0), ("Ventilación", 1.7), ("Cámara aislada", 0.55)],
    },
    "cafe": {
        "nombre": "Taza de café",
        "T0_rango": (80.0, 95.0),
        "T_amb": 22.0,
        "k_rango": (0.02, 0.06),
        "color_frio": (63, 182, 201),
        "color_calido": (232, 135, 58),
        "descripcion": "¿Cuánto tiempo falta para que el café esté a temperatura para beber?",
        "meta": 60.0,
        "condiciones": [("Sin tapa", 1.0), ("Abanico", 1.7), ("Tapa puesta", 0.55)],
    },
    "motor": {
        "nombre": "Motor de auto",
        "T0_rango": (95.0, 110.0),
        "T_amb": 25.0,
        "k_rango": (0.005, 0.02),
        "color_frio": (63, 182, 201),
        "color_calido": (230, 60, 40),
        "descripcion": "¿Cuánto debe esperar el mecánico antes de manipular el motor con seguridad?",
        "meta": 50.0,
        "condiciones": [("Sin cubierta", 1.0), ("Aire forzado", 1.7), ("Cubierta aislante", 0.55)],
    },
    "horno": {
        "nombre": "Comida recién horneada",
        "T0_rango": (150.0, 200.0),
        "T_amb": 24.0,
        "k_rango": (0.01, 0.04),
        "color_frio": (63, 182, 201),
        "color_calido": (245, 160, 40),
        "descripcion": "¿Cuánto falta para que esté lista para servir sin quemar?",
        "meta": 65.0,
        "condiciones": [("Bandeja abierta", 1.0), ("Corriente de aire", 1.7), ("Cubierto", 0.55)],
    },
}


def obtener_escenario(clave: str) -> dict:
    """
    Devuelve el diccionario de parámetros del escenario pedido.
    """
    try:
        return ESCENARIOS[clave]
    except KeyError:
        opciones = ", ".join(ESCENARIOS)
        raise ValueError(
            f"Escenario desconocido: {clave!r}. Opciones disponibles: {opciones}."
        ) from None


def listar_escenarios() -> list:
    """
    Devuelve una lista de (clave, nombre) para pintar el menú de selección.
    """
    return [(clave, datos["nombre"]) for clave, datos in ESCENARIOS.items()]
