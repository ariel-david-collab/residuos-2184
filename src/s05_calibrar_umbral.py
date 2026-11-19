"""Paso 5: calibra el umbral de abstención sobre `val/`.

Barre τ de 0.30 a 0.95 y mide, para cada valor, cuánto se acepta (cobertura) y
cuánto se acierta entre lo aceptado: a nivel de material y a nivel de bolsa
normativa (Resolución 2184 de 2019). El umbral recomendado es el menor que
alcanza la exactitud objetivo con la mayor cobertura posible.

Por defecto el criterio es la exactitud de **material**, no la de bolsa: cinco de
las nueve clases caen en la bolsa blanca, así que acertar la bolsa es fácil y
esconde un material equivocado. El barrido guarda las dos métricas para poder
trazar la curva de cobertura frente a exactitud en el informe.

Escribe `models/umbral.json`, que la API lee para proponer τ en la interfaz.

    .\\.venv\\\\Scripts\\\\python.exe src\\\\s05_calibrar_umbral.py
    .\\.venv\\\\Scripts\\\\python.exe src\\\\s05_calibrar_umbral.py --onnx models\\\\modelA_tm.onnx
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "api"))

from dominio import BOLSAS, MATERIALES, proyectar_bolsas  # noqa: E402
from imagen import cargar_bytes, preprocesar  # noqa: E402
from inferencia import Modelo  # noqa: E402

MANIFIESTO = RAIZ / "datos" / "manifiesto.csv"
MODELOS = RAIZ / "models"
SALIDA = MODELOS / "umbral.json"
UMBRALES = tuple(round(0.30 + 0.01 * i, 2) for i in range(66))  # 0.30 .. 0.95
NOMBRES_BOLSA = list(BOLSAS)
CLASES = [m["clase"] for m in MATERIALES]


def imagenes_val(limite: int = 0) -> list[dict]:
    """Filas de `val/`, opcionalmente recortadas a `limite` por clase."""
    filas = []
    with MANIFIESTO.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["parte"] == "val":
                filas.append(fila)
    if not limite:
        return filas

    por_clase: dict[str, int] = {}
    elegidas = []
    for fila in filas:
        clase = fila["clase"]
        if por_clase.get(clase, 0) < limite:
            elegidas.append(fila)
            por_clase[clase] = por_clase.get(clase, 0) + 1
    return elegidas


def probabilidades(modelo: Modelo, filas: list[dict]) -> np.ndarray:
    salida = []
    for i, fila in enumerate(filas, start=1):
        imagen = cargar_bytes((RAIZ / fila["ruta"]).read_bytes())
        salida.append(modelo.predecir(preprocesar(imagen)))
        if i % 100 == 0:
            print(f"  {i}/{len(filas)} imágenes")
    return np.asarray(salida)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibra el umbral de abstención.")
    parser.add_argument("--onnx", type=Path, default=MODELOS / "modelB_improved.onnx")
    parser.add_argument("--objetivo", type=float, default=0.90, help="exactitud a alcanzar entre lo aceptado")
    parser.add_argument(
        "--nivel",
        choices=("material", "bolsa"),
        default="material",
        help="nivel que manda al elegir τ (la bolsa se satisface por azar con 5 de 9 clases)",
    )
    parser.add_argument("--limite", type=int, default=0, help="imágenes por clase (prueba rápida)")
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args()

    modelo = Modelo(args.onnx)
    filas = imagenes_val(args.limite)
    print(f"Modelo: {modelo.nombre} · {args.onnx.name}")
    print(f"Validación: {len(filas)} imágenes")

    probs = probabilidades(modelo, filas)
    real_material = np.array([CLASES.index(f["clase"]) for f in filas])
    real_bolsa = np.array([NOMBRES_BOLSA.index(f["bolsa"]) for f in filas])

    confianza = probs.max(axis=1)
    pred_material = probs.argmax(axis=1)
    probs_bolsa = np.array([[proyectar_bolsas(p)[n] for n in NOMBRES_BOLSA] for p in probs])
    pred_bolsa = probs_bolsa.argmax(axis=1)

    curva = []
    for tau in UMBRALES:
        aceptadas = confianza >= tau
        if not aceptadas.any():
            curva.append({"tau": tau, "cobertura": 0.0, "exactitud_material": None, "exactitud_bolsa": None})
            continue
        curva.append(
            {
                "tau": tau,
                "cobertura": round(float(aceptadas.mean()), 4),
                "exactitud_material": round(
                    float((pred_material[aceptadas] == real_material[aceptadas]).mean()), 4
                ),
                "exactitud_bolsa": round(float((pred_bolsa[aceptadas] == real_bolsa[aceptadas]).mean()), 4),
            }
        )

    validos = [p for p in curva if p[f"exactitud_{args.nivel}"] is not None]
    cumplen = [p for p in validos if p[f"exactitud_{args.nivel}"] >= args.objetivo]
    if cumplen:
        elegido = max(cumplen, key=lambda p: p["cobertura"])
    elif validos:
        elegido = max(validos, key=lambda p: p[f"exactitud_{args.nivel}"] * p["cobertura"])
        print(f"  aviso: ningún umbral alcanza {args.objetivo:.0%} de exactitud de {args.nivel}")
    else:
        elegido = curva[0]
        print("  aviso: el modelo no supera ni el umbral mínimo; revisa el entrenamiento")

    print(f"Umbral recomendado: τ = {elegido['tau']:.2f}")
    if elegido["exactitud_bolsa"] is None:
        print("  sin imágenes aceptadas: no hay cobertura que medir")
    else:
        otro = "bolsa" if args.nivel == "material" else "material"
        print(
            f"  cobertura {elegido['cobertura']:.1%} · {args.nivel} {elegido[f'exactitud_{args.nivel}']:.1%}"
            f" · {otro} {elegido[f'exactitud_{otro}']:.1%}"
        )

    salida = {
        "modelo": modelo.nombre,
        "nivel": args.nivel,
        "objetivo": args.objetivo,
        "tau": elegido["tau"],
        "cobertura": elegido["cobertura"],
        "exactitud_bolsa": elegido["exactitud_bolsa"],
        "exactitud_material": elegido["exactitud_material"],
        "imagenes_val": len(filas),
        "curva": curva,
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    ruta = args.salida.resolve()
    print(f"  guardado: {ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else args.salida}")
    print(f"Clases: {', '.join(CLASES)}")


if __name__ == "__main__":
    main()
