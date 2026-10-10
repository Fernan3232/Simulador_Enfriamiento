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
  termómetro hasta cumplir la meta de temperatura; cada meta suma puntos.
- **Reto de predicción:** predice cuánto tardará el objeto en alcanzar su meta.
  La precisión añade puntos y puede mejorar la medalla de bronce a plata u oro.
- **Comparación:** analiza varias corridas para superponer sus datos y curvas.
  Así puedes observar cómo cada estrategia cambia el enfriamiento.
- Al terminar una partida se puede analizar el conjunto de mediciones generado
  con ruido gaussiano.
- **Modo Análisis:** escribe la temperatura ambiente y los pares `tiempo,
  temperatura`, uno por línea, o reutiliza los datos de la última simulación.
  Los campos aceptan edición con teclado; `Ctrl+A` selecciona todo el texto.
- **Resultados:** muestra `k`, `T0`, `R²`, residuos y la gráfica integrada.
  Usa **Analizar otra corrida** para ajustar otro dataset y superponerlo con
  las corridas ya analizadas.

## Organización

- `escenarios.py` — parámetros de los cuatro escenarios.
- `simulacion.py` — modelo físico, tasa de cambio, datos con ruido y despeje
  del tiempo.
- `analisis.py` — linealización, regresión por mínimos cuadrados, cálculo de
  R² y construcción de la figura comparativa.
- `juego.py` — pantallas, botones, campos de texto, simulación y visualización
  de los resultados.
- `main.py` — punto de entrada.

En el análisis se ajusta la recta
`ln(T - T_amb) = ln(T0 - T_amb) - k*t`; por eso `k` es el negativo de la
pendiente y `T0` se recupera a partir del intercepto.
