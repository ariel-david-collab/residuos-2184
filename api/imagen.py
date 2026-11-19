"""Preprocesado canónico de imagen.

Único lugar donde se define cómo entra una foto al modelo. Lo usan tanto la
evaluación offline como la API, para que no existan dos preprocesados distintos.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

LADO = 224


def cargar_bytes(datos: bytes) -> Image.Image:
    """Lee una imagen de disco o de red y corrige su orientación EXIF."""
    with Image.open(io.BytesIO(datos)) as im:
        im = ImageOps.exif_transpose(im)
        return im.convert("RGB")


def preprocesar(imagen: Image.Image) -> np.ndarray:
    """RGB 224x224 bilineal en [-1, 1], con lote de tamaño 1.

    Es exactamente el preprocesado que espera un modelo exportado por
    Teachable Machine (`px / 127.5 - 1`).
    """
    im = imagen.convert("RGB").resize((LADO, LADO), Image.Resampling.BILINEAR)
    arr = np.asarray(im, dtype=np.float32) / 127.5 - 1.0
    return arr[None, ...]
