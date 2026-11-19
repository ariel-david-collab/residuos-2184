"""Paso 4: Modelo B — MobileNetV3-Small ajustado sobre el corpus completo.

El Modelo A (Teachable Machine) ve 180 imágenes por clase. Este segundo modelo
ve todo `train/` del manifiesto, compensa el desbalance de RealWaste con pesos
en la pérdida y usa aumento de datos moderado. Entrena sobre `val/` con parada
temprana, se queda con la mejor época y exporta `models/modelB_improved.onnx`
para que la API lo prefiera sobre el Modelo A.

La normalización replica la de la aplicación (`px/127.5 - 1`, es decir media y
desvío 0.5): así el mismo tensor que arma `api/imagen.py` sirve para el Modelo A
y para el Modelo B, sin ramas por modelo en la API.

    .\\.venv\\\\Scripts\\\\python.exe src\\\\s04_modelo_b.py
    .\\.venv\\\\Scripts\\\\python.exe src\\\\s04_modelo_b.py --epocas 20

El historial de entrenamiento queda en `models/modelB_historial.json`.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

RAIZ = Path(__file__).resolve().parents[1]
MANIFIESTO = RAIZ / "datos" / "manifiesto.csv"
MODELOS = RAIZ / "models"
LADO = 224
SALIDA = MODELOS / "modelB_improved.onnx"
HISTORIAL = MODELOS / "modelB_historial.json"

MEDIA = (0.5, 0.5, 0.5)
DESVIO = (0.5, 0.5, 0.5)

AUMENTO = transforms.Compose(
    [
        transforms.RandomResizedCrop(LADO, scale=(0.65, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(MEDIA, DESVIO),
    ]
)

EVALUACION = transforms.Compose(
    [
        transforms.Resize((LADO, LADO)),
        transforms.ToTensor(),
        transforms.Normalize(MEDIA, DESVIO),
    ]
)


class Corpus(Dataset):
    """Imágenes del manifiesto para una parte (`train`, `val` o `test`)."""

    def __init__(self, filas: list[dict], clases: list[str], transformacion):
        self.filas = filas
        self.clases = clases
        self.transformacion = transformacion
        self.indices = {clase: i for i, clase in enumerate(clases)}

    def __len__(self) -> int:
        return len(self.filas)

    def __getitem__(self, posicion: int):
        fila = self.filas[posicion]
        with Image.open(RAIZ / fila["ruta"]) as imagen:
            tensor = self.transformacion(imagen.convert("RGB"))
        return tensor, self.indices[fila["clase"]]


def leer_manifiesto() -> dict[str, list[dict]]:
    partes: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    with MANIFIESTO.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            partes[fila["parte"]].append(fila)
    return partes


def pesos_de_clase(filas: list[dict], clases: list[str]) -> torch.Tensor:
    """Compensa el desbalance: cada clase pesa lo inverso a su frecuencia."""
    conteo = np.array([sum(1 for f in filas if f["clase"] == c) for c in clases], dtype=np.float64)
    return torch.tensor(len(filas) / (len(clases) * conteo), dtype=torch.float32)


def exactitud(modelo: nn.Module, cargador: DataLoader, criterio: nn.Module) -> tuple[float, float]:
    modelo.eval()
    perdida, aciertos, total = 0.0, 0, 0
    with torch.no_grad():
        for imagenes, etiquetas in cargador:
            salida = modelo(imagenes)
            perdida += criterio(salida, etiquetas).item() * len(etiquetas)
            aciertos += int((salida.argmax(1) == etiquetas).sum())
            total += len(etiquetas)
    return perdida / total, aciertos / total


def construir_modelo(clases: int) -> nn.Module:
    modelo = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    for parametro in modelo.parameters():
        parametro.requires_grad = False
    for capa in modelo.features[-2:]:
        for parametro in capa.parameters():
            parametro.requires_grad = True
    modelo.classifier[-1] = nn.Linear(modelo.classifier[-1].in_features, clases)
    return modelo


def entrenar(epocas: int, lote: int, tasa: float, paciencia: int, semilla: int, limite: int = 0) -> dict:
    torch.manual_seed(semilla)
    np.random.seed(semilla)

    partes = leer_manifiesto()
    if limite:
        for nombre, filas in partes.items():
            elegidas: list[dict] = []
            cuenta: dict[str, int] = {}
            for fila in filas:
                clase = fila["clase"]
                if cuenta.get(clase, 0) < limite:
                    elegidas.append(fila)
                    cuenta[clase] = cuenta.get(clase, 0) + 1
            partes[nombre] = elegidas
    clases = sorted({f["clase"] for f in partes["train"]})
    print(f"Corpus: {len(partes['train'])} train · {len(partes['val'])} val · {len(partes['test'])} test")
    print(f"Clases ({len(clases)}): {', '.join(clases)}")

    modelo = construir_modelo(len(clases))
    criterio = nn.CrossEntropyLoss(weight=pesos_de_clase(partes["train"], clases))
    optimizador = torch.optim.AdamW(
        [p for p in modelo.parameters() if p.requires_grad], lr=tasa, weight_decay=1e-4
    )
    planificador = torch.optim.lr_scheduler.CosineAnnealingLR(optimizador, T_max=epocas)

    cargadores = {
        "train": DataLoader(
            Corpus(partes["train"], clases, AUMENTO), batch_size=lote, shuffle=True, num_workers=0
        ),
        "val": DataLoader(Corpus(partes["val"], clases, EVALUACION), batch_size=lote, num_workers=0),
    }

    historial = {"clases": clases, "epocas": []}
    mejor = {"perdida": float("inf"), "epoca": 0, "exactitud": 0.0}
    sin_mejora = 0

    for epoca in range(1, epocas + 1):
        modelo.train()
        inicio = time.time()
        perdida, aciertos, total = 0.0, 0, 0
        for imagenes, etiquetas in cargadores["train"]:
            optimizador.zero_grad()
            salida = modelo(imagenes)
            costo = criterio(salida, etiquetas)
            costo.backward()
            optimizador.step()
            perdida += costo.item() * len(etiquetas)
            aciertos += int((salida.argmax(1) == etiquetas).sum())
            total += len(etiquetas)
        planificador.step()

        train_perdida, train_exactitud = perdida / total, aciertos / total
        val_perdida, val_exactitud = exactitud(modelo, cargadores["val"], criterio)
        historial["epocas"].append(
            {
                "epoca": epoca,
                "train_perdida": round(train_perdida, 4),
                "train_exactitud": round(train_exactitud, 4),
                "val_perdida": round(val_perdida, 4),
                "val_exactitud": round(val_exactitud, 4),
            }
        )
        print(
            f"  época {epoca:2d}/{epocas} · train {train_perdida:.3f}/{train_exactitud:.1%}"
            f" · val {val_perdida:.3f}/{val_exactitud:.1%} · {int(time.time() - inicio)} s"
        )

        if val_perdida < mejor["perdida"] - 1e-4:
            mejor = {"perdida": val_perdida, "epoca": epoca, "exactitud": val_exactitud}
            torch.save(modelo.state_dict(), MODELOS / "modelB_mejor.pt")
            sin_mejora = 0
        else:
            sin_mejora += 1
            if sin_mejora >= paciencia:
                print(f"  parada temprana: sin mejora en {paciencia} épocas")
                break

    modelo.load_state_dict(torch.load(MODELOS / "modelB_mejor.pt", weights_only=True))
    historial["mejor"] = mejor
    HISTORIAL.parent.mkdir(parents=True, exist_ok=True)
    HISTORIAL.write_text(json.dumps(historial, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  mejor época {mejor['epoca']} · val {mejor['perdida']:.3f}/{mejor['exactitud']:.1%}")
    return {"modelo": modelo, "clases": clases, "historial": historial}


def exportar(modelo: nn.Module, destino: Path) -> Path:
    modelo.eval()
    ejemplo = torch.randn(1, 3, LADO, LADO)
    destino.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        modelo,
        ejemplo,
        str(destino),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "lote"}, "logits": {0: "lote"}},
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    ruta = destino.resolve()
    nombre = ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else destino
    print(f"  ONNX: {nombre} ({ruta.stat().st_size // 1024} KB)")
    return ruta


def main() -> None:
    parser = argparse.ArgumentParser(description="Ajusta MobileNetV3-Small y exporta ONNX.")
    parser.add_argument("--epocas", type=int, default=12, help="máximo de épocas")
    parser.add_argument("--lote", type=int, default=32)
    parser.add_argument("--tasa", type=float, default=3e-4)
    parser.add_argument("--paciencia", type=int, default=3, help="épocas sin mejora antes de parar")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--limite", type=int, default=0, help="recorta cada parte (prueba rápida)")
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args()

    resultado = entrenar(args.epocas, args.lote, args.tasa, args.paciencia, args.semilla, args.limite)
    exportar(resultado["modelo"], args.salida)

    guardado = MODELOS / "modelB_clases.json"
    guardado.write_text(json.dumps(resultado["clases"], indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  clases: {guardado.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
