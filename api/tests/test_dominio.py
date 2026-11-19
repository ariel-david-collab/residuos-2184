"""Reglas del dominio: materiales, bolsas de la Resolución 2184 y abstención.

Estas pruebas fijan el contrato antes de escribir implementación (TDD).
"""

import pytest

from dominio import BOLSAS, MATERIALES, decidir, proyectar_bolsas


def probs(**por_material: float) -> list[float]:
    """Construye el vector de 9 probabilidades en el orden canónico."""
    valores = [0.0] * len(MATERIALES)
    for nombre, p in por_material.items():
        idx = next(i for i, m in enumerate(MATERIALES) if m["clase"] == nombre)
        valores[idx] = p
    return valores


def test_catalogo_tiene_nueve_materiales_y_tres_bolsas():
    assert len(MATERIALES) == 9
    assert set(BOLSAS) == {"blanca", "verde", "negra"}
    assert {m["bolsa"] for m in MATERIALES} <= set(BOLSAS)


def test_proyeccion_agrupa_los_materiales_en_su_bolsa():
    bolsas = proyectar_bolsas(probs(Plastic=1.0))
    assert bolsas["blanca"] == pytest.approx(1.0)
    assert bolsas["verde"] == pytest.approx(0.0)
    assert bolsas["negra"] == pytest.approx(0.0)


def test_proyeccion_suma_los_materiales_de_la_misma_bolsa():
    bolsas = proyectar_bolsas(probs(Paper=0.3, Cardboard=0.2, Vegetation=0.5))
    assert bolsas["blanca"] == pytest.approx(0.5)
    assert bolsas["verde"] == pytest.approx(0.5)
    assert bolsas["negra"] == pytest.approx(0.0)


def test_proyeccion_conserva_la_masa_de_probabilidad():
    vector = [1 / 9] * len(MATERIALES)
    bolsas = proyectar_bolsas(vector)
    assert sum(bolsas.values()) == pytest.approx(1.0)


def test_basura_y_textil_van_a_la_bolsa_negra():
    assert proyectar_bolsas(probs(**{"Miscellaneous Trash": 0.7, "Textile Trash": 0.3}))[
        "negra"
    ] == pytest.approx(1.0)


def test_abstiene_cuando_ningun_material_alcanza_el_umbral():
    decision = decidir([1 / 9] * len(MATERIALES), tau=0.5)
    assert decision.abstenido is True
    assert decision.material is None
    assert decision.bolsa is not None


def test_decide_cuando_la_confianza_supera_el_umbral():
    decision = decidir(probs(Glass=0.8, Metal=0.1, Plastic=0.1), tau=0.5)
    assert decision.abstenido is False
    assert decision.material["clase"] == "Glass"
    assert decision.bolsa == "blanca"
    assert decision.confianza == pytest.approx(0.8)


def test_el_umbral_es_inclusivo():
    decision = decidir(probs(Plastic=0.5, Paper=0.5), tau=0.5)
    assert decision.confianza == pytest.approx(0.5)
    assert decision.abstenido is False


def test_la_bolsa_sugerida_es_la_de_mayor_masa_aunque_el_material_no_gane():
    vector = probs(Plastic=0.35, Vegetation=0.30, Paper=0.20, Glass=0.15)
    decision = decidir(vector, tau=0.5)
    assert decision.abstenido is True
    assert decision.bolsa == "blanca"


def test_top3_ordena_de_mayor_a_menor():
    decision = decidir(probs(Plastic=0.5, Glass=0.3, Paper=0.2), tau=0.4)
    assert [t["clase"] for t in decision.top3] == ["Plastic", "Glass", "Paper"]
    assert decision.top3[0]["p"] == pytest.approx(0.5)


def test_rechaza_vectores_con_longitud_incorrecta():
    with pytest.raises(ValueError):
        decidir([0.5, 0.5], tau=0.5)
