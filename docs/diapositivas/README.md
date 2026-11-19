# Diapositivas de sustentación

Presentación en PowerPoint (17 diapositivas, 16:9) para la tarea. Las notas del
orador salen de `guion_por_diapositiva.md`: un bloque de texto por diapositiva,
con la voz que habla en cada una. Los guiones individuales de `docs/guiones/`
quedan como material de apoyo para una entrega por separado.

## Archivos

| Archivo | Qué es |
|---|---|
| `residuos_2184_sustentacion.pptx` | Presentación final, editable en PowerPoint |
| `residuos_2184_sustentacion.pdf` | Copia en PDF para proyectar sin PowerPoint |
| `generar_diapositivas.py` | Genera el `.pptx` desde las figuras y el guion |
| `guion_por_diapositiva.md` | Texto que se dice en cada diapositiva (fuente de las notas) |
| `figuras_deck.py` | Regenera los gráficos con la paleta de La Salle |
| `figs/` | Figuras propias de la presentación (no las del informe) |
| `mapa_diapositivas.md` | Recorrido, voz y recortes por diapositiva |

## Plantilla

- **Azul `#003057`** (Pantone 540C) y **amarillo `#F2A900`** (Pantone 130C), los
  dos colores principales del manual de marca de la Universidad de La Salle.
- Escala de grises para texto secundario; el rojo `#CB333B` se reserva para los
  errores que contaminan el flujo aprovechable.
- Titulares en **Franklin Gothic Heavy**; texto corrido en **Segoe UI**; rutas de
  la API en **Consolas**.
- Sin degradados ni esquinas redondeadas. Las capturas de la app llevan marco
  negro y sombra dura, el mismo lenguaje visual de la interfaz.

## Cómo se regenera

```powershell
# 1. Figuras (lee models/metrics.json, models/umbral.json y la Tabla 1)
.venv\Scripts\python.exe docs\diapositivas\figuras_deck.py

# 2. Presentación (lee guion_por_diapositiva.md)
.venv\Scripts\python.exe docs\diapositivas\generar_diapositivas.py
```

Si se edita el guion por diapositiva, basta con volver a ejecutar el paso 2:
las notas del orador se actualizan solas.

## Cómo presentar

- `F5` inicia la presentación; `Alt + F5` empieza desde la diapositiva actual.
- Vista **Notas del orador** (`Vista → Notas`) muestra el texto del guion debajo
  de cada diapositiva. En pantalla doble, activar **Usar vista del presentador**.
- El recorrido completo usa las 17 diapositivas (~10:50). Si necesitas 9:30,
  salta las diapositivas 8 y 9 y pasa de la 7 a la 10. Los guiones individuales
  usan la portada más su mitad (ver `mapa_diapositivas.md`).
- La demo en vivo necesita HTTPS y conexión; si falla, las capturas de las
  diapositivas 12 y 13 sirven de respaldo.
