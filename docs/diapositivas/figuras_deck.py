"""Figuras de la presentación, con la paleta institucional de La Salle.

Se regeneran desde `models/metrics.json`, `models/umbral.json` y la Tabla 1 del
informe, de modo que las diapositivas no contradigan al informe ni a los guiones.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
FIGS = Path(__file__).resolve().parent / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

AZUL = "#003057"
AMARILLO = "#F2A900"
GRIS = "#7C8B99"
TINTA = "#1A1A1A"
ROJO = "#CB333B"
VERDE = "#4A773C"

plt.rcParams.update(
    {
        "font.family": "Segoe UI",
        "font.size": 11,
        "text.color": TINTA,
        "axes.labelcolor": TINTA,
        "axes.edgecolor": "#C9D2DA",
        "axes.linewidth": 0.8,
        "xtick.color": TINTA,
        "ytick.color": TINTA,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#E6EBEF",
        "grid.linewidth": 0.8,
        "savefig.facecolor": "white",
    }
)

coma = FuncFormatter(lambda x, _: f"{x:.1f}".replace(".", ","))


def guardar(fig: plt.Figure, nombre: str) -> None:
    ruta = FIGS / nombre
    fig.savefig(ruta, dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"{nombre}: {Image.open(ruta).size[0]}x{Image.open(ruta).size[1]}")


def curva_umbral() -> None:
    datos = json.loads((RAIZ / "models" / "umbral.json").read_text(encoding="utf-8"))
    curva = datos["curva"]
    tau = [p["tau"] for p in curva]
    cob = [p["cobertura"] for p in curva]
    mat = [p["exactitud_material"] for p in curva]
    bol = [p["exactitud_bolsa"] for p in curva]

    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.plot(tau, cob, color=AZUL, lw=2.6, label="Cobertura")
    ax.plot(tau, mat, color=AMARILLO, lw=2.6, label="Exactitud de material")
    ax.plot(tau, bol, color=GRIS, lw=1.6, ls="--", label="Exactitud de bolsa")

    ax.axvline(datos["tau"], color=ROJO, lw=1.3, ls=(0, (4, 3)))
    ax.annotate(
        f"τ* = {datos['tau']:.2f}".replace(".", ","),
        xy=(datos["tau"] + 0.012, 0.44),
        color=ROJO,
        fontsize=12,
        fontweight="bold",
    )

    ax.set_xlim(0.30, 0.95)
    ax.set_ylim(0.38, 1.02)
    ax.set_xlabel("Umbral de abstención τ", fontsize=11)
    ax.set_ylabel("Proporción sobre val/", fontsize=11)
    ax.yaxis.set_major_formatter(coma)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}".replace(".", ",")))
    ax.grid(axis="y")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", frameon=False, fontsize=10, handlelength=2.2)
    guardar(fig, "curva_umbral.png")


def f1_clases() -> None:
    datos = json.loads((RAIZ / "models" / "metrics.json").read_text(encoding="utf-8"))
    clases = sorted(
        datos["modelos"]["modelB_improved"]["test"]["por_clase"],
        key=lambda c: c["f1"],
        reverse=True,
    )
    nombres = [c["material"] for c in clases]
    valores = [c["f1"] for c in clases]
    peor = min(valores)
    colores = [AMARILLO if v == peor else AZUL for v in valores]

    fig, ax = plt.subplots(figsize=(5.5, 4.1))
    barras = ax.barh(nombres, valores, color=colores, height=0.62)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.06)
    ax.set_xlabel("F1 por clase (test, Modelo B)", fontsize=10.5)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}".replace(".", ",")))
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0, labelsize=10.5)

    for barra, valor in zip(barras, valores):
        ax.text(
            valor + 0.008,
            barra.get_y() + barra.get_height() / 2,
            f"{valor:.3f}".replace(".", ","),
            va="center",
            fontsize=9.5,
            color=TINTA,
            fontweight="bold" if valor == peor else "normal",
        )
    guardar(fig, "f1_clases.png")


def matriz_bolsas() -> None:
    datos = json.loads((RAIZ / "models" / "metrics.json").read_text(encoding="utf-8"))
    matriz = datos["modelos"]["modelB_improved"]["test"]["bolsas"]["matriz_bolsas"]
    bolsas = ["Blanca", "Verde", "Negra"]
    # Se colorea por proporcion de la fila real: asi el diagonal se lee parejo y
    # los errores resaltan por su peso relativo, no por el conteo absoluto.
    proporcion = [[valor / sum(fila) for valor in fila] for fila in matriz]

    cmap = LinearSegmentedColormap.from_list("unisalle", ["#FFFFFF", "#DCE6EF", AZUL])
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    ax.imshow(proporcion, cmap=cmap, vmin=0, vmax=1)
    ax.set_xticks(range(3), bolsas)
    ax.set_yticks(range(3), bolsas)
    ax.set_xlabel("Bolsa predicha", fontsize=10.5)
    ax.set_ylabel("Bolsa real", fontsize=10.5)
    ax.tick_params(length=0, labelsize=10.5)
    ax.grid(visible=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for i, fila in enumerate(matriz):
        for j, valor in enumerate(fila):
            peligro = i == 2 and j < 2  # negra -> aprovechable: el error que contamina
            ax.text(
                j,
                i,
                str(valor),
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                color=ROJO if peligro else ("white" if proporcion[i][j] > 0.45 else TINTA),
            )
    guardar(fig, "matriz_bolsas.png")


def dominio() -> None:
    datos = json.loads((RAIZ / "models" / "metrics.json").read_text(encoding="utf-8"))
    a = datos["modelos"]["modelA_tm"]
    b = datos["modelos"]["modelB_improved"]
    valores_a = [a["test"]["exactitud"] * 100, a["trashnet"]["material_compartido"]["exactitud"] * 100]
    valores_b = [b["test"]["exactitud"] * 100, b["trashnet"]["material_compartido"]["exactitud"] * 100]

    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    x = range(2)
    ancho = 0.34
    ba = ax.bar([i - ancho / 2 for i in x], valores_a, ancho, color=GRIS, label="Modelo A")
    bb = ax.bar([i + ancho / 2 for i in x], valores_b, ancho, color=AZUL, label="Modelo B")
    ax.set_xticks(list(x), ["RealWaste (test)", "TrashNet"])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Exactitud de material (%)", fontsize=10.5)
    ax.grid(axis="y")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", frameon=False, fontsize=10)

    for barras in (ba, bb):
        for barra in barras:
            ax.text(
                barra.get_x() + barra.get_width() / 2,
                barra.get_height() + 1.8,
                f"{barra.get_height() + 1e-9:.1f}".replace(".", ","),
                ha="center",
                fontsize=10.5,
                fontweight="bold",
                color=TINTA,
            )
    guardar(fig, "dominio.png")


def datos_clases() -> None:
    # Tabla 1 del informe: conteo original de RealWaste, antes de deduplicar.
    conteos = {
        "Plástico": 921,
        "Metal": 790,
        "Papel": 500,
        "No aprovechable": 495,
        "Cartón": 461,
        "Vegetación": 436,
        "Vidrio": 420,
        "Orgánicos": 411,
        "Textil": 318,
    }
    nombres = list(conteos)
    valores = list(conteos.values())
    colores = [AMARILLO if n == "Plástico" else AZUL for n in nombres]

    fig, ax = plt.subplots(figsize=(6.1, 3.9))
    barras = ax.barh(nombres, valores, color=colores, height=0.62)
    ax.invert_yaxis()
    ax.set_xlim(0, 1050)
    ax.set_xlabel("Imágenes originales por clase", fontsize=10.5)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0, labelsize=10.5)

    for barra, valor in zip(barras, valores):
        ax.text(
            valor + 14,
            barra.get_y() + barra.get_height() / 2,
            f"{valor}",
            va="center",
            fontsize=9.5,
            color=TINTA,
        )
    guardar(fig, "datos_clases.png")


def recorte_ci() -> None:
    """Recorta la cadena de jobs del run de CI para que sea legible en la diapositiva."""
    original = RAIZ / "informe" / "figs" / "ci_run.png"
    imagen = Image.open(original)
    ancho, alto = imagen.size
    caja = (
        int(ancho * 0.248),
        int(alto * 0.232),
        int(ancho * 0.995),
        int(alto * 0.545),
    )
    recorte = imagen.crop(caja)
    ruta = FIGS / "ci_cadena.png"
    recorte.save(ruta)
    print(f"ci_cadena.png: {recorte.size[0]}x{recorte.size[1]}")


if __name__ == "__main__":
    curva_umbral()
    f1_clases()
    matriz_bolsas()
    dominio()
    datos_clases()
    recorte_ci()
