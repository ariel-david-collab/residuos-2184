"""Pruebas del envoltorio de inferencia.

El caso que importa: un ONNX exportado por Teachable Machine ya termina en
softmax, mientras que uno de PyTorch entrega logits. Si el envoltorio aplicara
softmax sobre una salida que ya es una distribución, las probabilidades se
aplanarían y la abstención se volvería inútil. `Modelo` debe detectarlo.
"""

from __future__ import annotations

import numpy as np
import onnx
from onnx import TensorProto, helper

from inferencia import Modelo


def _onnx(destino, valores: list[float], con_softmax: bool) -> None:
    """Grafo mínimo que devuelve un vector constante (con o sin softmax final)."""
    entrada = helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 3, 224, 224])
    salida = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, len(valores)])
    nodos = [
        helper.make_node(
            "Constant", [], ["c"],
            value=helper.make_tensor("c", TensorProto.FLOAT, [1, len(valores)], valores),
        ),
    ]
    if con_softmax:
        nodos.append(helper.make_node("Softmax", ["c"], ["y"], axis=1))
    else:
        nodos.append(helper.make_node("Identity", ["c"], ["y"]))
    grafo = helper.make_graph(nodos, "prueba", [entrada], [salida])
    modelo = helper.make_model(grafo, opset_imports=[helper.make_opsetid("", 13)])
    onnx.save(modelo, str(destino))


def _imagen() -> np.ndarray:
    return np.zeros((1, 224, 224, 3), dtype=np.float32)


def test_no_repite_el_softmax_del_export(tmp_path):
    ruta = tmp_path / "tm.onnx"
    # Un export de Teachable Machine ya devuelve probabilidades: su última capa
    # es softmax. Se alimenta con log-probabilidades para que la salida sea 0.92.
    deseadas = [0.01] * 8 + [0.92]
    _onnx(ruta, [float(np.log(p)) for p in deseadas], con_softmax=True)

    modelo = Modelo(ruta)

    assert modelo.probabilidades is True
    assert abs(modelo.predecir(_imagen())[8] - 0.92) < 1e-4


def test_aplica_softmax_a_los_logits(tmp_path):
    ruta = tmp_path / "pytorch.onnx"
    _onnx(ruta, [0.0] * 8 + [10.0], con_softmax=False)

    modelo = Modelo(ruta)

    assert modelo.probabilidades is False
    assert modelo.predecir(_imagen())[8] > 0.99
