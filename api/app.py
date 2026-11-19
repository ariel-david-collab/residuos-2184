"""API del clasificador normativo de residuos (Resolución 2184 de 2019)."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

import imagen
from dominio import BOLSAS, MATERIALES, decidir
from inferencia import cargar

RAIZ = Path(__file__).resolve().parents[1]
DIST = RAIZ / "web" / "dist"
MAX_BYTES = 12 * 1024 * 1024


def _tau_calibrado() -> float:
    """Umbral sugerido por `src/s05_calibrar_umbral.py`; 0.55 si aún no existe."""
    ruta = RAIZ / "models" / "umbral.json"
    if not ruta.exists():
        return 0.55
    import json

    return float(json.loads(ruta.read_text(encoding="utf-8")).get("tau", 0.55))


def _metricas(nombre_modelo: str) -> dict | None:
    """Exactitud del modelo activo en `test/`, publicada por `src/s06_evaluar.py`."""
    ruta = RAIZ / "models" / "metrics.json"
    if not ruta.exists():
        return None
    import json

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    del_modelo = datos.get("modelos", {}).get(nombre_modelo)
    if not del_modelo:
        return None
    test = del_modelo["test"]
    return {
        "imagenes": test["imagenes"],
        "exactitud_material": test["exactitud"],
        "exactitud_bolsa": test["bolsas"]["exactitud"],
        "tau": datos.get("tau"),
    }


TAU = _tau_calibrado()

app = FastAPI(title="Residuos 2184", version="0.1.0")
modelo = cargar()
METRICAS = _metricas(modelo.nombre)


def _uno(datos: bytes, tau: float, nombre: str) -> dict:
    try:
        imagen_pil = imagen.cargar_bytes(datos)
    except Exception as exc:  # noqa: BLE001 - cualquier fallo es "no es una imagen"
        raise HTTPException(400, f"{nombre}: no se pudo leer la imagen") from exc

    inicio = time.perf_counter()
    probs = modelo.predecir(imagen.preprocesar(imagen_pil))
    decision = decidir(probs, tau)
    ms = (time.perf_counter() - inicio) * 1000

    bolsa = BOLSAS[decision.bolsa]
    return {
        "archivo": nombre,
        "material": decision.material["material"] if decision.material else None,
        "clase": decision.material["clase"] if decision.material else None,
        "bolsa": decision.bolsa,
        "bolsa_nombre": bolsa["nombre"],
        "bolsa_rotulo": bolsa["rotulo"],
        "bolsa_detalle": bolsa["detalle"],
        "bolsa_color": bolsa["color"],
        "bolsa_borde": bolsa["borde"],
        "bolsa_texto": bolsa["texto"],
        "confianza": round(decision.confianza, 4),
        "abstenido": decision.abstenido,
        "top3": [
            {"clase": t["clase"], "material": t["material"], "p": round(t["p"], 4)}
            for t in decision.top3
        ],
        "bolsas_prob": {k: round(v, 4) for k, v in decision.bolsas_prob.items()},
        "latencia_ms": round(ms, 1),
    }


@app.get("/api/health")
def salud() -> dict:
    return {"ok": True, "modelo": modelo.nombre, "clases": len(MATERIALES)}


@app.get("/api/catalogo")
def catalogo() -> dict:
    return {
        "materiales": MATERIALES,
        "bolsas": BOLSAS,
        "tau_sugerido": TAU,
        "metricas": METRICAS,
    }


@app.post("/api/predict")
async def predecir(archivo: UploadFile = File(...), tau: float = Form(TAU)) -> dict:
    datos = await archivo.read()
    if not datos:
        raise HTTPException(400, "archivo vacío")
    if len(datos) > MAX_BYTES:
        raise HTTPException(413, "la imagen supera 12 MB")
    return _uno(datos, tau, archivo.filename or "imagen")


@app.post("/api/predict-lote")
async def predecir_lote(
    archivos: list[UploadFile] = File(...), tau: float = Form(TAU)
) -> dict:
    if not archivos:
        raise HTTPException(400, "no se recibieron archivos")
    inicio = time.perf_counter()
    resultados = []
    for a in archivos:
        datos = await a.read()
        if not datos or len(datos) > MAX_BYTES:
            continue
        try:
            resultados.append(_uno(datos, tau, a.filename or "imagen"))
        except HTTPException:
            continue

    por_bolsa = {k: 0 for k in BOLSAS}
    por_material: dict[str, int] = {}
    for r in resultados:
        # Los chips deben sumar exactamente el total junto con "sin decidir".
        if not r["abstenido"]:
            por_bolsa[r["bolsa"]] += 1
        clave = r["material"] or "Sin decidir"
        por_material[clave] = por_material.get(clave, 0) + 1

    return {
        "total": len(resultados),
        "por_bolsa": por_bolsa,
        "por_material": por_material,
        "abstenidos": sum(1 for r in resultados if r["abstenido"]),
        "latencia_ms": round((time.perf_counter() - inicio) * 1000, 1),
        "resultados": resultados,
    }


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
else:  # pragma: no cover - sólo en desarrollo antes de compilar el WASM

    @app.get("/")
    def sin_interfaz() -> None:
        raise HTTPException(
            503, "el frontend no está compilado: ejecuta `trunk build --release` en web/"
        )
