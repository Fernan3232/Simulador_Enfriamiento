"""
simulacion.py
--------------
Contiene únicamente física y matemática pura (sin Pygame, sin dibujo).
Así puedes probar este módulo por separado, incluso desde la consola,
antes de meterlo al juego.
"""

import numpy as np


def temperatura(t: float, T0: float, T_amb: float, k: float) -> float:
    """
    Ley de Enfriamiento de Newton, solución analítica:
        T(t) = T_amb + (T0 - T_amb) * e^(-k*t)

    `t` se expresa en segundos y `k` en 1/segundos.
    """
    return float(T_amb + (T0 - T_amb) * np.exp(-k * t))


def tasa_cambio(t: float, T0: float, T_amb: float, k: float) -> float:
    """
    dT/dt evaluada en el instante t. Útil para mostrarla en pantalla
    como dato "en vivo" durante la simulación.

    El resultado se expresa en °C por segundo.
    """
    return float(-k * (temperatura(t, T0, T_amb, k) - T_amb))


def generar_dataset(T0: float, T_amb: float, k: float,
                     t_max: float, paso: float,
                     ruido_std: float = 0.0) -> np.ndarray:
    """
    Genera pares (t, T) simulando "mediciones" tomadas cada `paso` segundos
    desde t=0 hasta t_max. Si ruido_std > 0, le suma ruido gaussiano a cada
    lectura de temperatura para que se sienta como un dato experimental real
    (np.random.normal(0, ruido_std)).

    Devuelve un array de forma (n, 2): columna 0 = t, columna 1 = T.

    Si `t_max` no es múltiplo exacto de `paso`, la última medición queda
    en el último instante menor que `t_max`.
    """
    if t_max < 0:
        raise ValueError("t_max debe ser mayor o igual que cero.")
    if paso <= 0:
        raise ValueError("paso debe ser mayor que cero.")
    if ruido_std < 0:
        raise ValueError("ruido_std debe ser mayor o igual que cero.")
    if k < 0:
        raise ValueError("k debe ser mayor o igual que cero.")

    cociente = t_max / paso
    intervalo_cercano = round(cociente)
    if np.isclose(cociente, intervalo_cercano, rtol=0, atol=1e-12):
        cantidad_intervalos = int(intervalo_cercano)
    else:
        cantidad_intervalos = int(np.floor(cociente))
    tiempos = paso * np.arange(cantidad_intervalos + 1, dtype=float)
    if np.isclose(tiempos[-1], t_max):
        tiempos[-1] = t_max

    temperaturas = T_amb + (T0 - T_amb) * np.exp(-k * tiempos)
    if ruido_std > 0:
        temperaturas += np.random.normal(0, ruido_std, size=tiempos.shape)

    return np.column_stack((tiempos, temperaturas))


def tiempo_para_alcanzar(T_objetivo: float, T0: float, T_amb: float, k: float) -> float:
    """
    Despeja t de la ecuación de temperatura para saber cuánto tiempo
    tarda el objeto en llegar a T_objetivo. Útil para el "reto" del juego
    (comparar la predicción del usuario contra el valor real).

        t = -ln((T_objetivo - T_amb) / (T0 - T_amb)) / k

    La temperatura ambiente solo se alcanza de forma asintótica, no en un
    tiempo finito. También se rechazan objetivos fuera del recorrido físico.
    """
    if k <= 0:
        if T_objetivo == T0:
            return 0.0
        raise ValueError("El objetivo no se alcanza con k menor o igual que cero.")

    if T_objetivo == T0:
        return 0.0

    diferencia_inicial = T0 - T_amb
    diferencia_objetivo = T_objetivo - T_amb
    if diferencia_inicial == 0:
        raise ValueError("El objeto ya está a temperatura ambiente y no cambia.")

    fraccion = diferencia_objetivo / diferencia_inicial
    if not 0 < fraccion < 1:
        raise ValueError(
            "El objetivo debe estar entre la temperatura inicial y la ambiente, "
            "sin incluir la temperatura ambiente."
        )

    return float(-np.log(fraccion) / k)
