"""Reglas del dominio del proyecto.

Traduce la salida del clasificador de materiales (9 clases de RealWaste) a la
decisión que realmente le importa al ciudadano: en qué bolsa del código de
colores de la Resolución 2184 de 2019 va el residuo, o si conviene abstenerse.

La proyección material -> bolsa es una regla normativa, no algo que el modelo
aprenda: por eso vive aquí y no en el modelo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

# Orden canónico = orden alfabético de las carpetas de RealWaste (ids 0..8).
MATERIALES: list[dict] = [
    {"id": 0, "clase": "Cardboard", "material": "Cartón", "bolsa": "blanca"},
    {"id": 1, "clase": "Food Organics", "material": "Orgánicos", "bolsa": "verde"},
    {"id": 2, "clase": "Glass", "material": "Vidrio", "bolsa": "blanca"},
    {"id": 3, "clase": "Metal", "material": "Metal", "bolsa": "blanca"},
    {"id": 4, "clase": "Miscellaneous Trash", "material": "No aprovechable", "bolsa": "negra"},
    {"id": 5, "clase": "Paper", "material": "Papel", "bolsa": "blanca"},
    {"id": 6, "clase": "Plastic", "material": "Plástico", "bolsa": "blanca"},
    {"id": 7, "clase": "Textile Trash", "material": "Textil", "bolsa": "negra"},
    {"id": 8, "clase": "Vegetation", "material": "Vegetación", "bolsa": "verde"},
]

BOLSAS: dict[str, dict] = {
    "blanca": {
        "nombre": "Blanca",
        "rotulo": "Aprovechables",
        "detalle": "Plástico, vidrio, metal, papel y cartón limpios.",
        "color": "#EDEDF0",
        "borde": "#D4D4D8",
        "texto": "#18181B",
    },
    "verde": {
        "nombre": "Verde",
        "rotulo": "Orgánicos",
        "detalle": "Restos de comida y residuos de poda o jardinería.",
        "color": "#16A34A",
        "borde": "#15803D",
        "texto": "#FFFFFF",
    },
    "negra": {
        "nombre": "Negra",
        "rotulo": "No aprovechables",
        "detalle": "Residuos mezclados, contaminados o de un solo uso sucio.",
        "color": "#18181B",
        "borde": "#000000",
        "texto": "#FAFAFA",
    },
}


@dataclass(frozen=True)
class Decision:
    """Resultado listo para la interfaz."""

    material: dict | None
    bolsa: str
    confianza: float
    abstenido: bool
    top3: list[dict]
    bolsas_prob: dict[str, float]


def _validar(probs: Sequence[float]) -> list[float]:
    if len(probs) != len(MATERIALES):
        raise ValueError(
            f"se esperaban {len(MATERIALES)} probabilidades, llegaron {len(probs)}"
        )
    return [float(p) for p in probs]


def proyectar_bolsas(probs: Sequence[float]) -> dict[str, float]:
    """Suma la masa de probabilidad de cada material en su bolsa normativa."""
    valores = _validar(probs)
    bolsas = {nombre: 0.0 for nombre in BOLSAS}
    for material, p in zip(MATERIALES, valores):
        bolsas[material["bolsa"]] += p
    return bolsas


def decidir(probs: Sequence[float], tau: float) -> Decision:
    """Decide material, bolsa y abstención.

    Si la mejor probabilidad no alcanza `tau`, se abstiene: un residuo mal
    clasificado contamina la bolsa completa, así que no adivinar es lo correcto.
    """
    valores = _validar(probs)
    orden = sorted(range(len(valores)), key=lambda i: valores[i], reverse=True)
    ganador = orden[0]
    confianza = valores[ganador]
    bolsas = proyectar_bolsas(valores)
    bolsa = max(bolsas, key=bolsas.get)
    abstenido = confianza < tau
    top3 = [
        {
            "clase": MATERIALES[i]["clase"],
            "material": MATERIALES[i]["material"],
            "p": valores[i],
        }
        for i in orden[:3]
    ]
    return Decision(
        material=None if abstenido else MATERIALES[ganador],
        bolsa=bolsa,
        confianza=confianza,
        abstenido=abstenido,
        top3=top3,
        bolsas_prob=bolsas,
    )
