# Laboratorio virtual: Ley de Enfriamiento de Newton

Aplicación interactiva para explorar la ley de enfriamiento de Newton y
ajustar mediciones experimentales. La interacción, la captura de datos, los
resultados y las gráficas ocurren dentro de la ventana Pygame.

## Instalación y ejecución

```bash
pip install -r requirements.txt
python main.py
```

## Recorrido de la aplicación

- **Modo Juego:** elige una estrategia antes de iniciar el reloj. Ventilación,
  tapas y cubiertas cambian la constante `k` según el escenario. Sigue el
  termómetro hasta cumplir la meta de temperatura; cada meta suma puntos. El
  objeto personalizado admite calentamiento o enfriamiento y un slider para
  controlar el ruido típico del termómetro (`σ`, en °C).
- **k desde el tiempo característico:** en el objeto personalizado puedes
  ingresar `τ` en segundos y el simulador calcula `k = 1/τ` en `1/s`. `τ`
  resume el efecto conjunto de las propiedades del objeto y su entorno; también
  puedes ingresar `k` directamente si ya la conoces.
- **Reto de predicción:** predice cuánto tardará el objeto en alcanzar su meta.
  La precisión añade puntos y puede mejorar la medalla de bronce a plata u oro.
- **Comparación:** analiza varias corridas para superponer sus datos y curvas.
  Así puedes observar cómo cada estrategia cambia el enfriamiento.
- Al terminar una partida se puede analizar el conjunto de mediciones generado
  con ruido gaussiano.
- **Modo Análisis:** escribe la temperatura ambiente y los pares `tiempo,
  temperatura`, uno por línea, o reutiliza los datos de la última simulación.
  Los campos aceptan edición con teclado; `Ctrl+A` selecciona todo el texto.
- **Resultados:** muestra `k`, `T0`, `R²`, residuos y la gráfica principal de
  temperatura contra tiempo integrada en la ventana.
  Usa **Analizar otra corrida** para ajustar otro dataset y superponerlo con
  las corridas ya analizadas.
- **Explicar cálculo:** presenta la ecuación diferencial con los valores del
  instante actual, la rapidez de cambio y una tabla de mediciones. El signo de
  `dT/dt` muestra si el objeto se enfría (negativo) o se calienta (positivo).
- **Quiz rápido:** refuerza cómo interpretar `k`, el equilibrio con el ambiente
  y el calentamiento cuando el objeto empieza más frío que su entorno.
## La idea matemática

La ley modela la rapidez de cambio de la temperatura como proporcional a la
diferencia entre el objeto y su ambiente:

`dT/dt = -k (T - T_amb)`

Si `T > T_amb`, la derivada es negativa y el objeto se enfría. Si `T < T_amb`,
es positiva y se calienta. Cuando ambas temperaturas coinciden, la derivada es
cero: el equilibrio es la asíntota del modelo. La solución para ambiente y `k`
constantes es `T(t) = T_amb + (T0 - T_amb) exp(-k t)`.

`k` se mide en `1/s`; cuanto mayor es `k`, más rápido cambia la temperatura.
La escala característica `τ = 1/k` indica el tiempo para reducir la diferencia
con el ambiente a `1/e` (aproximadamente 37 %) de su valor inicial. La vida
media de esa diferencia es `t½ = ln(2)/k`.

La gráfica de resultados prioriza `T(t)`: muestra las mediciones, la curva
ajustada y la temperatura ambiente. La guía paso a paso desarrolla la
linealización `ln(|T - T_amb|)` y explica por qué su pendiente permite
estimar `k`. La transformación no está definida cuando `T = T_amb`.

El modelo supone un ambiente constante y una temperatura uniforme dentro del
objeto: describe la tendencia educativa, no todos los detalles de una taza real.
En el objeto personalizado, el ruido se agrega a las mediciones simuladas, no
a la temperatura física que mueve la animación.

## Organización

- `escenarios.py` — parámetros de los cuatro escenarios.
- `simulacion.py` — modelo físico, tasa de cambio, datos con ruido y despeje
  del tiempo.
- `analisis.py` — linealización, regresión por mínimos cuadrados, cálculo de
  R² y construcción de la gráfica de temperatura.
- `juego.py` — pantallas, botones, campos de texto, simulación y visualización
  de los resultados.
- `main.py` — punto de entrada.

En el análisis se ajusta la recta
`ln(|T - T_amb|) = ln(|T0 - T_amb|) - k*t`; por eso `k` es el negativo de la
pendiente. El signo de `T0 - T_amb` se identifica del lado del ambiente donde
están las mediciones.
