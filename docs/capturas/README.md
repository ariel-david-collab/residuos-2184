# Capturas para el informe

Todas las imágenes de esta carpeta se generan con los scripts del proyecto, no
con capturas manuales de ventanas. Cada PNG tiene a su lado, cuando aplica, el
archivo de texto o el script que lo produjo, de modo que cualquier cifra del
informe se puede volver a comprobar.

> **Estado del modelo.** Las capturas de la app ya usan el **Modelo B**
> (MobileNetV3-Small ajustado), servido desde `models/modelB_improved.onnx` con
> el umbral τ = 0,63 que publica `models/umbral.json`. El modelo de demostración
> por heurística de color ya no interviene.

## Índice

### `01-pipeline-datos/`

| Archivo | Qué muestra |
|---|---|
| `salida-s01-datos.png` | Salida completa de `src/s01_datos.py`: inventario de RealWaste, duplicados eliminados, reparto train/val/test, conteo por bolsa y exportación del subconjunto de Teachable Machine. |
| `salida-s01-datos.txt` | El mismo texto, literal, tal como lo escribió el script. Es la fuente del PNG. |

La captura de consola se dibuja a partir del `.txt`, con fondo oscuro y
tipografía monoespaciada, para que sea legible en el PDF sin depender de una
foto de la terminal. El texto no se retoca.

### `02-app/`

| Archivo | Vista |
|---|---|
| `01-escritorio-inicio.png` | Estado de reposo: cabecera, umbral de abstención explicado, zona de carga, lote y, al pie, la exactitud real del modelo activo sobre `test/`. 1440 × 900. |
| `02-escritorio-veredicto.png` | Veredicto de una foto: bolsa, material, confianza, barras por clase y opción de repetir. |
| `03-escritorio-lote.png` | Lote de nueve fotos con el resumen por bolsa y el detalle por archivo. |
| `04-escritorio-abstencion.png` | Un papel arrugado que el modelo resuelve con 0.33 de confianza, con el umbral en 0.90: la app no decide y avisa «El modelo duda». |
| `05-detalle-umbral.png` | Recorte del control de exigencia y su explicación en lenguaje llano. |
| `06-detalle-veredicto.png` | Recorte del veredicto con las tres clases más probables. |
| `07-movil-inicio.png` | Estado de reposo en 390 × 844 (iPhone 14). |
| `08-movil-veredicto.png` | Veredicto en móvil, con la bolsa y las barras apiladas. |

### `03-teachable-machine/`

Generadas por `src/s02_tm.py` durante el entrenamiento del Modelo A. La
aplicación se abre en Edge porque el Chromium headless de Playwright no monta
Teachable Machine; la interfaz se captura en español (el navegador usa
`locale="es-CO"`).

| Archivo | Etapa |
|---|---|
| `01-proyecto-vacio.png` | Proyecto de imagen recién abierto, con las dos clases por defecto. |
| `02-clases-definidas.png` | Las nueve clases renombradas con los materiales de RealWaste. |
| `03-muestras-completas.png` | Cada clase con sus 180 imágenes cargadas. |
| `04-ultimas-clases.png` | Desplazamiento al final de la lista, con las clases restantes. |
| `04b-avanzado.png` | Panel de hiperparámetros: 50 épocas, lote 16, tasa 0,001. |
| `05-entrenamiento-en-curso.png` | Entrenamiento en ejecución con el contador de épocas. |
| `06-entrenamiento-terminado.png` | Modelo listo, ventana de vista previa en modo **Archivo** con una foto de `test/` y las probabilidades reales del modelo. |
| `07-exportacion.png` | Diálogo de exportación en la pestaña Tensorflow (Keras), con la descarga seleccionada. |
| `salida-s02-tm.png` | Salida completa del script: las nueve cargas, cada captura y el ZIP descargado. |
| `salida-s03-conversion.png` | Conversión del SavedModel a ONNX y verificación de paridad contra Keras. |

El ZIP descargado se guarda en `models/modelA_tm.zip` (`model.savedmodel/` y
`labels.txt`) y queda fuera del repositorio: pesa varios megabytes y se
reproduce con el script. La conversión a ONNX la consume
`src/s03_convertir_onnx.py`, que acepta tanto el SavedModel como un
`keras_model.h5`.

### `04-modelo-b/`

Entrenamiento del Modelo B con `src/s04_modelo_b.py` y calibración del umbral con
`src/s05_calibrar_umbral.py`. Cada log conserva su PNG de consola:

| Archivo | Qué muestra |
|---|---|
| `salida-s04-modelo-b.txt` | Doce épocas sobre 2.951 imágenes de `train/`, con pérdida y exactitud de `train` y `val` por época, la mejor época y la exportación a `models/modelB_improved.onnx`. |
| `salida-s04-modelo-b.png` | El mismo log dibujado como terminal. |
| `salida-s05-umbral.txt` | Barrido de τ sobre las 633 imágenes de `val/`: cobertura, exactitud de material y de bolsa, y el τ elegido (0.63). |
| `salida-s05-umbral.png` | El mismo log dibujado como terminal. |

Los resultados numéricos quedan en `models/modelB_historial.json` (historial de
épocas) y `models/umbral.json` (curva completa de calibración).

### `05-evaluacion/`

Evaluación final con `src/s06_evaluar.py`: métricas sobre `test` con los dos
modelos y prueba de cambio de dominio con TrashNet.

| Archivo | Qué muestra |
|---|---|
| `salida-s06-evaluacion.txt` | Exactitud, macro F1, exactitud de bolsa y AUC de A y B sobre las 633 imágenes de `test/`; el paso por TrashNet (2.527) con y sin abstención; y la lista de figuras escritas. |
| `salida-s06-evaluacion.png` | El mismo log dibujado como terminal. |

Los números completos quedan en `models/metrics.json`: matriz de confusión de 9
materiales y de 3 bolsas, P/R/F1 y AUC por clase, top-2, log-loss y el efecto de
τ en cada modelo.

### Figuras de evaluación

En `figs/`, a 300 dpi, generadas por `src/s06_evaluar.py`:

- `eval_01_matriz_materiales.png`: matriz de confusión de 9 materiales, A y B.
- `eval_02_matriz_bolsas.png`: matriz de confusión de las 3 bolsas normativas.
- `eval_03_f1_clases.png`: F1 por material de los dos modelos.
- `eval_04_roc_a.png` y `eval_04_roc_b.png`: ROC uno-contra-el-resto con AUC por clase.
- `eval_05_cobertura_umbral.png`: cobertura frente a exactitud al mover τ (sobre `val/`).
- `eval_06_trashnet_a.png` y `eval_06_trashnet_b.png`: recall por material en TrashNet frente a `test/`, y el efecto de la abstención.

### `06-despliegue/`

Producción en **https://residuos.open-laboratories.com**: Traefik termina TLS,
la imagen se consume desde GHCR y el contenedor no publica puertos.

| Archivo | Qué muestra |
|---|---|
| `01-sitio-escritorio.png` | La aplicación servida por HTTPS desde el VPS, a 1440×900. |
| `02-sitio-movil.png` | La misma página a 390×844. |
| `03-actions.png` | Historial de GitHub Actions: pruebas, escaneo de secretos, build y publicación en GHCR. |
| `04-ghcr.png` | Paquete público `residuos-2184` con los tags `sha-*` y `latest`. |
| `05-run-deploy.png` | Run de `workflow_dispatch` con los tres jobs en verde: Pruebas → Imagen en GHCR → Despliegue en el VPS. |
| `salida-deploy.txt` | Log literal del wrapper `residuos-deploy`: pull de la imagen, tag pineado en `.release.env`, recreación del contenedor y health check por HTTPS. |
| `salida-deploy.png` | El mismo log dibujado como terminal. |
| `salida-verificacion.txt` | Verificación en el VPS: contenedor `healthy`, sin puertos publicados, health y catálogo por HTTPS, redirección 301, certificado Let's Encrypt y una predicción real. |
| `salida-verificacion.png` | El mismo log dibujado como terminal. |

Las cinco primeras las genera `src/capturas_despliegue.py` (Playwright sobre
las páginas públicas); los logs se dibujan con `src/capturas_consola.py`. En el
historial de Actions quedan también los dos fallos del primer push —imagen y
escaneo de secretos—, conservados como evidencia de la depuración del CI.

## Figuras del análisis exploratorio

No están en esta carpeta sino en `figs/`, generadas por `src/s02_eda.py` a
300 dpi:

- `eda_01_clases.png`: conteo por clase y reparto entre train, val y test.
- `eda_02_bolsas.png`: distribución de las nueve clases en las tres bolsas.
- `eda_03_mosaico.png`: muestras de RealWaste y de TrashNet.

## Cómo regenerarlas

Con la aplicación servida en `http://127.0.0.1:8077`:

```powershell
.\.venv\Scripts\python.exe src\s02_eda.py          # figuras EDA
.\.venv\Scripts\python.exe src\s06_evaluar.py      # métricas y figuras de evaluación
.\.venv\Scripts\python.exe src\capturas_consola.py # logs como terminal
.\.venv\Scripts\python.exe src\capturas_ui.py      # interfaz, escritorio y móvil
.\.venv\Scripts\python.exe src\capturas_despliegue.py  # sitio público, Actions y GHCR
```

`capturas_ui.py` acepta `--base` para apuntar a otro servidor; al terminar el
entrenamiento se vuelve a ejecutar contra la instancia con el modelo real y las
capturas se reemplazan sin tocar el resto del informe.

La interfaz se captura con Playwright y Chromium headless, con
`deviceScaleFactor` 2 en escritorio y 3 en móvil, `locale="es-CO"` y las
animaciones desactivadas. El script recorre el flujo completo: reposo, una
foto, un lote de nueve, umbral en 0.90 para forzar la abstención y recortes de
los dos bloques que interesan.
