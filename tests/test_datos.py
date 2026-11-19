"""Curación del dataset: huella perceptual, deduplicación y partición.

El punto crítico del proyecto es que ninguna imagen repetida (o casi repetida)
pueda aparecer a la vez en train y en test: eso inflaría las métricas y el
jurado lo detectaría. Por eso la deduplicación se prueba antes que nada.
"""

import numpy as np
import pytest
from PIL import Image

from datos import (
    Registro,
    dhash,
    deduplicar,
    distancia_hamming,
    partir_estratificado,
)


def imagen(patron: str) -> Image.Image:
    """Imágenes sintéticas con estructura horizontal para diferenciar hashes."""
    x = np.linspace(0, 255, 64, dtype=np.uint8)
    if patron == "degradado":
        filas = np.tile(x, (64, 1))
    elif patron == "invertido":
        filas = np.tile(x[::-1], (64, 1))
    elif patron == "columnas":
        filas = np.tile(np.r_[np.zeros(32), np.full(32, 255)].astype(np.uint8), (64, 1))
    else:
        filas = np.tile(np.full(64, 128, dtype=np.uint8), (64, 1))
    return Image.fromarray(filas, mode="L").convert("RGB")


def registro(nombre: str, clase: str, im: Image.Image) -> Registro:
    return Registro(ruta=nombre, clase=clase, huella=dhash(im))


def test_dhash_da_64_bits_y_es_estable():
    a = dhash(imagen("degradado"))
    b = dhash(imagen("degradado"))
    assert 0 <= a < 2**64
    assert a == b


def test_dhash_distingue_estructuras_distintas():
    a = dhash(imagen("degradado"))
    b = dhash(imagen("invertido"))
    assert distancia_hamming(a, b) > 6


def test_distancia_hamming_cuenta_bits():
    assert distancia_hamming(0b1010, 0b1000) == 1
    assert distancia_hamming(0, 0) == 0
    assert distancia_hamming(2**64 - 1, 0) == 64


def test_deduplicar_elimina_la_misma_imagen_redimensionada():
    original = imagen("degradado")
    copia = original.resize((200, 200))
    registros = [
        registro("a.jpg", "Cartboard", original),
        registro("b.jpg", "Cardboard", copia),
        registro("c.jpg", "Paper", imagen("invertido")),
    ]
    unicos = deduplicar(registros, umbral=6)
    assert len(unicos) == 2
    assert unicos[0].ruta == "a.jpg"


def test_deduplicar_conserva_imagenes_distintas():
    registros = [
        registro("a.jpg", "Paper", imagen("degradado")),
        registro("b.jpg", "Paper", imagen("columnas")),
        registro("c.jpg", "Glass", imagen("invertido")),
    ]
    assert len(deduplicar(registros, umbral=6)) == 3


def test_particion_estratificada_respeta_las_clases_y_las_fracciones():
    registros = [
        registro(f"{clase}-{i}.jpg", clase, imagen("degradado" if i % 2 else "columnas"))
        for clase in ("Paper", "Glass")
        for i in range(20)
    ]
    partes = partir_estratificado(registros, semilla=42, fracciones=(0.7, 0.15, 0.15))

    assert set(partes) == {"train", "val", "test"}
    total = sum(len(v) for v in partes.values())
    assert total == len(registros)
    assert len(partes["train"]) == 28
    assert len(partes["val"]) == 6
    assert len(partes["test"]) == 6

    for clase in ("Paper", "Glass"):
        en_train = sum(r.clase == clase for r in partes["train"])
        en_val = sum(r.clase == clase for r in partes["val"])
        en_test = sum(r.clase == clase for r in partes["test"])
        assert (en_train, en_val, en_test) == (14, 3, 3)


def test_particion_es_reproducible_con_la_misma_semilla():
    registros = [
        registro(f"r{i}.jpg", "Paper" if i % 2 else "Glass", imagen("degradado"))
        for i in range(10)
    ]
    a = partir_estratificado(registros, semilla=42, fracciones=(0.7, 0.15, 0.15))
    b = partir_estratificado(registros, semilla=42, fracciones=(0.7, 0.15, 0.15))
    assert [r.ruta for r in a["test"]] == [r.ruta for r in b["test"]]


def test_particion_no_deja_clases_vacias_en_val_o_test():
    registros = [registro(f"r{i}.jpg", "Textile", imagen("degradado")) for i in range(3)]
    partes = partir_estratificado(registros, semilla=42, fracciones=(0.7, 0.15, 0.15))
    assert len(partes["train"]) >= 1
    assert len(partes["val"]) >= 1
    assert len(partes["test"]) >= 1


def test_particion_rechaza_fracciones_invalidas():
    with pytest.raises(ValueError):
        partir_estratificado([], semilla=42, fracciones=(0.5, 0.5, 0.5))
