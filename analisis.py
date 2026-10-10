"""
analisis.py
------------
Módulo 2: toma datos (t, T) -- generados por el juego o ingresados a mano --
y verifica si obedecen la Ley de Enfriamiento de Newton, estimando k y
qué tan bueno es el ajuste (R²).

Idea clave: linealizar el modelo.
    T(t) = T_amb + (T0 - T_amb) * e^(-k*t)
    T(t) - T_amb = (T0 - T_amb) * e^(-k*t)
    ln(T(t) - T_amb) = ln(T0 - T_amb) - k*t   <-- esto ya es una recta: y = b + m*t

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

    Los puntos no finitos o con T <= T_amb se marcan como NaN: no pertenecen
    al dominio del logaritmo y el ajuste los excluirá.
    """
    _, temperaturas = _validar_vectores(t, T)
    resultado = np.full(temperaturas.shape, np.nan, dtype=float)
    validos = np.isfinite(temperaturas) & (temperaturas > T_amb)
    resultado[validos] = np.log(temperaturas[validos] - T_amb)
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

    return {
        "k": k_estimada,
        "T0": float(T_amb + np.exp(intercepto)),
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

    Solo se comparan observaciones finitas por encima de T_amb, el mismo
    dominio usado al linealizar.
    """
    from simulacion import temperatura

    tiempos, temperaturas = _validar_vectores(t, T)
    validos = (
        np.isfinite(tiempos)
        & np.isfinite(temperaturas)
        & (temperaturas > T_amb)
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

    tiempos, temperaturas = _validar_vectores(t, T)
    validos = (
        np.isfinite(tiempos)
        & np.isfinite(temperaturas)
        & (temperaturas > T_amb)
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

    figura = Figure(figsize=(7.2, 4.4), dpi=100, facecolor="#f4f7fb")
    ejes = figura.add_subplot(111)
    colores = ("#db5b4c", "#2878b5", "#4b9b69", "#9a68b5", "#d08b32")
    resumen = []
    for indice, item in enumerate(series):
        datos_t, datos_T = _validar_vectores(item["t"], item["T"])
        mascara = (
            np.isfinite(datos_t)
            & np.isfinite(datos_T)
            & (datos_T > item["T_amb"])
        )
        if not np.any(mascara):
            continue
        ajuste = item["resultado"]
        color = colores[indice % len(colores)]
        etiqueta = item.get("etiqueta", f"Corrida {indice + 1}")
        ejes.scatter(datos_t[mascara], datos_T[mascara], color=color, s=25,
                     alpha=0.8, label=f"{etiqueta}: datos")
        curva = item["T_amb"] + (ajuste["T0"] - item["T_amb"]) * np.exp(
            -ajuste["k"] * tiempos_curva
        )
        ejes.plot(tiempos_curva, curva, color=color, linewidth=2,
                  label=f"{etiqueta}: k={ajuste['k']:.4f}")
        resumen.append(
            f"{etiqueta}: k={ajuste['k']:.5f} 1/s, "
            f"T0={ajuste['T0']:.2f} °C, R²={item.get('r2', r2):.4f}"
        )

    # El cuadro resume cada ajuste para comparar parámetros sin salir de la gráfica.
    ejes.text(
        0.02, 0.98, "\n".join(resumen),
        transform=ejes.transAxes, va="top", fontsize=8,
        bbox={"facecolor": "white", "alpha": 0.88, "edgecolor": "#9aa8b7"},
    )
    ejes.set_xlabel("Tiempo (s)")
    ejes.set_ylabel("Temperatura (°C)")
    ejes.set_title("Ley de Enfriamiento de Newton")
    ejes.grid(True, alpha=0.25)
    ejes.legend(loc="best", fontsize=8)
    figura.tight_layout()
    FigureCanvasAgg(figura).draw()
    return figura
