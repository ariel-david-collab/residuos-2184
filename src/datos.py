"""Curación del dataset: huella perceptual, deduplicación y partición.

La huella dHash compara cada píxel con el de su derecha en una versión de
9x8 en gris y guarda un bit por comparación: 64 bits en total. Dos fotos de
la misma escena, aunque cambien de tamaño o de compresión, quedan a pocos
bits de distancia; dos residuos distintos quedan lejos.

Mantener duplicados fuera del conjunto es lo que impide que `test` se
contamine con imágenes que el modelo ya vio en `train`.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from PIL import Image, ImageOps

LADO_HASH = 8
PARTES = ("train", "val", "test")


@dataclass(frozen=True)
class Registro:
    """Una imagen del corpus, con su clase y su huella de 64 bits."""

    ruta: str
    clase: str
    huella: int
    bolsa: str = ""


def dhash(imagen: Image.Image, lado: int = LADO_HASH) -> int:
    """Huella perceptual de 64 bits (comparación horizontal de vecinos)."""
    gris = ImageOps.exif_transpose(imagen).convert("L")
    gris = gris.resize((lado + 1, lado), Image.Resampling.BILINEAR)
    px = np.asarray(gris, dtype=np.int16)
    bits = (px[:, :-1] < px[:, 1:]).reshape(-1)

    valor = 0
    for bit in bits:
        valor = (valor << 1) | int(bit)
    return valor


def distancia_hamming(a: int, b: int) -> int:
    """Número de bits distintos entre dos huellas."""
    return (a ^ b).bit_count()


def deduplicar(registros: Sequence[Registro], umbral: int = 6) -> list[Registro]:
    """Conserva el primer registro de cada grupo de imágenes casi iguales."""
    unicos: list[Registro] = []
    for r in registros:
        if all(distancia_hamming(r.huella, u.huella) > umbral for u in unicos):
            unicos.append(r)
    return unicos


def partir_estratificado(
    registros: Sequence[Registro],
    semilla: int = 42,
    fracciones: tuple[float, float, float] = (0.7, 0.15, 0.15),
) -> dict[str, list[Registro]]:
    """Reparte por clase respetando las fracciones y sin dejar clases vacías."""
    if len(fracciones) != 3 or abs(sum(fracciones) - 1.0) > 1e-9:
        raise ValueError("las fracciones deben ser tres y sumar 1")

    por_clase: dict[str, list[Registro]] = defaultdict(list)
    for r in registros:
        por_clase[r.clase].append(r)

    rng = random.Random(semilla)
    partes: dict[str, list[Registro]] = {p: [] for p in PARTES}

    for clase in sorted(por_clase):
        items = sorted(por_clase[clase], key=lambda r: r.ruta)
        rng.shuffle(items)
        n = len(items)
        n_test, n_val = _cuotas(n, fracciones)
        partes["test"].extend(items[:n_test])
        partes["val"].extend(items[n_test : n_test + n_val])
        partes["train"].extend(items[n_test + n_val :])

    return partes


def _cuotas(n: int, fracciones: tuple[float, float, float]) -> tuple[int, int]:
    """Cuántas imágenes van a test y a val cuando la clase tiene `n`."""
    if n <= 1:
        return 0, 0
    if n == 2:
        return 0, 1

    n_test = max(1, round(n * fracciones[2]))
    n_val = max(1, round(n * fracciones[1]))
    if n_val + n_test >= n:
        n_test, n_val = 1, 1
    return n_test, n_val
