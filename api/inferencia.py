"""Inferencia: un ONNX si existe, o un modelo de demostración si aún no hay pesos.

La interfaz es la misma en ambos casos, así que cuando aparezca el modelo
entrenado basta con dejarlo en `models/` y reiniciar: la aplicación no cambia.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
MODELOS = RAIZ / "models"

# Orden de preferencia: el modelo mejorado manda si está disponible.
PREFERIDOS = ("modelB_improved.onnx", "modelA_tm.onnx")


class Modelo:
    """Envoltorio que normaliza la entrada según lo que espere el ONNX."""

    def __init__(self, ruta: Path):
        import onnxruntime as ort

        self.ruta = ruta
        self.nombre = ruta.stem
        self.sesion = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
        entrada = self.sesion.get_inputs()[0]
        self.entrada = entrada.name
        forma = list(entrada.shape)
        # NHWC (Teachable Machine) o NCHW (PyTorch), indistintamente.
        self.nhwc = len(forma) == 4 and forma[-1] == 3
        self.salida = self.sesion.get_outputs()[0].name
        # Un export de Teachable Machine ya trae la capa softmax; un modelo de
        # PyTorch entrega logits. Se detecta una sola vez, al cargar.
        self.probabilidades = self._ya_normaliza()

    def _crudo(self, lote: np.ndarray) -> np.ndarray:
        salida = self.sesion.run([self.salida], {self.entrada: lote.astype(np.float32)})[0]
        return np.asarray(salida, dtype=np.float64).reshape(-1)

    def _ya_normaliza(self) -> bool:
        """¿La salida cruda ya es una distribución de probabilidad?"""
        forma = (1, 224, 224, 3) if self.nhwc else (1, 3, 224, 224)
        y = self._crudo(np.zeros(forma, dtype=np.float32))
        return bool(np.all(y >= 0.0) and 0.99 <= y.sum() <= 1.01)

    def predecir(self, lote: np.ndarray) -> np.ndarray:
        x = lote if self.nhwc else np.transpose(lote, (0, 3, 1, 2))
        y = self._crudo(x)
        return y if self.probabilidades else _softmax(y)


class ModeloDemo:
    """Demostración sin pesos: heurística de color, marcada como tal en la UI."""

    nombre = "demostración"

    def predecir(self, lote: np.ndarray) -> np.ndarray:
        rgb = (lote[0].astype(np.float64) + 1.0) / 2.0
        r, g, b = (rgb[..., i].mean() for i in range(3))
        brillo = float(rgb.mean())
        saturacion = float((rgb.max(axis=-1) - rgb.min(axis=-1)).mean())

        # Puntajes por material en el orden canónico (Cardboard..Vegetation).
        puntajes = np.array(
            [
                1.9 * brillo - 1.2 * saturacion,          # Cartón
                1.6 * min(r, g) + 0.8 * brillo - 0.4,     # Orgánicos
                1.5 * b - 0.9 * saturacion + 0.3,         # Vidrio
                1.3 * brillo - 1.1 * saturacion - 0.2,    # Metal
                -2.2 * brillo + 0.5,                      # No aprovechable
                1.8 * brillo - 1.5 * saturacion + 0.4,    # Papel
                2.2 * saturacion - 0.6 * brillo,          # Plástico
                1.2 * saturacion - 0.8 * abs(brillo - 0.5),  # Textil
                max(0.0, g - max(r, b)) * 4.0,            # Vegetación
            ]
        )
        return _softmax(puntajes * 6.0)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def cargar() -> Modelo | ModeloDemo:
    for nombre in PREFERIDOS:
        ruta = MODELOS / nombre
        if ruta.exists():
            return Modelo(ruta)
    otros = sorted(MODELOS.glob("*.onnx"))
    if otros:
        return Modelo(otros[0])
    return ModeloDemo()
