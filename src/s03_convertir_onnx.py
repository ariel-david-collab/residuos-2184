"""Paso 3: convierte el modelo de Teachable Machine a ONNX y verifica la paridad.

Toma el ZIP que descarga `src/s02_tm.py` —que puede traer `keras_model.h5` o
`model.savedmodel/`—, lo convierte con `tf2onnx` y comprueba sobre imágenes de
`test/` que la salida de ONNX coincide con la del modelo exportado. Si la
diferencia máxima supera la tolerancia, el script falla: un modelo convertido
que no reproduce al original no sirve.

Uso:
    .\\.venv\\Scripts\\python.exe src\\s03_convertir_onnx.py
    .\\.venv\\Scripts\\python.exe src\\s03_convertir_onnx.py --zip models\\prueba_tm.zip
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np

# TensorFlow escribe en stderr avisos de oneDNN que ensucian la salida del paso.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "api"))

from imagen import cargar_bytes, preprocesar  # noqa: E402

MODELOS = RAIZ / "models"
MANIFIESTO = RAIZ / "datos" / "manifiesto.csv"
LADO = 224
TOLERANCIA = 1e-4


def extraer(zip_path: Path, destino: Path) -> tuple[Path, Path]:
    """Devuelve el modelo (`.h5` o carpeta SavedModel) y el `labels.txt`."""
    shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as paquete:
        paquete.extractall(destino)
    etiquetas = next(destino.rglob("labels.txt"))
    h5 = next(destino.rglob("*.h5"), None)
    if h5:
        return h5, etiquetas
    return next(destino.rglob("saved_model.pb")).parent, etiquetas


def orden_de_etiquetas(etiquetas: Path) -> list[str]:
    return [linea.strip().split(" ", 1)[-1] for linea in etiquetas.read_text(encoding="utf-8").splitlines() if linea.strip()]


def convertir(ruta: Path, destino: Path, opset: int):
    """Convierte el modelo a ONNX y devuelve una función que predice con el original."""
    import tensorflow as tf
    import tf2onnx

    if ruta.is_file():
        import tf_keras

        modelo = tf_keras.models.load_model(str(ruta), compile=False)
        print(f"  Keras: entrada {modelo.input_shape} · salida {modelo.output_shape}")
        firma = [tf.TensorSpec([None, LADO, LADO, 3], tf.float32, name="input")]
        tf2onnx.convert.from_keras(modelo, input_signature=firma, opset=opset, output_path=str(destino))
        return lambda x: modelo.predict(x, verbose=0)

    modelo = tf.saved_model.load(str(ruta))
    firma = modelo.signatures["serving_default"]
    entradas = {clave: tuple(espec.shape) for clave, espec in firma.structured_input_signature[1].items()}
    salidas = {clave: tuple(espec.shape) for clave, espec in firma.structured_outputs.items()}
    print(f"  SavedModel: entrada {entradas} · salida {salidas}")
    destino.unlink(missing_ok=True)
    subprocess.run(
        [sys.executable, "-m", "tf2onnx.convert", "--saved-model", str(ruta), "--output", str(destino), "--opset", str(opset)],
        check=True,
    )
    return lambda x: list(firma(tf.constant(x, dtype=tf.float32)).values())[0].numpy()


def imagenes_test(limite: int) -> list[Path]:
    with MANIFIESTO.open(encoding="utf-8", newline="") as archivo:
        filas = [f for f in csv.DictReader(archivo) if f["parte"] == "test"]
    # Una por clase, para que la paridad cubra las nueve.
    vistas: dict[str, list[str]] = {}
    for fila in filas:
        vistas.setdefault(fila["clase"], []).append(fila["ruta"])
    seleccion: list[Path] = []
    for clase in sorted(vistas):
        for ruta in vistas[clase][: max(1, limite // len(vistas))]:
            seleccion.append(RAIZ / ruta)
    return seleccion[:limite]


def verificar(predecir, onnx: Path, rutas: list[Path]) -> float:
    import onnxruntime as ort

    sesion = ort.InferenceSession(str(onnx), providers=["CPUExecutionProvider"])
    entrada = sesion.get_inputs()[0].name
    salida = sesion.get_outputs()[0].name
    diferencias = []
    for ruta in rutas:
        x = preprocesar(cargar_bytes(ruta.read_bytes()))
        esperado = np.asarray(predecir(x)).reshape(-1)
        obtenido = np.asarray(sesion.run([salida], {entrada: x.astype(np.float32)})[0]).reshape(-1)
        diferencias.append(float(np.abs(esperado - obtenido).max()))
    print(f"  paridad sobre {len(rutas)} imágenes: máxima {max(diferencias):.2e}, media {np.mean(diferencias):.2e}")
    return max(diferencias)


def main() -> None:
    parser = argparse.ArgumentParser(description="Modelo A: Keras a ONNX")
    parser.add_argument("--zip", type=Path, default=MODELOS / "modelA_tm.zip")
    parser.add_argument("--onnx", type=Path, default=MODELOS / "modelA_tm.onnx")
    parser.add_argument("--opset", type=int, default=13)
    parser.add_argument("--muestras", type=int, default=18)
    args = parser.parse_args()

    if not args.zip.exists():
        raise SystemExit(f"falta {args.zip.relative_to(RAIZ)}: ejecuta antes src/s02_tm.py")

    print(f"Extrayendo {args.zip.name}")
    modelo_path, etiquetas = extraer(args.zip, MODELOS / "tm_export")
    print(f"  {modelo_path.name} · {etiquetas.name}")

    clases = orden_de_etiquetas(etiquetas)
    print(f"  clases ({len(clases)}): {', '.join(clases)}")

    print("Convirtiendo a ONNX")
    predecir = convertir(modelo_path, args.onnx, args.opset)
    print(f"  {args.onnx.relative_to(RAIZ)} ({args.onnx.stat().st_size // 1024} KB)")

    print("Verificando paridad")
    diferencia = verificar(predecir, args.onnx, imagenes_test(args.muestras))
    if diferencia > TOLERANCIA:
        raise SystemExit(f"la conversión no reproduce a Keras: diferencia {diferencia:.2e} > {TOLERANCIA:.0e}")
    shutil.rmtree(MODELOS / "tm_export", ignore_errors=True)
    print("Listo: el ONNX reproduce al modelo exportado.")


if __name__ == "__main__":
    main()
