"""Paso 2: figuras del EDA para el informe (300 dpi).

Lee `datos/manifiesto.csv` y produce en `figs/`:

1. Distribución de imágenes por material, coloreada por bolsa normativa.
2. Reparto por bolsa y estratificación train/val/test.
3. Mosaico de muestras reales (RealWaste) frente a estudio (TrashNet).

Uso:
    .\\\\.venv\\\\Scripts\\\\python.exe src\\\\s02_eda.py
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parents[1]
FIGS = RAIZ / "figs"

PAPEL = "#F4F3EE"
TINTA = "#18181B"
GRIS = "#6B6B70"
COLOR = {"blanca": "#EDEDF0", "verde": "#16A34A", "negra": "#18181B"}
BORDE = {"blanca": "#D4D4D8", "verde": "#15803D", "negra": "#000000"}
ETIQUETA = {
    "blanca": "Blanca · aprovechables",
    "verde": "Verde · orgánicos",
    "negra": "Negra · no aprovechables",
}
ORDEN_PARTES = ("train", "val", "test")
RUTA_REALWASTE = RAIZ / "datos/realwaste/realwaste-main/RealWaste"
RUTA_TRASHNET = RAIZ / "datos/trashnet/dataset-resized"
CLASES_TRASHNET = ("cardboard", "glass", "metal", "paper", "plastic", "trash")


def leer_manifiesto() -> list[dict[str, str]]:
    with (RAIZ / "datos/manifiesto.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def entero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def pct(x: float, decimales: int = 1) -> str:
    return f"{x * 100:.{decimales}f}".replace(".", ",") + " %"


def estilo() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "text.color": TINTA,
            "axes.labelcolor": TINTA,
            "axes.edgecolor": TINTA,
            "axes.linewidth": 0.8,
            "xtick.color": GRIS,
            "ytick.color": TINTA,
            "figure.facecolor": PAPEL,
            "savefig.facecolor": PAPEL,
        }
    )


def _guardar(fig: plt.Figure, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=300, bbox_inches="tight", facecolor=PAPEL)
    plt.close(fig)
    print(f"  {destino.relative_to(RAIZ)}")


def figura_clases(filas: list[dict[str, str]]) -> None:
    conteo = Counter(f["material"] for f in filas)
    bolsa_de = {f["material"]: f["bolsa"] for f in filas}
    total = len(filas)

    pares = sorted(conteo.items(), key=lambda kv: (-kv[1], kv[0]))
    nombres = [m for m, _ in pares]
    valores = [n for _, n in pares]
    bolsas = [bolsa_de[m] for m in nombres]
    y = list(range(len(nombres)))[::-1]

    fig, ax = plt.subplots(figsize=(7.4, 4.5))
    ax.set_facecolor(PAPEL)
    ax.barh(
        y,
        valores,
        height=0.62,
        color=[COLOR[b] for b in bolsas],
        edgecolor=[BORDE[b] for b in bolsas],
        linewidth=1.1,
    )

    for yi, valor in zip(y, valores):
        ax.text(
            valor + max(valores) * 0.015,
            yi,
            f"{entero(valor)}  ·  {pct(valor / total)}",
            va="center",
            ha="left",
            fontsize=9,
            color=TINTA,
        )

    ax.set_yticks(y, nombres)
    ax.set_xlim(0, max(valores) * 1.28)
    ax.set_xlabel("Imágenes únicas tras deduplicación")
    ax.set_title(
        "Composición del corpus por material",
        loc="left",
        fontsize=14,
        fontweight="bold",
        pad=18,
    )
    ax.text(
        0,
        1.015,
        f"RealWaste (UCI 908) · {entero(total)} imágenes únicas · 535 duplicados eliminados (dHash ≤ 6 bits)",
        transform=ax.transAxes,
        fontsize=8.5,
        color=GRIS,
    )
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)

    leyenda = [
        Patch(facecolor=COLOR[b], edgecolor=BORDE[b], linewidth=1.1, label=ETIQUETA[b])
        for b in ("blanca", "verde", "negra")
    ]
    ax.legend(
        handles=leyenda,
        loc="lower right",
        frameon=False,
        fontsize=8.5,
        title="Bolsa Res. 2184/2019",
        title_fontsize=8.5,
    )
    _guardar(fig, FIGS / "eda_01_clases.png")


def figura_bolsas(filas: list[dict[str, str]]) -> None:
    total = len(filas)
    por_bolsa = Counter(f["bolsa"] for f in filas)
    por_parte: dict[str, Counter[str]] = defaultdict(Counter)
    for f in filas:
        por_parte[f["parte"]][f["bolsa"]] += 1

    fig, (izq, der) = plt.subplots(
        1, 2, figsize=(8.6, 3.9), gridspec_kw={"width_ratios": [1, 1.35]}
    )
    for ax in (izq, der):
        ax.set_facecolor(PAPEL)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)

    # Panel A: masa por bolsa normativa.
    bolsas = sorted(por_bolsa, key=lambda b: (-por_bolsa[b], b))
    valores = [por_bolsa[b] for b in bolsas]
    x = range(len(bolsas))
    izq.bar(
        x,
        valores,
        width=0.58,
        color=[COLOR[b] for b in bolsas],
        edgecolor=[BORDE[b] for b in bolsas],
        linewidth=1.1,
    )
    for xi, b, valor in zip(x, bolsas, valores):
        izq.text(
            xi,
            valor + max(valores) * 0.025,
            f"{entero(valor)}\n{pct(valor / total)}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    izq.set_xticks(x, [b.capitalize() for b in bolsas])
    izq.set_ylim(0, max(valores) * 1.22)
    izq.set_ylabel("Imágenes")
    izq.set_title("Masa por bolsa normativa", loc="left", fontsize=11, fontweight="bold")

    # Panel B: estratificación por parte.
    xs = range(len(ORDEN_PARTES))
    base = [0.0] * len(ORDEN_PARTES)
    for bolsa in ("blanca", "verde", "negra"):
        valores = [por_parte[p][bolsa] for p in ORDEN_PARTES]
        der.bar(
            xs,
            valores,
            bottom=base,
            width=0.55,
            color=COLOR[bolsa],
            edgecolor=BORDE[bolsa],
            linewidth=1.0,
            label=ETIQUETA[bolsa],
        )
        base = [a + b for a, b in zip(base, valores)]

    for xi, parte in zip(xs, ORDEN_PARTES):
        total_parte = sum(por_parte[parte].values())
        der.text(
            xi,
            total_parte + max(base) * 0.02,
            f"{entero(total_parte)}\n{pct(total_parte / total, 0)}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    der.set_xticks(xs, ["Entrenamiento" if p == "train" else "Validación" if p == "val" else "Prueba" for p in ORDEN_PARTES])
    der.set_ylim(0, max(base) * 1.22)
    der.set_title("Estratificación 70 / 15 / 15", loc="left", fontsize=11, fontweight="bold")
    der.legend(frameon=False, fontsize=8.5, loc="upper right")

    fig.suptitle(
        "Reparto del corpus y composición de cada partición",
        x=0.06,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _guardar(fig, FIGS / "eda_02_bolsas.png")


def _muestra(carpeta: Path) -> Image.Image:
    archivos = sorted(
        f for f in carpeta.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    with Image.open(archivos[len(archivos) // 2]) as im:
        return ImageOps.fit(im.convert("RGB"), (360, 360))


def figura_mosaico() -> None:
    realwaste = sorted(p.name for p in RUTA_REALWASTE.iterdir() if p.is_dir())
    fig = plt.figure(figsize=(9.4, 7.0))
    exterior = fig.add_gridspec(
        2, 1, height_ratios=[3, 1], hspace=0.12, top=0.86, bottom=0.15, left=0.05, right=0.95
    )

    arriba = exterior[0].subgridspec(3, 3, hspace=0.24, wspace=0.14)
    ultimo = None
    for i, clase in enumerate(realwaste):
        ax = fig.add_subplot(arriba[i // 3, i % 3])
        ax.imshow(_muestra(RUTA_REALWASTE / clase))
        ax.set_title(clase, fontsize=8.5, pad=3)
        ax.axis("off")
        ax.set_anchor("N")
        ultimo = ax

    abajo = exterior[1].subgridspec(1, 6, hspace=0, wspace=0.14)
    primero_abajo = None
    for i, clase in enumerate(CLASES_TRASHNET):
        ax = fig.add_subplot(abajo[0, i])
        ax.imshow(_muestra(RUTA_TRASHNET / clase))
        ax.set_title(clase, fontsize=8.5, pad=3)
        ax.axis("off")
        ax.set_anchor("S")
        if primero_abajo is None:
            primero_abajo = ax

    fig.text(
        0.05,
        0.975,
        "Muestras del dominio real frente al dominio de estudio",
        fontsize=14,
        fontweight="bold",
        va="top",
    )
    fig.text(
        0.05,
        0.938,
        "Arriba: RealWaste, residuos fotografiados en un relleno sanitario (9 clases, entrenamiento y prueba).",
        fontsize=8.5,
        color=GRIS,
        va="top",
    )

    assert primero_abajo is not None
    caja = primero_abajo.get_position()
    fig.text(
        0.05,
        caja.y0 - 0.028,
        "Abajo: TrashNet, objetos sobre fondo blanco (6 clases, solo prueba externa de cambio de dominio).",
        fontsize=8.5,
        color=GRIS,
        va="top",
    )
    _guardar(fig, FIGS / "eda_03_mosaico.png")


def main() -> None:
    estilo()
    filas = leer_manifiesto()
    print(f"Manifiesto: {len(filas)} imágenes")
    figura_clases(filas)
    figura_bolsas(filas)
    figura_mosaico()


if __name__ == "__main__":
    main()
