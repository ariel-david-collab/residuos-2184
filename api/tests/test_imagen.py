"""Preprocesado canónico compartido por evaluación y API.

Debe ser idéntico al de Teachable Machine: RGB, 224x224 bilineal, px/127.5 - 1.
"""

import numpy as np
import pytest
from PIL import Image

from imagen import preprocesar


def test_devuelve_lote_de_uno_con_forma_nhwc():
    tensor = preprocesar(Image.new("RGB", (640, 480), (0, 0, 0)))
    assert tensor.shape == (1, 224, 224, 3)
    assert tensor.dtype == np.float32


def test_blanco_puro_queda_en_uno():
    tensor = preprocesar(Image.new("RGB", (300, 300), (255, 255, 255)))
    assert tensor.min() == pytest.approx(1.0)
    assert tensor.max() == pytest.approx(1.0)


def test_negro_puro_queda_en_menos_uno():
    tensor = preprocesar(Image.new("RGB", (300, 300), (0, 0, 0)))
    assert tensor.min() == pytest.approx(-1.0)
    assert tensor.max() == pytest.approx(-1.0)


def test_conserva_el_orden_rgb():
    tensor = preprocesar(Image.new("RGB", (64, 64), (255, 0, 0)))
    assert tensor[0, :, :, 0].mean() == pytest.approx(1.0)
    assert tensor[0, :, :, 1].mean() == pytest.approx(-1.0)
    assert tensor[0, :, :, 2].mean() == pytest.approx(-1.0)


def test_acepta_imagen_en_escala_de_grises():
    tensor = preprocesar(Image.new("L", (100, 100), 128))
    assert tensor.shape == (1, 224, 224, 3)
