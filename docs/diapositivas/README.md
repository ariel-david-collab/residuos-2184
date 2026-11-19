# Diapositivas de sustentación

Presentación en PowerPoint (17 diapositivas, 16:9) que acompaña los tres guiones
de `docs/guiones/`. Las notas del orador de cada diapositiva se extraen
**literalmente** de los guiones, así que la presentación y el discurso no se
pueden desincronizar.

## Archivos

| Archivo | Qué es |
|---|---|
| `residuos_2184_sustentacion.pptx` | Presentación final, editable en PowerPoint |
| `residuos_2184_sustentacion.pdf` | Copia en PDF para proyectar sin PowerPoint |
| `generar_diapositivas.py` | Genera el `.pptx` desde las figuras y los guiones |
| `figuras_deck.py` | Regenera los gráficos con la paleta de La Salle |
| `figs/` | Figuras propias de la presentación (no las del informe) |
| `mapa_diapositivas.md` | Qué diapositiva va con cada bloque de cada guion |

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

# 2. Presentación (lee los guiones de docs/guiones/)
.venv\Scripts\python.exe docs\diapositivas\generar_diapositivas.py
```

Si se edita un guion, basta con volver a ejecutar el paso 2: las notas del
orador se actualizan solas.

## Cómo presentar

- `F5` inicia la presentación; `Alt + F5` empieza desde la diapositiva actual.
- Vista **Notas del orador** (`Vista → Notas`) muestra el texto del guion debajo
  de cada diapositiva. En pantalla doble, activar **Usar vista del presentador**.
- El guion integrado de 9:30 usa las 17 diapositivas. Los guiones individuales
  usan la portada más su mitad (ver `mapa_diapositivas.md`).
- La demo en vivo necesita HTTPS y conexión; si falla, las capturas de las
  diapositivas 12 y 13 sirven de respaldo.
