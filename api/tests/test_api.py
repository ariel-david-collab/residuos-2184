"""Prueba de humo de la API: contrato HTTP del prototipo."""

import io

from fastapi.testclient import TestClient
from PIL import Image

from app import app

cliente = TestClient(app)


def png(color: tuple[int, int, int] = (120, 160, 90)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (320, 240), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_health_responde_el_modelo_activo():
    r = cliente.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["clases"] == 9


def test_catalogo_expone_las_tres_bolsas():
    r = cliente.get("/api/catalogo")
    assert r.status_code == 200
    assert set(r.json()["bolsas"]) == {"blanca", "verde", "negra"}


def test_catalogo_publica_la_exactitud_del_modelo_activo():
    """La línea de contexto de la interfaz sale de models/metrics.json."""
    datos = cliente.get("/api/catalogo").json()
    metricas = datos["metricas"]
    assert metricas is not None
    assert metricas["imagenes"] > 0
    assert 0.0 < metricas["exactitud_material"] <= 1.0
    assert 0.0 < metricas["exactitud_bolsa"] <= 1.0
    # La bolsa es más fácil que el material: cinco clases caen en la blanca.
    assert metricas["exactitud_bolsa"] >= metricas["exactitud_material"]


def test_predict_devuelve_una_decision_completa():
    r = cliente.post("/api/predict", files={"archivo": ("x.png", png(), "image/png")})
    assert r.status_code == 200
    datos = r.json()
    assert datos["bolsa"] in {"blanca", "verde", "negra"}
    assert 0.0 <= datos["confianza"] <= 1.0
    assert len(datos["top3"]) == 3
    assert datos["latencia_ms"] >= 0


def test_predict_se_abstiene_con_umbral_alto():
    r = cliente.post(
        "/api/predict",
        files={"archivo": ("x.png", png(), "image/png")},
        data={"tau": "0.999"},
    )
    assert r.status_code == 200
    assert r.json()["abstenido"] is True
    assert r.json()["material"] is None


def test_predict_rechaza_archivos_que_no_son_imagen():
    r = cliente.post("/api/predict", files={"archivo": ("x.txt", b"no soy imagen", "text/plain")})
    assert r.status_code == 400


def test_lote_cuenta_todas_las_bolsas():
    archivos = [
        ("archivos", ("a.png", png((240, 240, 235)), "image/png")),
        ("archivos", ("b.png", png((90, 150, 70)), "image/png")),
    ]
    r = cliente.post("/api/predict-lote", files=archivos)
    assert r.status_code == 200
    datos = r.json()
    assert datos["total"] == 2
    assert len(datos["resultados"]) == 2
    # Cada imagen cae en una sola categoría: una bolsa decidida o "sin decidir".
    assert sum(datos["por_bolsa"].values()) + datos["abstenidos"] == datos["total"]


def test_lote_sin_decisiones_no_reparte_bolsas():
    archivos = [("archivos", ("a.png", png((240, 240, 235)), "image/png"))]
    r = cliente.post(
        "/api/predict-lote", files=archivos, data={"tau": "0.999"}
    )
    assert r.status_code == 200
    datos = r.json()
    assert datos["abstenidos"] == 1
    assert all(v == 0 for v in datos["por_bolsa"].values())
