# Residuos 2184 · prototipo

Clasificador de residuos que no responde con el material sino con **la bolsa
correcta** del código de colores colombiano (Resolución 2184 de 2019), y que se
abstiene cuando no está seguro.

- **Frontend:** Rust (Leptos CSR) compilado a WASM con `trunk`.
- **Backend:** Python 3.12, FastAPI y ONNX Runtime CPU.
- **Despliegue:** una sola imagen Docker que sirve la interfaz y la API en el
  mismo origen, publicada en GHCR.

## Estado actual

Fases 1 a 6 del plan cerradas. La aplicación funciona de punta a punta con el
**Modelo B** (`models/modelB_improved.onnx`, MobileNetV3-Small ajustado sobre
RealWaste) y el umbral τ = 0,63 que publica `models/umbral.json`. El Modelo A
(Teachable Machine) queda en `models/modelA_tm.onnx` como referencia de la
comparación.

En producción: **https://residuos.open-laboratories.com** (Traefik + Let's
Encrypt, contenedor `healthy`, sin puertos publicados).

Sobre las 633 imágenes reservadas de `test/`:

| | Material | Bolsa | Macro F1 | AUC |
|---|---|---|---|---|
| Modelo B | 83,6 % | 94,9 % | 0,841 | 0,987 |
| Modelo A | 78,2 % | 91,9 % | 0,777 | 0,971 |

Con τ = 0,63 el Modelo B decide en el 80,9 % de los casos y, entre esos, acierta
el 91,8 % del material y el 98,2 % de la bolsa. La prueba de cambio de dominio
con TrashNet (2.527 imágenes) está en `models/metrics.json` y en las figuras
`figs/eval_*`.

Lo que ya es definitivo:

- proyección de las 9 clases de material a las 3 bolsas normativas;
- umbral de abstención calibrable desde la interfaz;
- exactitud real del modelo publicado en `/api/catalogo` y visible en la página;
- contrato HTTP (`/api/predict`, `/api/predict-lote`, `/api/health`, `/api/catalogo`);
- pruebas de dominio, de preprocesado, de inferencia y de contrato;
- imagen Docker multi-stage y pipeline a GHCR.

## Ejecutar en local

```powershell
# 1. dependencias
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt -r requirements-dev.txt
#    (opcional) para entrenar y convertir el Modelo A:
uv pip install --python .venv\Scripts\python.exe -r requirements-entrenamiento.txt

# 2. frontend (una vez por cambio en web/)
cd web
trunk build --release
cd ..

# 3. API + interfaz
.\.venv\Scripts\python.exe -m uvicorn app:app --app-dir api --port 8000 --reload
```

Abrir <http://127.0.0.1:8000>.

Si `web/dist` no existe, la API responde 503 en `/`: es el único error posible
del arranque y significa que falta compilar el WASM.

## Datos y entrenamiento

Los scripts de `src/` reproducen todo el material del informe, desde las carpetas
crudas hasta el modelo ONNX. Se ejecutan en orden:

> `requirements-entrenamiento.txt` (TensorFlow + `tf2onnx`) sólo hace falta para
> los dos últimos pasos; la API ejecuta el modelo con `onnxruntime` y no lo
> instala en producción.

```powershell
.\.venv\Scripts\python.exe src\s01_datos.py           # inventario, dHash, split y export para TM
.\.venv\Scripts\python.exe src\s02_eda.py             # figuras del análisis exploratorio
.\.venv\Scripts\python.exe src\s02_tm.py              # entrena el Modelo A en Teachable Machine
.\.venv\Scripts\python.exe src\s03_convertir_onnx.py  # Keras a ONNX con verificación de paridad
.\.venv\Scripts\python.exe src\s04_modelo_b.py        # Modelo B: MobileNetV3-Small ajustado
.\.venv\Scripts\python.exe src\s05_calibrar_umbral.py # barrido de τ sobre val/ -> umbral.json
.\.venv\Scripts\python.exe src\s06_evaluar.py         # métricas de A y B, TrashNet y figuras
```

- `datos/manifiesto.csv` es la fuente de verdad de la partición: ninguna imagen
  aparece en dos partes y los duplicados (dHash a distancia ≤ 6) se eliminan
  antes de repartir.
- `datos/train_tm_224/` es el único subconjunto que se sube a Teachable Machine
  (180 imágenes por clase, ya a 224×224).
- `src/s02_tm.py` necesita Edge: el Chromium headless de Playwright no monta la
  aplicación. Corre la interfaz en español y deja las capturas en
  `docs/capturas/03-teachable-machine/`.
- `src/s03_convertir_onnx.py` falla si el ONNX no reproduce al `.h5` con una
  diferencia máxima de `1e-4`, así que un modelo mal convertido no llega a la app.

Las figuras quedan en `figs/` a 300 dpi y las capturas en `docs/capturas/`; el
índice y la procedencia de cada una están en `docs/capturas/README.md`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest api/tests -q
```

- `test_dominio.py` — reglas normativas: proyección a bolsas, abstención, top-3.
- `test_imagen.py` — preprocesado canónico (RGB, 224×224, `px/127.5 − 1`).
- `test_inferencia.py` — el ONNX de Teachable Machine ya trae softmax y el de
  PyTorch no: el envoltorio no debe normalizar dos veces.
- `test_api.py` — contrato HTTP, manejo de lotes y exactitud publicada.

## Contrato

`POST /api/predict` (multipart: `archivo`, `tau`) devuelve:

```json
{
  "material": "Plástico",
  "bolsa": "blanca",
  "bolsa_nombre": "Blanca",
  "bolsa_rotulo": "Aprovechables",
  "confianza": 0.87,
  "abstenido": false,
  "top3": [{ "clase": "Plastic", "material": "Plástico", "p": 0.87 }],
  "bolsas_prob": { "blanca": 0.91, "verde": 0.02, "negra": 0.07 },
  "latencia_ms": 12.4
}
```

`POST /api/predict-lote` recibe `archivos` (varios) y agrega conteos por bolsa,
por material y cuántos quedaron sin decidir.

## Docker y CI

```powershell
docker build -t residuos-2184 .
docker run --rm -p 8080:8000 residuos-2184
```

La imagen final pesa ~471 MB, corre como usuario `app` sin privilegios y trae su
propio `HEALTHCHECK` contra `/api/health`. Solo copia los ONNX y los JSON de
`models/`: los pesos intermedios (`.zip`, `.pt`, historial) quedan fuera.

El workflow `.github/workflows/imagen.yml` corre las pruebas y publica
`ghcr.io/ariel-david-collab/residuos-2184` en cada push a `main`
(`:sha-<commit>` + `:latest`). Un tag `vX.Y.Z` además despliega en el VPS; un
commit a `main` no despliega.

El despliegue sigue el patrón de
[`VPS-Infrastructure`](https://github.com/ariel-david-collab/vps-infrastructure):
Traefik + red `web`, imagen de GHCR pineada en `.release.env`, `.env`
materializado desde **OpenBao** y usuario `deploy-residuos` con
`ForceCommand`. El contenedor **no publica puertos**. Procedimiento completo en
[`docs/despliegue.md`](docs/despliegue.md); los archivos viven en
[`deploy/`](deploy/).

La cámara del navegador exige HTTPS, así que en producción se entra por el
dominio, no por la IP.
