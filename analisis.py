"""
analisis.py
------------
Módulo 2: toma datos (t, T) -- generados por el juego o ingresados a mano --
y verifica si obedecen la Ley de Enfriamiento de Newton, estimando k y
qué tan bueno es el ajuste (R²).

Idea clave: linealizar el modelo.
    T(t) = T_amb + (T0 - T_amb) * e^(-k*t)
    T(t) - T_amb = (T0 - T_amb) * e^(-k*t)
    ln(|T(t) - T_amb|) = ln(|T0 - T_amb|) - k*t   <-- y = b + m*t

Con eso, un ajuste lineal simple (mínimos cuadrados) te da la pendiente
(-k) y el intercepto (ln(T0 - T_amb)).
"""

import numpy as np


def _validar_vectores(t: np.ndarray, T: np.ndarray) -> tuple:
    """Convierte las entradas a vectores numéricos y comprueba sus dimensiones."""
    tiempos = np.asarray(t, dtype=float)
    temperaturas = np.asarray(T, dtype=float)
    if tiempos.ndim != 1 or temperaturas.ndim != 1:
        raise ValueError("t y T deben ser arreglos unidimensionales.")
    if tiempos.size != temperaturas.size:
        raise ValueError("t y T deben tener la misma cantidad de datos.")
    return tiempos, temperaturas


def linealizar_datos(t: np.ndarray, T: np.ndarray, T_amb: float) -> np.ndarray:
    """
    Calcula y = ln(T - T_amb) para cada punto.

    Se usa ln(|T - T_amb|), válido tanto para calentamiento como enfriamiento.
    En equilibrio exacto la diferencia es cero y se marca como NaN.
    """
    _, temperaturas = _validar_vectores(t, T)
    resultado = np.full(temperaturas.shape, np.nan, dtype=float)
    diferencia = np.abs(temperaturas - T_amb)
    validos = np.isfinite(temperaturas) & (diferencia > 0)
    resultado[validos] = np.log(diferencia[validos])
    return resultado


def ajustar_modelo(t: np.ndarray, T: np.ndarray, T_amb: float) -> dict:
    """
    Ajusta la recta linealizada con np.polyfit(t, y, 1) y recupera:
        k_estimada   = -pendiente
        T0_estimada  = T_amb + exp(intercepto)

    Devuelve un diccionario, por ejemplo:
        {"k": ..., "T0": ..., "pendiente": ..., "intercepto": ...}

    En la recta y = m*t + b, la pendiente es -k y el intercepto
    es ln(T0 - T_amb).
    """
    tiempos, temperaturas = _validar_vectores(t, T)
    y = linealizar_datos(tiempos, temperaturas, T_amb)
    validos = np.isfinite(tiempos) & np.isfinite(y)
    if np.count_nonzero(validos) < 2:
        raise ValueError("Se necesitan al menos dos datos válidos para ajustar.")
    if np.unique(tiempos[validos]).size < 2:
        raise ValueError("Los tiempos válidos deben contener al menos dos valores distintos.")

    # polyfit encuentra la recta por mínimos cuadrados; el modelo físico da k = -m.
    pendiente, intercepto = np.polyfit(tiempos[validos], y[validos], 1)
    k_estimada = float(-pendiente)
    if k_estimada <= 0:
        raise ValueError(
            "El ajuste no representa enfriamiento: la pendiente no produjo una k positiva."
        )

    signo = 1.0 if np.median(temperaturas[validos] - T_amb) > 0 else -1.0
    return {
        "k": k_estimada,
        "T0": float(T_amb + signo * np.exp(intercepto)),
        "pendiente": float(pendiente),
        "intercepto": float(intercepto),
    }


def calcular_r2(t: np.ndarray, T: np.ndarray, T_amb: float,
                 k: float, T0: float) -> float:
    """
    Calcula R² comparando los datos reales contra el modelo ajustado:
        R² = 1 - (SS_residual / SS_total)
        SS_residual = sum((T_real - T_predicha)^2)
        SS_total    = sum((T_real - promedio(T_real))^2)

    Solo se comparan observaciones finitas distintas de T_amb, el mismo
    dominio usado al linealizar. La linealización admite calentamiento y enfriamiento.
    """
    from simulacion import temperatura

    tiempos, temperaturas = _validar_vectores(t, T)
    validos = (
        np.isfinite(tiempos)
        & np.isfinite(temperaturas)
        & (np.abs(temperaturas - T_amb) > 0)
    )
    if not np.any(validos):
        raise ValueError("No hay datos válidos para calcular R².")

    tiempos_validos = tiempos[validos]
    temperaturas_validas = temperaturas[validos]
    predichas = np.array(
        [temperatura(ti, T0, T_amb, k) for ti in tiempos_validos],
        dtype=float,
    )
    ss_residual = np.sum((temperaturas_validas - predichas) ** 2)
    ss_total = np.sum((temperaturas_validas - np.mean(temperaturas_validas)) ** 2)
    if np.isclose(ss_total, 0.0):
        return 1.0 if np.isclose(ss_residual, 0.0) else 0.0
    return float(1.0 - ss_residual / ss_total)


def graficar_resultado(t: np.ndarray, T: np.ndarray, T_amb: float,
                        resultado_ajuste: dict, r2: float,
                        comparaciones: list | None = None):
    """
    Crea y devuelve una figura Matplotlib (no la muestra por separado), para
    que la interfaz pueda integrarla en su propia ventana. `comparaciones`
    acepta resultados previos con claves t, T, T_amb, resultado y etiqueta.
    """
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

    tiempos, temperaturas = _validar_vectores(t, T)
    validos = (
        np.isfinite(tiempos)
        & np.isfinite(temperaturas)
        & (np.abs(temperaturas - T_amb) > 0)
    )
    if not np.any(validos):
        raise ValueError("No hay datos válidos para graficar.")

    series = [{
        "t": tiempos[validos],
        "T": temperaturas[validos],
        "T_amb": T_amb,
        "resultado": resultado_ajuste,
        "r2": r2,
        "etiqueta": "Análisis actual",
    }]
    series.extend(comparaciones or [])
    t_min = min(float(np.min(np.asarray(item["t"], dtype=float))) for item in series)
    t_max = max(float(np.max(np.asarray(item["t"], dtype=float))) for item in series)
    tiempos_curva = np.linspace(t_min, t_max if t_max > t_min else t_min + 1, 300)

    # Una sola vista prioriza la curva T(t), principal para comprender el modelo.
    fondo_figura = "#172436"
    fondo_ejes = "#203149"
    color_texto = "#E8F0F7"
    color_secundario = "#AFC0D2"
    color_rejilla = "#3A5069"
    color_borde = "#4D657F"
    figura = Figure(figsize=(7.3, 5.0), dpi=100, facecolor=fondo_figura)
    figura.suptitle("Temperatura y modelo de Newton", color=color_texto,
                    fontsize=12, fontweight="bold", y=0.985)
    ejes = figura.add_subplot(111)
    colores = ("#56CFE1", "#FFB25B", "#91E08B", "#C69CFF", "#FF7B89")
    etiquetas_leyenda = []
    for indice, item in enumerate(series):
        datos_t, datos_T = _validar_vectores(item["t"], item["T"])
        mascara = (
            np.isfinite(datos_t)
            & np.isfinite(datos_T)
            & (np.abs(datos_T - item["T_amb"]) > 0)
        )
        if not np.any(mascara):
            continue
        ajuste = item["resultado"]
        color = colores[indice % len(colores)]
        etiqueta = item.get("etiqueta", f"Corrida {indice + 1}")
        etiquetas_leyenda.append(Line2D(
            [0], [0], color=color, marker="o", markersize=4,
            linewidth=1.8, label=etiqueta,
        ))
        ejes.scatter(datos_t[mascara], datos_T[mascara], color=color, s=18,
                     edgecolors=fondo_ejes, linewidths=0.6, alpha=0.95, zorder=3)
        ejes.axhline(item["T_amb"], color=color, linestyle=(0, (4, 3)), linewidth=0.9,
                     alpha=0.65)
        curva = item["T_amb"] + (ajuste["T0"] - item["T_amb"]) * np.exp(
            -ajuste["k"] * tiempos_curva
        )
        ejes.plot(tiempos_curva, curva, color=color, linewidth=1.8, zorder=2)

    ejes.set_ylabel("Temperatura (°C)")
    ejes.set_xlabel("Tiempo (s)")
    ejes.set_title(
        "Puntos: mediciones  ·  curva: ajuste del modelo  ·  trazo discontinuo: T ambiente",
        loc="left", color=color_texto, fontsize=8, pad=7,
    )
    ejes.grid(True, color=color_rejilla, alpha=0.8, linewidth=0.55)
    ejes.set_facecolor(fondo_ejes)
    ejes.tick_params(axis="both", colors=color_secundario, labelsize=8, length=3)
    ejes.xaxis.label.set_color(color_texto)
    ejes.yaxis.label.set_color(color_texto)
    ejes.xaxis.label.set_size(8.5)
    ejes.yaxis.label.set_size(8.5)
    for borde in ejes.spines.values():
        borde.set_color(color_borde)
        borde.set_linewidth(0.7)

    ejes.legend(handles=etiquetas_leyenda, loc="upper right", frameon=True,
                facecolor=fondo_figura, edgecolor=color_borde, framealpha=0.92,
                fontsize=7.5, labelcolor=color_secundario, handlelength=1.8)
    figura.subplots_adjust(left=0.12, right=0.97, top=0.91, bottom=0.12)
    FigureCanvasAgg(figura).draw()
    return figura
