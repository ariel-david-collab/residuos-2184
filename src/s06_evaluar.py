"""Paso 6: evaluación exhaustiva de los modelos A y B para el informe.

Evalúa sobre `test/` (RealWaste, sin tocar en el entrenamiento) y sobre TrashNet
(cambio de dominio) y produce:

- Exactitud, precisión, recall y F1 por clase, macro y ponderado por soporte.
- Matrices de confusión de 9 materiales y de 3 bolsas normativas.
- ROC uno-contra-el-resto y AUC por clase y macro.
- Exactitud top-2 y log-loss.
- Efecto de la abstención con el τ calibrado (cobertura y exactitud entre lo aceptado).
- `models/metrics.json` y figuras a 300 dpi en `figs/`.

TrashNet tiene seis clases; cinco son materiales de RealWaste. La prueba de
materiales se limita a esas cinco (un `trash` de TrashNet es una mezcla, no un
material) y la de bolsas usa las seis, con `trash` en la bolsa negra.

Uso:
    .\\\\.venv\\\\Scripts\\\\python.exe src\\\\s06_evaluar.py
    .\\\\.venv\\\\Scripts\\\\python.exe src\\\\s06_evaluar.py --limite 5
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from sklearn.metrics import (
    auc,
    confusion_matrix,
    log_loss,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
    top_k_accuracy_score,
)

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "api"))

from dominio import BOLSAS, MATERIALES, proyectar_bolsas  # noqa: E402
from imagen import cargar_bytes, preprocesar  # noqa: E402
from inferencia import Modelo  # noqa: E402

MANIFIESTO = RAIZ / "datos" / "manifiesto.csv"
MODELOS = RAIZ / "models"
FIGS = RAIZ / "figs"
SALIDA = MODELOS / "metrics.json"
UMBRAL = MODELOS / "umbral.json"
TRASHNET = RAIZ / "datos" / "trashnet" / "dataset-resized"

CLASES = [m["clase"] for m in MATERIALES]
MATERIALES_ES = [m["material"] for m in MATERIALES]
NOMBRES_BOLSA = list(BOLSAS)
BOLSA_DE = [m["bolsa"] for m in MATERIALES]
# TrashNet -> clases de RealWaste. `trash` no es un material: es una mezcla.
TRASHNET_MATERIAL = {
    "cardboard": "Cardboard",
    "glass": "Glass",
    "metal": "Metal",
    "paper": "Paper",
    "plastic": "Plastic",
}
TRASHNET_BOLSA = {**{k: "blanca" for k in ("cardboard", "glass", "metal", "paper", "plastic")}, "trash": "negra"}

PAPEL = "#F4F3EE"
TINTA = "#18181B"
GRIS = "#6B6B70"
VERDE = "#16A34A"
AMARILLO = "#E8B71A"
ROJO = "#C2410C"
PALETA = ("#18181B", "#16A34A", "#E8B71A", "#2563EB", "#C2410C", "#6B6B70", "#7C3AED", "#0D9488", "#B45309")
MAPA = LinearSegmentedColormap.from_list("papel_verde", (PAPEL, VERDE, "#0B5D2B"))
ETIQUETAS_CORTAS = {
    "Cardboard": "Cartón",
    "Food Organics": "Orgánicos",
    "Glass": "Vidrio",
    "Metal": "Metal",
    "Miscellaneous Trash": "No aprovech.",
    "Paper": "Papel",
    "Plastic": "Plástico",
    "Textile Trash": "Textil",
    "Vegetation": "Vegetación",
}


# ------------------------------------------------------------------ datos


def filas_manifiesto(parte: str, limite: int = 0) -> list[dict[str, str]]:
    with MANIFIESTO.open(encoding="utf-8", newline="") as archivo:
        filas = [f for f in csv.DictReader(archivo) if f["parte"] == parte]
    return _limitar(filas, limite)


def imagenes_trashnet(limite: int = 0) -> list[dict[str, str]]:
    filas = []
    for carpeta in sorted(p for p in TRASHNET.iterdir() if p.is_dir()):
        if carpeta.name not in TRASHNET_BOLSA:
            continue
        for archivo in sorted(carpeta.iterdir()):
            if archivo.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                filas.append(
                    {
                        "ruta": str(archivo.relative_to(RAIZ)).replace("\\", "/"),
                        "clase": carpeta.name,
                        "bolsa": TRASHNET_BOLSA[carpeta.name],
                    }
                )
    return _limitar(filas, limite)


def _limitar(filas: list[dict], limite: int) -> list[dict]:
    if not limite:
        return filas
    por_clase: dict[str, int] = {}
    elegidas = []
    for fila in filas:
        if por_clase.get(fila["clase"], 0) < limite:
            elegidas.append(fila)
            por_clase[fila["clase"]] = por_clase.get(fila["clase"], 0) + 1
    return elegidas


def probabilidades(modelo: Modelo, filas: list[dict]) -> np.ndarray:
    salida = np.empty((len(filas), len(CLASES)), dtype=np.float64)
    for i, fila in enumerate(filas, start=1):
        imagen = cargar_bytes((RAIZ / fila["ruta"]).read_bytes())
        salida[i - 1] = modelo.predecir(preprocesar(imagen))
        if i % 500 == 0 or i == len(filas):
            print(f"  {i}/{len(filas)} imágenes")
    # El ONNX de Teachable Machine devuelve float32 y la suma queda en 0.9997;
    # normalizar la fila deja probabilidades bien definidas para log-loss.
    return salida / salida.sum(axis=1, keepdims=True)


# --------------------------------------------------------------- métricas


def metricas_material(probs: np.ndarray, real: np.ndarray) -> dict:
    pred = probs.argmax(axis=1)
    p, r, f1, soporte = precision_recall_fscore_support(
        real, pred, labels=range(len(CLASES)), zero_division=0
    )
    pm, rm, fm, _ = precision_recall_fscore_support(
        real, pred, labels=range(len(CLASES)), average="macro", zero_division=0
    )
    pp, rp, fp, _ = precision_recall_fscore_support(
        real, pred, labels=range(len(CLASES)), average="weighted", zero_division=0
    )
    aucs = np.array([roc_auc_score((real == i).astype(int), probs[:, i]) for i in range(len(CLASES))])
    return {
        "imagenes": int(len(real)),
        "exactitud": round(float((pred == real).mean()), 4),
        "exactitud_top2": round(float(top_k_accuracy_score(real, probs, k=2, labels=range(len(CLASES)))), 4),
        "log_loss": round(float(log_loss(real, probs, labels=range(len(CLASES)))), 4),
        "macro": {"precision": round(float(pm), 4), "recall": round(float(rm), 4), "f1": round(float(fm), 4)},
        "ponderado": {"precision": round(float(pp), 4), "recall": round(float(rp), 4), "f1": round(float(fp), 4)},
        "auc_macro": round(float(np.mean(aucs)), 4),
        "por_clase": [
            {
                "clase": CLASES[i],
                "material": MATERIALES_ES[i],
                "bolsa": BOLSA_DE[i],
                "precision": round(float(p[i]), 4),
                "recall": round(float(r[i]), 4),
                "f1": round(float(f1[i]), 4),
                "auc": round(float(aucs[i]), 4),
                "soporte": int(soporte[i]),
            }
            for i in range(len(CLASES))
        ],
        "matriz_materiales": confusion_matrix(real, pred, labels=range(len(CLASES))).tolist(),
    }


def probs_bolsa(probs: np.ndarray) -> np.ndarray:
    salida = np.empty((len(probs), len(NOMBRES_BOLSA)))
    for i, fila in enumerate(probs):
        bolsas = proyectar_bolsas(fila)
        salida[i] = [bolsas[n] for n in NOMBRES_BOLSA]
    return salida


def metricas_bolsa(probs: np.ndarray, real: np.ndarray) -> dict:
    pb = probs_bolsa(probs)
    pred = pb.argmax(axis=1)
    p, r, f1, soporte = precision_recall_fscore_support(
        real, pred, labels=range(len(NOMBRES_BOLSA)), zero_division=0
    )
    pm, rm, fm, _ = precision_recall_fscore_support(
        real, pred, labels=range(len(NOMBRES_BOLSA)), average="macro", zero_division=0
    )
    return {
        "exactitud": round(float((pred == real).mean()), 4),
        "macro": {"precision": round(float(pm), 4), "recall": round(float(rm), 4), "f1": round(float(fm), 4)},
        "por_bolsa": [
            {
                "bolsa": NOMBRES_BOLSA[i],
                "precision": round(float(p[i]), 4),
                "recall": round(float(r[i]), 4),
                "f1": round(float(f1[i]), 4),
                "soporte": int(soporte[i]),
            }
            for i in range(len(NOMBRES_BOLSA))
        ],
        "matriz_bolsas": confusion_matrix(real, pred, labels=range(len(NOMBRES_BOLSA))).tolist(),
    }


def efecto_abstencion(probs: np.ndarray, real_material: np.ndarray, real_bolsa: np.ndarray, tau: float) -> dict:
    confianza = probs.max(axis=1)
    aceptadas = confianza >= tau
    if not aceptadas.any():
        return {"tau": tau, "cobertura": 0.0, "exactitud_material": None, "exactitud_bolsa": None}
    pred_material = probs.argmax(axis=1)
    pred_bolsa = probs_bolsa(probs).argmax(axis=1)
    return {
        "tau": tau,
        "cobertura": round(float(aceptadas.mean()), 4),
        "exactitud_material": round(float((pred_material[aceptadas] == real_material[aceptadas]).mean()), 4),
        "exactitud_bolsa": round(float((pred_bolsa[aceptadas] == real_bolsa[aceptadas]).mean()), 4),
    }


def metricas_trashnet(probs: np.ndarray, filas: list[dict], tau: float) -> dict:
    """Cambio de dominio: materiales compartidos y bolsas normativas."""
    en_material = [i for i, f in enumerate(filas) if f["clase"] in TRASHNET_MATERIAL]
    compartidas = sorted({TRASHNET_MATERIAL[filas[i]["clase"]] for i in en_material}, key=CLASES.index)
    indices = [CLASES.index(c) for c in compartidas]
    sub = probs[en_material]
    real_local = np.array([indices.index(CLASES.index(TRASHNET_MATERIAL[filas[i]["clase"]])) for i in en_material])
    # Sexta etiqueta para "predijo otro material": cuenta como error, no como acierto.
    pred = np.array([indices.index(p) if p in indices else len(compartidas) for p in sub.argmax(axis=1)])
    p, r, f1, soporte = precision_recall_fscore_support(
        real_local, pred, labels=range(len(compartidas)), zero_division=0
    )
    pm, rm, fm, _ = precision_recall_fscore_support(
        real_local, pred, labels=range(len(compartidas)), average="macro", zero_division=0
    )
    aciertos = pred == real_local
    material = {
        "clases": compartidas,
        "imagenes": int(len(sub)),
        "exactitud": round(float(aciertos.mean()), 4),
        "macro": {"precision": round(float(pm), 4), "recall": round(float(rm), 4), "f1": round(float(fm), 4)},
        "por_clase": [
            {
                "clase": compartidas[i],
                "precision": round(float(p[i]), 4),
                "recall": round(float(r[i]), 4),
                "f1": round(float(f1[i]), 4),
                "soporte": int(soporte[i]),
            }
            for i in range(len(compartidas))
        ],
        "matriz": confusion_matrix(real_local, pred, labels=range(len(compartidas) + 1)).tolist(),
        "con_abstencion": _cobertura(sub.max(axis=1), aciertos, tau),
    }

    real_bolsa = np.array([NOMBRES_BOLSA.index(f["bolsa"]) for f in filas])
    bolsa = metricas_bolsa(probs, real_bolsa)
    bolsa["con_abstencion"] = _cobertura(
        probs.max(axis=1), probs_bolsa(probs).argmax(axis=1) == real_bolsa, tau
    )
    return {"material_compartido": material, "bolsas": bolsa}


def _cobertura(confianza: np.ndarray, aciertos: np.ndarray, tau: float) -> dict:
    aceptadas = confianza >= tau
    if not aceptadas.any():
        return {"tau": tau, "cobertura": 0.0, "exactitud": None}
    return {
        "tau": tau,
        "cobertura": round(float(aceptadas.mean()), 4),
        "exactitud": round(float(aciertos[aceptadas].mean()), 4),
    }


# ---------------------------------------------------------------- figuras


def estilo() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
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


def _matriz(ax: plt.Axes, matriz: list[list[int]], etiquetas: list[str], titulo: str) -> None:
    datos = np.asarray(matriz, dtype=float)
    filas = datos.sum(axis=1, keepdims=True)
    norm = np.divide(datos, filas, out=np.zeros_like(datos), where=filas > 0)
    ax.imshow(norm, cmap=MAPA, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(etiquetas)))
    ax.set_yticks(range(len(etiquetas)))
    ax.set_xticklabels(etiquetas, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(etiquetas, fontsize=7)
    ax.set_xlabel("Predicho")
    ax.set_ylabel("Real")
    ax.set_title(titulo, fontsize=8.5, loc="left", pad=6)
    for i in range(len(etiquetas)):
        for j in range(len(etiquetas)):
            valor = norm[i, j]
            if valor >= 0.005:
                ax.text(
                    j, i, f"{valor * 100:.0f}",
                    ha="center", va="center", fontsize=6.2,
                    color="#FFFFFF" if valor > 0.55 else TINTA,
                )
    ax.set_xticks(np.arange(-0.5, len(etiquetas), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(etiquetas), 1), minor=True)
    ax.grid(which="minor", color=PAPEL, linewidth=1.2)
    ax.tick_params(which="minor", length=0)


def figura_matrices(resultados: dict, nombres: list[str]) -> None:
    fig, ejes = plt.subplots(1, len(nombres), figsize=(11.4, 5.0))
    if len(nombres) == 1:
        ejes = [ejes]
    for ax, nombre in zip(ejes, nombres):
        _matriz(
            ax,
            resultados[nombre]["test"]["matriz_materiales"],
            [ETIQUETAS_CORTAS[c] for c in CLASES],
            f"{nombre} · exactitud {resultados[nombre]['test']['exactitud']:.1%}",
        )
    fig.suptitle(
        "Matriz de confusión por material sobre test (RealWaste), % por fila",
        fontsize=10, x=0.01, ha="left", color=TINTA,
    )
    fig.tight_layout()
    _guardar(fig, FIGS / "eval_01_matriz_materiales.png")


def figura_bolsas(resultados: dict, nombres: list[str]) -> None:
    fig, ejes = plt.subplots(1, len(nombres), figsize=(8.6, 3.4))
    if len(nombres) == 1:
        ejes = [ejes]
    etiquetas = [BOLSAS[b]["nombre"] for b in NOMBRES_BOLSA]
    for ax, nombre in zip(ejes, nombres):
        _matriz(
            ax,
            resultados[nombre]["test"]["bolsas"]["matriz_bolsas"],
            etiquetas,
            f"{nombre} · exactitud {resultados[nombre]['test']['bolsas']['exactitud']:.1%}",
        )
    fig.suptitle(
        "Matriz de confusión por bolsa normativa (Resolución 2184 de 2019), % por fila",
        fontsize=10, x=0.01, ha="left", color=TINTA,
    )
    fig.tight_layout()
    _guardar(fig, FIGS / "eval_02_matriz_bolsas.png")


def figura_clases(resultados: dict, nombres: list[str]) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.set_facecolor(PAPEL)
    posiciones = np.arange(len(CLASES))
    ancho = 0.8 / max(1, len(nombres))
    for k, nombre in enumerate(nombres):
        valores = [c["f1"] for c in resultados[nombre]["test"]["por_clase"]]
        ax.barh(
            posiciones + (k - (len(nombres) - 1) / 2) * ancho, valores, height=ancho * 0.92,
            color=PALETA[k % len(PALETA)], edgecolor=TINTA, linewidth=0.5, label=nombre,
        )
    ax.set_yticks(posiciones)
    ax.set_yticklabels([ETIQUETAS_CORTAS[c] for c in CLASES])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("F1 por clase")
    ax.grid(axis="x", color="#D9D7CE", linewidth=0.6)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.legend(
        frameon=False, fontsize=7.5, ncol=len(nombres),
        loc="upper center", bbox_to_anchor=(0.5, -0.12),
    )
    fig.suptitle("F1 por material sobre test", fontsize=10, x=0.01, ha="left", color=TINTA)
    fig.tight_layout()
    _guardar(fig, FIGS / "eval_03_f1_clases.png")


def figura_roc(probs: np.ndarray, real: np.ndarray, nombre: str, auc_macro: float) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    ax.set_facecolor(PAPEL)
    for i, clase in enumerate(CLASES):
        fpr, tpr, _ = roc_curve((real == i).astype(int), probs[:, i])
        ax.plot(fpr, tpr, color=PALETA[i], linewidth=1.15, label=f"{ETIQUETAS_CORTAS[clase]} · {auc(fpr, tpr):.3f}")
    ax.plot([0, 1], [0, 1], color=GRIS, linewidth=0.8, linestyle=(0, (4, 3)))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.01)
    ax.set_xlabel("Falsos positivos")
    ax.set_ylabel("Verdaderos positivos")
    ax.grid(color="#D9D7CE", linewidth=0.5)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.legend(frameon=False, fontsize=6.4, loc="lower right", title="AUC OvR", title_fontsize=6.6)
    ax.set_title(f"ROC uno-contra-el-resto · {nombre} · macro {auc_macro:.3f}", fontsize=9, loc="left")
    fig.tight_layout()
    _guardar(fig, FIGS / f"eval_04_roc_{'b' if nombre == 'modelB_improved' else 'a'}.png")


def figura_cobertura(curva: list[dict], tau: float) -> None:
    validos = [p for p in curva if p["exactitud_material"] is not None]
    taus = [p["tau"] for p in validos]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.set_facecolor(PAPEL)
    ax.plot(taus, [p["cobertura"] for p in validos], color=TINTA, linewidth=1.6, label="Cobertura")
    ax.plot(taus, [p["exactitud_material"] for p in validos], color=VERDE, linewidth=1.6, label="Exactitud de material")
    ax.plot(taus, [p["exactitud_bolsa"] for p in validos], color=AMARILLO, linewidth=1.6, label="Exactitud de bolsa")
    ax.axvline(tau, color=ROJO, linewidth=1.0, linestyle=(0, (4, 3)))
    ax.annotate(
        f"τ* = {tau:.2f}", xy=(tau, 0.02), xytext=(tau + 0.015, 0.06), fontsize=7.5, color=ROJO,
    )
    ax.set_xlim(min(taus), max(taus))
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Umbral de abstención τ")
    ax.set_ylabel("Proporción sobre val")
    ax.grid(color="#D9D7CE", linewidth=0.5)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")
    ax.set_title("Cobertura frente a exactitud al variar el umbral", fontsize=9, loc="left")
    fig.tight_layout()
    _guardar(fig, FIGS / "eval_05_cobertura_umbral.png")


def figura_trashnet(resultados: dict, nombre: str) -> None:
    datos = resultados[nombre]["trashnet"]
    material = datos["material_compartido"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.8), gridspec_kw={"width_ratios": [1.35, 1]})
    for ax in (ax1, ax2):
        ax.set_facecolor(PAPEL)
        ax.grid(axis="y", color="#D9D7CE", linewidth=0.5)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)

    posiciones = np.arange(len(material["clases"]))
    ax1.bar(posiciones - 0.19, [c["recall"] for c in material["por_clase"]], width=0.36, color=VERDE,
            edgecolor=TINTA, linewidth=0.5, label="TrashNet (dominio externo)")
    ax1.bar(posiciones + 0.19, [c["recall"] for c in resultados[nombre]["test"]["por_clase"] if c["clase"] in material["clases"]],
            width=0.36, color=TINTA, edgecolor=TINTA, linewidth=0.5, label="RealWaste test")
    ax1.set_xticks(posiciones)
    ax1.set_xticklabels([ETIQUETAS_CORTAS[c] for c in material["clases"]], fontsize=8)
    ax1.set_ylim(0, 1.18)
    ax1.set_ylabel("Recall (material)")
    ax1.legend(
        frameon=False, fontsize=6.8, ncol=2, loc="upper center",
        bbox_to_anchor=(0.5, 1.01), handlelength=1.4, columnspacing=1.4,
    )
    ax1.set_title("Materiales compartidos, sin abstención", fontsize=8.5, loc="left")

    sin = [material["exactitud"], datos["bolsas"]["exactitud"]]
    con = [material["con_abstencion"]["exactitud"], datos["bolsas"]["con_abstencion"]["exactitud"]]
    if None in con:
        con = [x if x is not None else 0.0 for x in con]
    x = np.arange(2)
    ax2.bar(x - 0.19, sin, width=0.36, color=GRIS, edgecolor=TINTA, linewidth=0.5, label="Sin abstención")
    ax2.bar(x + 0.19, con, width=0.36, color=VERDE, edgecolor=TINTA, linewidth=0.5,
            label=f"Con abstención (τ={material['con_abstencion']['tau']:.2f})")
    if material["con_abstencion"]["cobertura"] > 0:
        for i in range(2):
            ax2.text(i - 0.19, sin[i] + 0.02, f"{sin[i]:.0%}", ha="center", fontsize=7, color=TINTA)
            ax2.text(i + 0.19, con[i] + 0.02, f"{con[i]:.0%}", ha="center", fontsize=7, color=TINTA)
    ax2.set_xticks(x)
    ax2.set_xticklabels(["Material", "Bolsa"], fontsize=8)
    ax2.set_ylim(0, 1.22)
    ax2.set_ylabel("Exactitud")
    ax2.legend(
        frameon=False, fontsize=6.8, ncol=2, loc="upper center",
        bbox_to_anchor=(0.5, 1.01), handlelength=1.4, columnspacing=1.4,
    )
    ax2.set_title(
        f"Cobertura {material['con_abstencion']['cobertura']:.0%} · {material['imagenes']} imágenes",
        fontsize=8.5, loc="left",
    )
    fig.suptitle(f"Cambio de dominio RealWaste → TrashNet · {nombre}", fontsize=10, x=0.01, ha="left", color=TINTA)
    fig.tight_layout()
    _guardar(fig, FIGS / f"eval_06_trashnet_{'b' if nombre == 'modelB_improved' else 'a'}.png")


# -------------------------------------------------------------------- main


def evaluar(ruta: Path, tau: float, limite: int) -> dict:
    modelo = Modelo(ruta)
    print(f"\nModelo: {modelo.nombre} · {ruta.name}")

    inicio = time.perf_counter()
    filas = filas_manifiesto("test", limite)
    probs = probabilidades(modelo, filas)
    real_material = np.array([CLASES.index(f["clase"]) for f in filas])
    real_bolsa = np.array([NOMBRES_BOLSA.index(f["bolsa"]) for f in filas])
    test = metricas_material(probs, real_material)
    test["bolsas"] = metricas_bolsa(probs, real_bolsa)
    test["abstencion"] = efecto_abstencion(probs, real_material, real_bolsa, tau)
    print(
        f"  test: exactitud {test['exactitud']:.1%} · macro F1 {test['macro']['f1']:.3f}"
        f" · bolsa {test['bolsas']['exactitud']:.1%} · AUC {test['auc_macro']:.3f}"
    )

    filas_externas = imagenes_trashnet(limite)
    probs_externas = probabilidades(modelo, filas_externas)
    externo = metricas_trashnet(probs_externas, filas_externas, tau)
    print(
        f"  TrashNet: material {externo['material_compartido']['exactitud']:.1%}"
        f" · bolsa {externo['bolsas']['exactitud']:.1%}"
        f" · con τ {externo['material_compartido']['con_abstencion']['cobertura']:.1%} de cobertura"
    )
    segundos = round(time.perf_counter() - inicio, 1)

    return {
        "archivo": str(ruta.relative_to(RAIZ)).replace("\\", "/"),
        "segundos": segundos,
        "test": test,
        "trashnet": externo,
        "probabilidades_test": probs,
        "reales_test": real_material,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa los modelos A y B sobre test y TrashNet.")
    parser.add_argument("--limite", type=int, default=0, help="imágenes por clase (prueba rápida)")
    parser.add_argument("--salida", type=Path, default=SALIDA)
    args = parser.parse_args()

    tau = 0.63
    if UMBRAL.exists():
        tau = float(json.loads(UMBRAL.read_text(encoding="utf-8"))["tau"])
    estilo()

    candidatos = [MODELOS / "modelB_improved.onnx", MODELOS / "modelA_tm.onnx"]
    existentes = [p for p in candidatos if p.exists()]
    if not existentes:
        raise SystemExit("no hay modelos ONNX en models/")

    resultados: dict[str, dict] = {}
    for ruta in existentes:
        resultados[ruta.stem] = evaluar(ruta, tau, args.limite)
    nombres = list(resultados)

    print("\nFiguras")
    figura_matrices(resultados, nombres)
    figura_bolsas(resultados, nombres)
    figura_clases(resultados, nombres)
    for nombre in nombres:
        figura_roc(resultados[nombre]["probabilidades_test"], resultados[nombre]["reales_test"],
                   nombre, resultados[nombre]["test"]["auc_macro"])
        figura_trashnet(resultados, nombre)
    if UMBRAL.exists():
        figura_cobertura(json.loads(UMBRAL.read_text(encoding="utf-8"))["curva"], tau)

    salida = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "tau": tau,
        "test": "RealWaste test/ (partición reservada, sin uso en entrenamiento ni calibración)",
        "externo": "TrashNet dataset-resized (dominio externo); material solo en las 5 clases compartidas",
        "modelos": {
            nombre: {
                k: v for k, v in datos.items() if k not in ("probabilidades_test", "reales_test")
            }
            for nombre, datos in resultados.items()
        },
    }
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGuardado: {args.salida}")


if __name__ == "__main__":
    main()
