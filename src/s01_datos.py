"""Paso 1: inventario, deduplicación y partición de RealWaste.

Lee las 9 carpetas de RealWaste, calcula la huella dHash de cada imagen,
elimina duplicados (distancia de Hamming <= umbral) y reparte el corpus en
train/val/test de forma estratificada y reproducible.

Escribe `datos/manifiesto.csv` (fuente de verdad para el entrenamiento y la
evaluación) y `datos/resumen_datos.json` (cifras para el informe).

Uso:
    .\\.venv\\Scripts\\python.exe src\\s01_datos.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "api"))

from dominio import MATERIALES  # noqa: E402

from datos import Registro, dhash, deduplicar, partir_estratificado  # noqa: E402

EXTENSIONES = {".jpg", ".jpeg", ".png"}
POR_CLASE = {m["clase"]: m for m in MATERIALES}


def inventariar(raiz: Path) -> tuple[list[Registro], list[str], list[str]]:
    """Devuelve registros válidos, rutas corruptas y carpetas desconocidas."""
    registros: list[Registro] = []
    corruptas: list[str] = []
    desconocidas: set[str] = set()

    for carpeta in sorted(p for p in raiz.rglob("*") if p.is_dir()):
        archivos = [f for f in carpeta.iterdir() if f.suffix.lower() in EXTENSIONES]
        if not archivos:
            continue
        if carpeta.name not in POR_CLASE:
            desconocidas.add(carpeta.name)
            continue

        material = POR_CLASE[carpeta.name]
        for archivo in sorted(archivos):
            try:
                with Image.open(archivo) as im:
                    im.load()
                    huella = dhash(im)
            except Exception:  # noqa: BLE001 - cualquier fallo deja la imagen fuera
                corruptas.append(str(archivo.relative_to(RAIZ)))
                continue
            registros.append(
                Registro(
                    ruta=str(archivo.relative_to(RAIZ)).replace("\\", "/"),
                    clase=material["clase"],
                    huella=huella,
                    bolsa=material["bolsa"],
                )
            )

    return registros, corruptas, sorted(desconocidas)


def escribir_manifiesto(
    destino: Path, registros: list[Registro], partes: dict[str, list[Registro]]
) -> None:
    parte_de = {r.ruta: nombre for nombre, items in partes.items() for r in items}
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["ruta", "clase", "material", "bolsa", "huella", "parte"])
        for r in registros:
            escritor.writerow(
                [
                    r.ruta,
                    r.clase,
                    POR_CLASE[r.clase]["material"],
                    r.bolsa,
                    f"{r.huella:016x}",
                    parte_de[r.ruta],
                ]
            )


def exportar_tm(
    train: list[Registro],
    destino: Path,
    por_clase: int = 180,
    lado: int = 224,
    semilla: int = 42,
) -> dict[str, int]:
    """Copia un subconjunto equilibrado y liviano para Teachable Machine.

    Teachable Machine colapsa la pestaña del navegador con miles de imágenes
    grandes; 180 por clase a 224 px entra sin problema y mantiene el reparto
    estratificado del split de entrenamiento.
    """
    import random

    rng = random.Random(semilla)
    por_clase_dict: dict[str, list[Registro]] = {}
    for r in train:
        por_clase_dict.setdefault(r.clase, []).append(r)

    exportadas: dict[str, int] = {}
    for clase, items in sorted(por_clase_dict.items()):
        muestra = sorted(items, key=lambda r: r.ruta)
        rng.shuffle(muestra)
        carpeta = destino / clase
        carpeta.mkdir(parents=True, exist_ok=True)

        for i, r in enumerate(muestra[:por_clase]):
            with Image.open(RAIZ / r.ruta) as im:
                im = im.convert("RGB").resize((lado, lado), Image.Resampling.BILINEAR)
                im.save(carpeta / f"{clase.replace(' ', '_').lower()}_{i:03d}.jpg", "JPEG", quality=90)
        exportadas[clase] = len(muestra[:por_clase])

    return exportadas



def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--raiz", default="datos/realwaste/realwaste-main/RealWaste", type=Path
    )
    ap.add_argument("--csv", default="datos/manifiesto.csv", type=Path)
    ap.add_argument("--resumen", default="datos/resumen_datos.json", type=Path)
    ap.add_argument("--umbral", type=int, default=6)
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument(
        "--tm",
        default="datos/train_tm_224",
        type=Path,
        help="carpeta del subconjunto para Teachable Machine; vacío para omitir",
    )
    args = ap.parse_args()

    raiz = RAIZ / args.raiz if not args.raiz.is_absolute() else args.raiz
    if not raiz.exists():
        raise SystemExit(f"no existe la carpeta de RealWaste: {raiz}")

    print(f"Leyendo {raiz.relative_to(RAIZ)} ...")
    registros, corruptas, desconocidas = inventariar(raiz)
    print(f"  imágenes válidas: {len(registros)}")
    print(f"  corruptas:        {len(corruptas)}")
    if desconocidas:
        print(f"  carpetas ignoradas: {desconocidas}")

    faltan = sorted(set(POR_CLASE) - {r.clase for r in registros})
    if faltan:
        raise SystemExit(f"faltan clases de RealWaste: {faltan}")

    unicos = deduplicar(registros, umbral=args.umbral)
    print(f"  duplicados (<= {args.umbral} bits): {len(registros) - len(unicos)}")

    partes = partir_estratificado(unicos, semilla=args.semilla)
    escribir_manifiesto(RAIZ / args.csv, unicos, partes)

    resumen = {
        "dataset": "RealWaste (UCI 908)",
        "umbral_dhash": args.umbral,
        "semilla": args.semilla,
        "leidas": len(registros),
        "corruptas": len(corruptas),
        "duplicadas": len(registros) - len(unicos),
        "total": len(unicos),
        "por_parte": {k: len(v) for k, v in partes.items()},
        "por_clase": {
            clase: dict(Counter(r.clase for r in unicos))
            for clase in sorted({r.clase for r in unicos})
        },
        "por_bolsa": dict(Counter(r.bolsa for r in unicos)),
    }
    destino_resumen = RAIZ / args.resumen
    destino_resumen.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nReparto:")
    for nombre, items in partes.items():
        print(f"  {nombre:5} {len(items):5}  ({len(items) / len(unicos):.1%})")
    print("\nPor bolsa:")
    for bolsa, n in sorted(resumen["por_bolsa"].items()):
        print(f"  {bolsa:7} {n:5}")
    print(f"\nManifiesto: {args.csv}")
    print(f"Resumen:    {args.resumen}")

    if args.tm:
        print(f"\nExportando subconjunto TM a {args.tm} ...")
        exportadas = exportar_tm(partes["train"], RAIZ / args.tm, semilla=args.semilla)
        for clase, n in exportadas.items():
            print(f"  {clase:22} {n:4}")
        print(f"  total {sum(exportadas.values())}")


if __name__ == "__main__":
    main()
