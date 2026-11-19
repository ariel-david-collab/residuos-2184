"""Genera la presentación de sustentación (17 diapositivas, 16:9).

Plantilla: azul #003057 y amarillo #F2A900 del manual de marca de la
Universidad de La Salle, tipografía Franklin Gothic para titulares y Segoe UI
para texto corrido.

Las notas del orador se extraen de los guiones en `docs/guiones/`, de modo que
la presentación y el discurso no se puedan desincronizar: si cambia un guion,
se vuelve a ejecutar este script y las notas se actualizan solas.

Uso:
    .venv\\Scripts\\python.exe docs/diapositivas/generar_diapositivas.py
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parents[2]
FIGS = Path(__file__).resolve().parent / "figs"
INFORME = RAIZ / "informe" / "figs"
GUIONES = RAIZ / "docs" / "guiones"
SALIDA = Path(__file__).resolve().parent / "residuos_2184_sustentacion.pptx"

# --- paleta institucional -------------------------------------------------
AZUL = "003057"
AMARILLO = "F2A900"
TINTA = "1A1A1A"
GRIS = "6B7A88"
GRIS_CLARO = "8A97A3"
PANEL = "EDF2F6"
LINEA = "D5DDE5"
BLANCO = "FFFFFF"
ROJO = "CB333B"
VERDE = "4A773C"
AZUL_SUAVE = "0A3D66"
AZUL_PALIDO = "C9D6E2"

DISPLAY = "Franklin Gothic Heavy"
BODY = "Segoe UI"
MONO = "Consolas"

ANCHO, ALTO = 13.333, 7.5
M = 0.78
DER = ANCHO - M
CONTENIDO = DER - M

TOTAL = 17


# --- utilidades -----------------------------------------------------------
def color(valor: str) -> RGBColor:
    return RGBColor.from_string(valor)


def rect(slide, x, y, w, h, fill=None, line=None, lw=1.0):
    forma = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    if fill:
        forma.fill.solid()
        forma.fill.fore_color.rgb = color(fill)
    else:
        forma.fill.background()
    if line:
        forma.line.color.rgb = color(line)
        forma.line.width = Pt(lw)
    else:
        forma.line.fill.background()
    forma.shadow.inherit = False
    return forma


def txt(
    slide,
    x,
    y,
    w,
    h,
    contenido,
    size=14,
    color_=TINTA,
    font=BODY,
    bold=False,
    italic=False,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    line=1.05,
    space=0,
    spacing=None,
    wrap=True,
):
    caja = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = caja.text_frame
    tf.word_wrap = wrap
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor

    if isinstance(contenido, str):
        parrafos = [[(contenido, {})]]
    elif contenido and isinstance(contenido[0], str):
        parrafos = [[(p, {})] for p in contenido]
    elif contenido and isinstance(contenido[0], tuple):
        parrafos = [contenido]
    else:
        parrafos = contenido

    for i, parrafo in enumerate(parrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line
        p.space_after = Pt(space)
        for texto, estilo in parrafo:
            run = p.add_run()
            run.text = texto
            f = run.font
            f.size = Pt(estilo.get("size", size))
            f.name = estilo.get("font", font)
            f.bold = estilo.get("bold", bold)
            f.italic = estilo.get("italic", italic)
            f.color.rgb = color(estilo.get("color", color_))
            esp = estilo.get("spacing", spacing)
            if esp:
                run._r.get_or_add_rPr().set("spc", str(int(esp * 100)))
    return caja


def bullets(slide, x, y, w, h, items, size=12, gap=7, color_=TINTA, marca=AMARILLO, line=1.12):
    parrafos = [
        [
            ("▸  ", {"color": marca, "bold": True, "size": size}),
            (item, {}),
        ]
        for item in items
    ]
    return txt(slide, x, y, w, h, parrafos, size=size, color_=color_, space=gap, line=line)


def medidas(ruta, w):
    ancho, alto = Image.open(ruta).size
    return w, w * alto / ancho


def imagen(slide, ruta, x, y, w):
    w, h = medidas(ruta, w)
    slide.shapes.add_picture(str(ruta), Inches(x), Inches(y), Inches(w), Inches(h))
    return w, h


def captura(slide, ruta, x, y, w):
    """Captura con marco negro y sombra dura: el lenguaje visual de la app."""
    w, h = medidas(ruta, w)
    rect(slide, x + 0.07, y + 0.07, w, h, fill=TINTA)
    slide.shapes.add_picture(str(ruta), Inches(x), Inches(y), Inches(w), Inches(h))
    rect(slide, x, y, w, h, fill=None, line=TINTA, lw=1.4)
    return w, h


def pie(slide, numero):
    rect(slide, M, 6.97, CONTENIDO, 0.01, fill=LINEA)
    txt(slide, M, 7.06, 8.0, 0.2, "Residuos 2184 · Universidad de La Salle", 8.5, GRIS_CLARO)
    txt(
        slide,
        DER - 1.4,
        7.06,
        1.4,
        0.2,
        f"{numero:02d} / {TOTAL}",
        8.5,
        GRIS_CLARO,
        align=PP_ALIGN.RIGHT,
    )


def cabecera(slide, kicker, titulo, size=28, regla_y=1.53):
    txt(slide, M, 0.40, 10.0, 0.24, kicker.upper(), 9.5, AZUL, bold=True, spacing=1.7)
    txt(slide, M, 0.65, CONTENIDO, 0.9, titulo, size, TINTA, font=DISPLAY, line=0.95)
    rect(slide, M, regla_y, 0.85, 0.055, fill=AMARILLO)


# --- notas del orador -----------------------------------------------------
def seccion(ruta: Path, prefijo: str) -> str:
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    inicio = None
    for i, linea in enumerate(lineas):
        if linea.startswith("### ") and linea[4:].strip().startswith(prefijo):
            inicio = i + 1
            break
    if inicio is None:
        raise ValueError(f"No encuentro el bloque {prefijo} en {ruta.name}")
    cuerpo = []
    for linea in lineas[inicio:]:
        if linea.startswith("### ") or linea.strip() == "---":
            break
        cuerpo.append(linea)
    return "\n".join(cuerpo).strip()


def limpiar(texto: str) -> str:
    texto = texto.replace("**", "")
    texto = re.sub(r"\*\[(.+?)\]\*", r"[\1]", texto, flags=re.S)
    return texto.strip()


def bloque(ruta: Path, prefijo: str, rango=None) -> str:
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", seccion(ruta, prefijo)) if p.strip()]
    if rango is not None:
        parrafos = parrafos[rango[0] : rango[1]]
    return "\n\n".join(limpiar(p) for p in parrafos)


def notas(slide, bloques):
    partes = []
    for etiqueta, ruta, prefijo, rango in bloques:
        cuerpo = prefijo if ruta is None else bloque(ruta, prefijo, rango)
        partes.append(f"== {etiqueta} ==\n{cuerpo}")
    slide.notes_slide.notes_text_frame.text = "\n\n".join(partes)


# --- diapositivas ---------------------------------------------------------
def portada(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, 0, 0, ANCHO, ALTO, fill=AZUL)
    rect(s, 0, 0, 0.30, ALTO, fill=AMARILLO)

    txt(
        s,
        1.05,
        1.02,
        10.0,
        0.26,
        "PROYECTO DE GRADO · MAESTRÍA EN INTELIGENCIA ARTIFICIAL",
        10.5,
        AMARILLO,
        bold=True,
        spacing=1.9,
    )
    txt(s, 1.05, 1.38, 9.8, 2.55, "¿A qué bolsa\nva esto?", 66, BLANCO, font=DISPLAY, line=0.88)
    rect(s, 1.05, 4.00, 1.45, 0.07, fill=AMARILLO)
    txt(
        s,
        1.05,
        4.26,
        7.9,
        1.1,
        "Clasificador normativo de residuos sólidos: de la predicción del material "
        "a la bolsa correcta, y a la abstención cuando la evidencia no alcanza.",
        15.5,
        AZUL_PALIDO,
        line=1.22,
    )
    txt(
        s,
        1.05,
        5.62,
        8.3,
        0.32,
        "Ariel David Herrera Ahumada · José Arquímedes Soto Montaña",
        14.5,
        BLANCO,
        bold=True,
    )
    txt(
        s,
        1.05,
        6.02,
        8.3,
        0.3,
        "Universidad de La Salle · Maestría en Inteligencia Artificial · Bogotá",
        11,
        "9FB3C6",
    )
    txt(s, 9.15, 5.65, 3.6, 1.5, "2184", 88, AZUL_SUAVE, font=DISPLAY, align=PP_ALIGN.RIGHT, wrap=False)

    notas(
        s,
        [
            ("INTEGRADO · 0:00–0:40 · Ariel", GUIONES / "guion_sustentacion_integrado_9m30s.md", "0:00", None),
            ("INDIVIDUAL ARIEL · 0:00–0:50", GUIONES / "guion_individual_ariel_9m.md", "0:00", None),
            ("INDIVIDUAL JOSÉ · 0:00–0:50", GUIONES / "guion_individual_jose_9m.md", "0:00", None),
        ],
    )
    return s


def problema(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "01 · El problema", "La norma es clara.\nLa decisión, no.", regla_y=1.72)

    txt(
        s,
        M,
        2.02,
        6.5,
        0.9,
        "Tres bolsas, nueve materiales y un objeto que no siempre encaja.",
        20,
        AZUL,
        line=1.15,
    )

    casos = [
        "Un vaso de papel con residuos de café",
        "Una bolsa de plástico que contuvo comida",
        "Un empaque multicapa",
    ]
    for i, caso in enumerate(casos):
        y = 2.95 + i * 0.72
        txt(s, M, y, 0.55, 0.35, f"0{i + 1}", 12, AMARILLO, bold=True, spacing=1.0)
        txt(s, M + 0.62, y - 0.02, 5.7, 0.55, caso, 15.5, TINTA, line=1.1)

    txt(
        s,
        M,
        5.45,
        6.4,
        0.8,
        "Por eso el sistema no solo clasifica: decide si la evidencia alcanza para decidir.",
        13.5,
        GRIS,
        line=1.2,
    )

    rect(s, 7.55, 1.85, 5.0, 3.35, fill=AMARILLO)
    txt(s, 7.95, 2.12, 4.2, 0.25, "EL COSTO DEL ERROR", 9.5, AZUL, bold=True, spacing=1.6)
    txt(
        s,
        7.95,
        2.55,
        4.2,
        1.9,
        "Un solo residuo contaminado puede invalidar la bolsa entera.",
        24,
        AZUL,
        font=DISPLAY,
        line=0.98,
    )
    txt(
        s,
        7.95,
        4.35,
        4.2,
        0.6,
        "Contaminar lo aprovechable cuesta más que perder un aprovechable.",
        11.5,
        AZUL,
        line=1.2,
    )

    notas(
        s,
        [
            ("INTEGRADO · 0:00–0:40 (continúa)", GUIONES / "guion_sustentacion_integrado_9m30s.md", "0:00", None),
            ("INDIVIDUAL ARIEL · 0:00–0:50", GUIONES / "guion_individual_ariel_9m.md", "0:00", None),
        ],
    )
    return s


def datos(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "02 · Datos", "De 4.752 imágenes a 4.217 únicas")

    cifras = [
        ("4.752", "imágenes originales de RealWaste"),
        ("535", "duplicados eliminados · 11,3 %"),
        ("4.217", "corpus final · 2.951 / 633 / 633"),
    ]
    for i, (numero, etiqueta) in enumerate(cifras):
        y = 1.80 + i * 1.18
        txt(s, M, y, 2.4, 0.62, numero, 36, AZUL, font=DISPLAY, line=0.95)
        txt(s, M, y + 0.62, 4.2, 0.3, etiqueta, 11.5, GRIS, line=1.1)

    rect(s, M, 5.42, 4.35, 0.85, fill=PANEL)
    rect(s, M, 5.42, 0.06, 0.85, fill=AZUL)
    txt(
        s,
        M + 0.22,
        5.55,
        3.95,
        0.6,
        "TrashNet · 2.527 imágenes, solo prueba externa. No entrena ni calibra.",
        10.5,
        TINTA,
        line=1.15,
    )

    imagen(s, FIGS / "datos_clases.png", 5.55, 1.80, 7.0)
    txt(
        s,
        5.55,
        6.12,
        7.0,
        0.3,
        "dHash de 64 bits · distancia de Hamming ≤ 6 · el manifiesto CSV es la fuente de verdad",
        9,
        GRIS_CLARO,
    )

    notas(
        s,
        [
            ("INTEGRADO · 0:40–1:50 (datos)", GUIONES / "guion_sustentacion_integrado_9m30s.md", "0:40", (0, 1)),
            ("INDIVIDUAL ARIEL · 0:50–2:20", GUIONES / "guion_individual_ariel_9m.md", "0:50", None),
        ],
    )
    return s


def proyeccion(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "03 · Dominio", "Nueve materiales, tres bolsas")

    bolsas = [
        ("BLANCA", "Aprovechables", ["Cartón", "Vidrio", "Metal", "Papel", "Plástico"], BLANCO, TINTA, LINEA),
        ("VERDE", "Orgánicos", ["Orgánicos", "Vegetación"], VERDE, BLANCO, VERDE),
        ("NEGRA", "No aprovechables", ["No aprovechable", "Textil"], TINTA, BLANCO, TINTA),
    ]
    for i, (nombre, tipo, materiales, fondo, texto, borde) in enumerate(bolsas):
        x = M + i * 3.95
        rect(s, x, 1.82, 0.62, 0.62, fill=fondo, line=borde, lw=1.2)
        txt(s, x + 0.78, 1.84, 2.8, 0.38, nombre, 21, TINTA, font=DISPLAY)
        txt(s, x + 0.78, 2.26, 2.8, 0.25, tipo, 10, GRIS)
        bullets(s, x, 2.90, 3.45, 2.2, materiales, size=13.5, gap=7, marca=AMARILLO)
        if i < 2:
            rect(s, x + 3.72, 1.82, 0.012, 3.3, fill=LINEA)

    rect(s, M, 5.45, CONTENIDO, 1.08, fill=PANEL)
    rect(s, M, 5.45, 0.06, 1.08, fill=AMARILLO)
    txt(
        s,
        M + 0.24,
        5.60,
        11.2,
        0.85,
        "El 63,6 % del corpus va a la bolsa blanca: la exactitud de bolsa se infla "
        "aunque el material esté mal. Por eso el umbral se calibra sobre material, no sobre bolsa.",
        13.5,
        TINTA,
        line=1.22,
    )

    notas(
        s,
        [
            ("INTEGRADO · 0:40–1:50 (proyección)", GUIONES / "guion_sustentacion_integrado_9m30s.md", "0:40", (1, 9)),
            ("INDIVIDUAL ARIEL · 2:20–3:20", GUIONES / "guion_individual_ariel_9m.md", "2:20", None),
        ],
    )
    return s


def modelos(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "04 · Método", "Dos caminos, la misma vara")

    tarjetas = [
        (
            M,
            "MODELO A · LÍNEA BASE",
            "Teachable Machine",
            [
                "180 imágenes por clase · 1.620 en total",
                "224 × 224 · 50 épocas",
                "Lote 16 · tasa de aprendizaje 0,001",
                "Sin código: el límite de la herramienta",
            ],
            "F2F4F6",
            TINTA,
            GRIS,
            GRIS,
        ),
        (
            6.95,
            "MODELO B · PROPUESTO",
            "MobileNetV3-Small",
            [
                "Todo train/ · 2.951 imágenes",
                "12 épocas · AdamW 3×10⁻⁴ · coseno",
                "Lote 32 · pesos por clase",
                "Aumento moderado · 2 últimos bloques",
            ],
            PANEL,
            AZUL,
            AZUL,
            AZUL,
        ),
    ]
    for x, kicker, titulo, items, fondo, color_titulo, color_kicker, borde in tarjetas:
        rect(s, x, 1.82, 5.55, 3.45, fill=fondo, line=borde, lw=1.2)
        txt(s, x + 0.35, 2.05, 4.9, 0.25, kicker, 9, color_kicker, bold=True, spacing=1.6)
        txt(s, x + 0.35, 2.38, 4.9, 0.5, titulo, 23, color_titulo, font=DISPLAY)
        bullets(s, x + 0.35, 3.10, 4.85, 2.0, items, size=12.5, gap=8, marca=AMARILLO)

    rect(s, M, 5.62, CONTENIDO, 0.95, fill=BLANCO)
    rect(s, M, 5.62, 0.06, 0.95, fill=AMARILLO)
    txt(
        s,
        M + 0.24,
        5.76,
        11.2,
        0.7,
        "Misma normalización en ambos: x/127,5 − 1. La comparación mide modelos, no preprocesados.",
        14,
        TINTA,
        line=1.15,
    )

    notas(
        s,
        [
            ("INTEGRADO · 1:50–2:50 · Ariel", GUIONES / "guion_sustentacion_integrado_9m30s.md", "1:50", None),
            ("INDIVIDUAL ARIEL · 3:20–5:00", GUIONES / "guion_individual_ariel_9m.md", "3:20", None),
        ],
    )
    return s


def umbral(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "05 · Calibración", "τ = 0,63: el punto donde el sistema prefiere callar", size=26)

    imagen(s, FIGS / "curva_umbral.png", M, 1.85, 7.0)

    stats = [
        ("77,6 %", "cobertura en val/"),
        ("90,0 %", "exactitud de material"),
        ("96,5 %", "exactitud de bolsa"),
    ]
    for i, (numero, etiqueta) in enumerate(stats):
        y = 1.90 + i * 1.05
        txt(s, 8.20, y, 2.0, 0.55, numero, 28, AZUL, font=DISPLAY, line=0.95)
        txt(s, 8.20, y + 0.52, 3.9, 0.3, etiqueta, 11, GRIS)

    txt(
        s,
        8.20,
        5.12,
        4.15,
        1.5,
        "Calibrado en val/ y congelado antes de tocar test/. Sobre bolsa habría elegido 0,30: "
        "la abstención sería decorativa.",
        11.5,
        TINTA,
        line=1.2,
    )

    notas(
        s,
        [
            ("INTEGRADO · 2:50–3:40 · Ariel", GUIONES / "guion_sustentacion_integrado_9m30s.md", "2:50", None),
            ("INDIVIDUAL ARIEL · 5:00–6:20", GUIONES / "guion_individual_ariel_9m.md", "5:00", None),
        ],
    )
    return s


def resultados(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "06 · Resultados", "El Modelo B gana en todo")

    txt(s, M, 1.68, 8.0, 0.25, "633 imágenes de test/ · una sola evaluación", 10, GRIS)

    columnas = [2.85, 1.85, 1.75, 1.75, 1.65, 1.92]
    encabezados = ["", "Material", "Bolsa", "F1 macro", "AUC macro", "Log-loss"]
    x0, y0 = M, 2.08
    x = x0
    for j, (ancho, texto) in enumerate(zip(columnas, encabezados)):
        if j == 0:
            txt(s, x + 0.18, y0, ancho - 0.2, 0.3, texto.upper(), 8.5, GRIS, bold=True, spacing=1.2)
        else:
            txt(
                s,
                x,
                y0,
                ancho - 0.12,
                0.3,
                texto.upper(),
                8.5,
                GRIS,
                bold=True,
                spacing=1.2,
                align=PP_ALIGN.RIGHT,
            )
        x += ancho
    rect(s, x0, y0 + 0.38, CONTENIDO, 0.012, fill=LINEA)

    filas = [
        ("A · Teachable Machine", "78,2 %", "91,9 %", "0,777", "0,971", "0,976", False),
        ("B · MobileNetV3-Small", "83,6 %", "94,9 %", "0,841", "0,987", "0,450", True),
    ]
    for i, (modelo, mat, bol, f1, auc, ll, destacada) in enumerate(filas):
        y = y0 + 0.42 + i * 0.78
        if destacada:
            rect(s, x0, y, CONTENIDO, 0.78, fill=PANEL)
            rect(s, x0, y, 0.06, 0.78, fill=AZUL)
        x = x0
        valores = [modelo, mat, bol, f1, auc, ll]
        for j, (ancho, valor) in enumerate(zip(columnas, valores)):
            if j == 0:
                txt(s, x + 0.18, y, ancho - 0.2, 0.78, valor, 12.5, TINTA, bold=True, anchor=MSO_ANCHOR.MIDDLE)
            else:
                txt(
                    s,
                    x,
                    y,
                    ancho - 0.12,
                    0.78,
                    valor,
                    19,
                    AZUL if destacada else TINTA,
                    font=DISPLAY,
                    align=PP_ALIGN.RIGHT,
                    anchor=MSO_ANCHOR.MIDDLE,
                )
            x += ancho

    txt(s, M, 4.55, 6.0, 0.25, "LA DIFERENCIA DECISIVA ES EL LOG-LOSS", 9, GRIS, bold=True, spacing=1.5)
    txt(s, M, 4.82, 2.2, 0.75, "0,450", 38, AZUL, font=DISPLAY, line=0.9)
    txt(s, M + 1.95, 5.12, 1.2, 0.35, "vs 0,976", 16, GRIS, font=DISPLAY)
    txt(
        s,
        5.30,
        4.88,
        7.2,
        0.95,
        "Un modelo sobreconfiado no puede callar de forma selectiva. El B no solo acierta más: "
        "sus probabilidades sirven para decidir cuándo abstenerse.",
        12.5,
        TINTA,
        line=1.2,
    )
    txt(
        s,
        M,
        6.25,
        11.6,
        0.3,
        "+5,4 material · +3,0 bolsa · +0,064 F1 macro · +0,017 AUC",
        10.5,
        AZUL,
        bold=True,
    )

    notas(
        s,
        [
            ("INTEGRADO · 3:40–4:45 · Ariel", GUIONES / "guion_sustentacion_integrado_9m30s.md", "3:40", None),
            ("INDIVIDUAL ARIEL · 6:20–8:20 (comparación global)", GUIONES / "guion_individual_ariel_9m.md", "6:20", (0, 1)),
        ],
    )
    return s


def por_clase(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "06 · Resultados", "Acierta cuando decide; falla al reconocer")

    imagen(s, FIGS / "f1_clases.png", M, 1.85, 5.5)

    txt(s, 6.70, 1.90, 2.2, 0.3, "MEJOR CLASE", 8.5, GRIS, bold=True, spacing=1.4)
    txt(s, 6.70, 2.18, 2.4, 0.55, "0,968", 28, AZUL, font=DISPLAY)
    txt(s, 6.70, 2.72, 2.6, 0.3, "Vegetación", 11, GRIS)

    txt(s, 9.55, 1.90, 2.6, 0.3, "PEOR CLASE", 8.5, GRIS, bold=True, spacing=1.4)
    txt(s, 9.55, 2.18, 2.4, 0.55, "0,746", 28, TINTA, font=DISPLAY)
    txt(s, 9.55, 2.72, 2.9, 0.3, "No aprovechable", 11, GRIS)

    rect(s, 6.70, 3.30, 5.55, 2.25, fill=PANEL)
    rect(s, 6.70, 3.30, 0.06, 2.25, fill=AMARILLO)
    txt(s, 7.00, 3.48, 5.0, 0.3, "PLÁSTICO", 9, GRIS, bold=True, spacing=1.5)
    txt(
        s,
        7.00,
        3.76,
        4.95,
        0.45,
        [("Precisión 0,881", {"bold": True}), ("   ·   recall 0,712", {})],
        14,
        TINTA,
    )
    txt(
        s,
        7.00,
        4.32,
        4.95,
        1.0,
        "18 de sus 125 imágenes se predicen como metal. Cuando el modelo declara plástico "
        "acierta; lo que falla es reconocerlo en todas sus formas.",
        11.5,
        TINTA,
        line=1.22,
    )

    txt(
        s,
        6.70,
        5.85,
        5.55,
        0.8,
        "El AUC mide separación entre clases; el recall, la decisión con un umbral implícito de 0,5.",
        10.5,
        GRIS,
        line=1.2,
    )

    notas(
        s,
        [
            ("INDIVIDUAL ARIEL · 6:20–8:20 (por clase)", GUIONES / "guion_individual_ariel_9m.md", "6:20", (1, 2)),
        ],
    )
    return s


def bolsas(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "06 · Resultados", "La bolsa negra es el punto débil")

    imagen(s, FIGS / "matriz_bolsas.png", M, 1.95, 5.0)

    txt(s, 6.30, 1.90, 5.9, 0.25, "F1 POR BOLSA", 8.5, GRIS, bold=True, spacing=1.4)
    valores = [("0,968", "Blanca", AZUL), ("0,952", "Verde", AZUL), ("0,873", "Negra", ROJO)]
    for i, (valor, etiqueta, tono) in enumerate(valores):
        x = 6.30 + i * 2.05
        txt(s, x, 2.18, 1.9, 0.5, valor, 24, tono, font=DISPLAY)
        txt(s, x, 2.68, 1.9, 0.25, etiqueta, 10, GRIS)

    rect(s, 6.30, 3.20, 6.0, 1.45, fill=PANEL)
    rect(s, 6.30, 3.20, 0.06, 1.45, fill=ROJO)
    txt(
        s,
        6.58,
        3.38,
        5.55,
        1.1,
        "18 de los 107 residuos de la negra se escapan a blanca o verde (16,8 %). "
        "Es el error que contamina el flujo aprovechable.",
        11.5,
        TINTA,
        line=1.22,
    )

    txt(
        s,
        6.30,
        4.95,
        6.0,
        1.2,
        [
            [("Con τ = 0,63 ", {"bold": True, "color": AZUL}), ("el B decide en el 80,9 % de los casos y acierta ", {})],
            [("91,8 % de material y 98,2 % de bolsa.", {"bold": True})],
        ],
        12,
        TINTA,
        line=1.25,
        space=4,
    )

    notas(
        s,
        [
            (
                "INDIVIDUAL ARIEL · 6:20–8:20 (bolsa y costo del error)",
                GUIONES / "guion_individual_ariel_9m.md",
                "6:20",
                (2, 6),
            ),
        ],
    )
    return s


def relevo(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, 0, 0, ANCHO, ALTO, fill=AZUL)
    rect(s, 0, 0, 0.30, ALTO, fill=AMARILLO)

    txt(s, 1.05, 1.55, 6.0, 0.3, "PARTE 2 · 04:45", 11, AMARILLO, bold=True, spacing=2.0)
    txt(s, 1.05, 1.95, 8.4, 1.6, "De la métrica\na la persona", 46, BLANCO, font=DISPLAY, line=0.92)
    txt(
        s,
        1.05,
        4.05,
        7.6,
        0.5,
        "Arquitectura · Interfaz · Pruebas · Despliegue",
        14,
        AZUL_PALIDO,
    )
    txt(s, 9.05, 5.55, 3.9, 1.5, "04:45", 76, AZUL_SUAVE, font=DISPLAY, align=PP_ALIGN.RIGHT, wrap=False)

    notas(
        s,
        [
            (
                "RELEVO · José toma la palabra",
                None,
                "Ariel cede la palabra sin pausa larga. José retoma con «Gracias, Ariel» y "
                "arranca el bloque de arquitectura (4:45 del guion integrado).",
                None,
            ),
            (
                "INDIVIDUAL JOSÉ · apertura",
                GUIONES / "guion_individual_jose_9m.md",
                "0:00",
                None,
            ),
        ],
    )
    return s


def arquitectura(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "07 · Sistema", "Cuatro capas y una regla: el dominio no depende de nada", size=26)

    capas = [
        ("01", "DOMINIO", "Materiales, bolsas y decidir(probs, τ)", "Python puro: sin FastAPI ni ONNX", True),
        ("02", "INFERENCIA", "Carga el ONNX, preprocesa y devuelve probabilidades", "", False),
        ("03", "HTTP", "Expone el contrato y sirve los estáticos", "", False),
        ("04", "INTERFAZ", "Rust + Leptos compilado a WebAssembly", "", False),
    ]
    for i, (numero, nombre, desc, extra, destacada) in enumerate(capas):
        y = 1.82 + i * 1.06
        rect(s, M, y, 6.55, 0.94, fill=AZUL if destacada else PANEL)
        txt(s, M + 0.22, y + 0.18, 0.5, 0.25, numero, 9, AMARILLO, bold=True, spacing=1.2)
        txt(s, M + 0.78, y + 0.13, 5.5, 0.28, nombre, 13, BLANCO if destacada else AZUL, bold=True, spacing=1.2)
        txt(s, M + 0.78, y + 0.43, 5.55, 0.45, desc, 10.5, BLANCO if destacada else TINTA, line=1.1)
        if extra:
            txt(s, M + 0.78, y + 0.68, 5.55, 0.22, extra, 9, AMARILLO)

    rect(s, 7.75, 1.82, 4.8, 3.95, fill=BLANCO, line=LINEA, lw=1.2)
    txt(s, 8.00, 2.02, 4.3, 0.25, "CUATRO RUTAS", 9, GRIS, bold=True, spacing=1.6)
    rutas = [
        ("/api/health", "modelo activo y clases"),
        ("/api/catalogo", "materiales, τ y métricas"),
        ("/api/predict", "una imagen"),
        ("/api/predict-lote", "varias imágenes"),
    ]
    for i, (ruta, desc) in enumerate(rutas):
        y = 2.38 + i * 0.78
        txt(s, 8.00, y, 4.3, 0.3, ruta, 12, AZUL, font=MONO, bold=True)
        txt(s, 8.00, y + 0.27, 4.3, 0.25, desc, 9.5, GRIS)

    txt(
        s,
        7.75,
        5.95,
        4.8,
        0.8,
        "Un solo contenedor: WASM + Python. Sin CORS, sin un segundo servicio.",
        11,
        GRIS,
        line=1.2,
    )

    notas(
        s,
        [
            ("INTEGRADO · 4:45–5:20 · José", GUIONES / "guion_sustentacion_integrado_9m30s.md", "4:45", None),
            ("INDIVIDUAL JOSÉ · 0:50–2:20", GUIONES / "guion_individual_jose_9m.md", "0:50", None),
        ],
    )
    return s


def interfaz(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "08 · Interfaz", "El veredicto se lee en color y en palabra")

    captura(s, INFORME / "ui_veredicto.png", M, 1.82, 7.85)

    puntos = [
        "Color y nombre de la bolsa: el color nunca es la única señal.",
        "Umbral visible sin scroll y explicado en lenguaje llano.",
        "Al pie, la exactitud real del modelo que está decidiendo.",
    ]
    bullets(s, 8.95, 1.95, 3.6, 2.2, puntos, size=12, gap=12, line=1.18)

    txt(
        s,
        8.95,
        4.35,
        3.55,
        1.1,
        "El control de exigencia va de 0,30 a 0,90 y arranca en el τ que publica el catálogo.",
        10.5,
        GRIS,
        line=1.2,
    )

    txt(
        s,
        M,
        5.72,
        7.85,
        0.3,
        "Captura real de la aplicación en producción · residuos.open-laboratories.com",
        8.5,
        GRIS_CLARO,
    )

    notas(
        s,
        [
            ("INTEGRADO · 5:20–6:40 (interfaz y demo)", GUIONES / "guion_sustentacion_integrado_9m30s.md", "5:20", (0, 2)),
            ("INDIVIDUAL JOSÉ · 2:20–4:10", GUIONES / "guion_individual_jose_9m.md", "2:20", None),
        ],
    )
    return s


def abstencion(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "08 · Interfaz", "«El modelo duda»")

    captura(s, INFORME / "ui_abstencion.png", M, 1.85, 7.25)

    txt(s, 8.45, 1.90, 4.1, 0.4, "CUANDO NINGUNA CLASE SUPERA τ", 8.5, GRIS, bold=True, spacing=1.3)
    txt(
        s,
        8.45,
        2.22,
        4.05,
        1.5,
        "Ninguna clase supera el umbral. Revisa si el residuo está limpio y seco, "
        "o consulta la guía de tu punto ecológico antes de elegir la bolsa.",
        12,
        TINTA,
        line=1.22,
    )
    rect(s, 8.45, 3.80, 4.05, 1.25, fill=PANEL)
    rect(s, 8.45, 3.80, 0.06, 1.25, fill=AMARILLO)
    txt(
        s,
        8.72,
        3.96,
        3.7,
        1.0,
        "La bolsa de mayor masa sigue apareciendo, pero como sugerencia a revisar, no como veredicto.",
        11,
        TINTA,
        line=1.2,
    )
    txt(
        s,
        8.45,
        5.30,
        4.05,
        0.8,
        "Un modelo que siempre dice 0,99 no puede callar de forma selectiva.",
        10.5,
        GRIS,
        line=1.2,
    )

    txt(
        s,
        M,
        5.98,
        7.25,
        0.3,
        "τ elevado a 0,90 para forzar la abstención en la demostración",
        8.5,
        GRIS_CLARO,
    )

    notas(
        s,
        [
            ("INTEGRADO · 5:20–6:40 (abstención)", GUIONES / "guion_sustentacion_integrado_9m30s.md", "5:20", (2, 9)),
            ("INDIVIDUAL JOSÉ · 4:10–5:10", GUIONES / "guion_individual_jose_9m.md", "4:10", None),
        ],
    )
    return s


def pruebas(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "09 · Calidad", "35 pruebas, cuatro suites, un manifiesto")

    suites = [
        ("01", "DATOS", "dHash, deduplicación, estratificación y reproducibilidad de la partición."),
        ("02", "DOMINIO", "Proyección a bolsas, masa de probabilidad, abstención, borde τ y top-3."),
        ("03", "IMAGEN", "Forma NHWC, rango [−1, 1], orden RGB y escala de grises."),
        ("04", "INFERENCIA", "Doble softmax, contrato, lotes y archivos inválidos."),
    ]
    for i, (numero, nombre, desc) in enumerate(suites):
        x = M + (i % 2) * 5.95
        y = 1.85 + (i // 2) * 1.62
        rect(s, x, y, 5.6, 1.45, fill=PANEL)
        txt(s, x + 0.22, y + 0.18, 0.45, 0.25, numero, 9, AMARILLO, bold=True, spacing=1.2)
        txt(s, x + 0.78, y + 0.16, 4.6, 0.25, nombre, 11, AZUL, bold=True, spacing=1.3)
        txt(s, x + 0.78, y + 0.48, 4.55, 0.85, desc, 10.5, TINTA, line=1.18)

    txt(s, M, 5.35, 1.9, 0.75, "35", 42, AZUL, font=DISPLAY, line=0.9)
    txt(s, M + 1.45, 5.48, 4.5, 0.6, "pruebas en menos de un segundo", 13, TINTA)
    txt(
        s,
        6.55,
        5.45,
        6.0,
        0.9,
        "7 scripts y un manifiesto · partición determinista · s06_evaluar.py regenera cada cifra del informe.",
        11,
        GRIS,
        line=1.2,
    )

    notas(
        s,
        [
            ("INTEGRADO · 6:40–7:20 · José", GUIONES / "guion_sustentacion_integrado_9m30s.md", "6:40", None),
            ("INDIVIDUAL JOSÉ · 5:10–6:10", GUIONES / "guion_individual_jose_9m.md", "5:10", None),
        ],
    )
    return s


def despliegue(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "10 · Operación", "Un contenedor, ningún puerto público")

    bullets(
        s,
        M,
        1.85,
        6.3,
        2.3,
        [
            "WASM + Python en una sola imagen de 471 MB.",
            "Usuario sin privilegios y HEALTHCHECK contra /api/health.",
            "CI: pruebas, gitleaks, GHCR y despliegue con tag explícito.",
            "Inferencia en CPU: 5–12 ms por imagen, preprocesado incluido.",
        ],
        size=11.5,
        gap=10,
        line=1.18,
    )

    captura(s, FIGS / "ci_cadena.png", M, 4.42, 6.3)
    txt(
        s,
        M,
        4.18,
        6.3,
        0.25,
        "RUN REAL · 1 min 9 s DE PUNTA A PUNTA",
        8.5,
        GRIS,
        bold=True,
        spacing=1.3,
    )

    rect(s, 7.55, 1.85, 5.0, 4.2, fill=PANEL)
    txt(s, 7.85, 2.05, 4.4, 0.25, "SUPERFICIE DE ATAQUE", 9, GRIS, bold=True, spacing=1.5)
    bullets(
        s,
        7.85,
        2.42,
        4.4,
        2.8,
        [
            "Traefik y red web: ningún puerto publicado.",
            "TLS con Let’s Encrypt; HTTP → HTTPS 301.",
            "ForceCommand con allowlist de tags: una llave no da shell.",
            "Secretos materializados desde OpenBao.",
            "gitleaks en cada push.",
            "SSH público cerrado; el CI entra por Tailscale.",
        ],
        size=11,
        gap=10,
        line=1.15,
    )
    rect(s, 7.85, 5.28, 4.4, 0.01, fill="C9D6E2")
    txt(
        s,
        7.85,
        5.42,
        4.4,
        0.5,
        "El tag vX.Y.Z dispara el despliegue; main solo publica la imagen.",
        9.5,
        GRIS,
        line=1.18,
    )

    notas(
        s,
        [
            ("INTEGRADO · 7:20–8:30 · José", GUIONES / "guion_sustentacion_integrado_9m30s.md", "7:20", None),
            ("INDIVIDUAL JOSÉ · 6:10–8:00", GUIONES / "guion_individual_jose_9m.md", "6:10", None),
        ],
    )
    return s


def dominio(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecera(s, "11 · Límites", "Cuando el dominio cambia, la métrica se cae")

    imagen(s, FIGS / "dominio.png", M, 1.85, 6.25)

    txt(s, 7.30, 1.90, 5.2, 0.25, "TRASHNET · PRUEBA EXTERNA", 8.5, GRIS, bold=True, spacing=1.4)
    txt(s, 7.30, 2.18, 2.4, 0.6, "42,4 %", 30, AZUL, font=DISPLAY)
    txt(s, 7.30, 2.72, 4.9, 0.3, "exactitud de material", 10.5, GRIS)

    txt(s, 7.30, 3.15, 2.4, 0.5, "92,9 %", 24, TINTA, font=DISPLAY)
    txt(s, 7.30, 3.60, 5.0, 0.5, "de bolsa, pero 2.390 de 2.527 imágenes van a la blanca", 10.5, GRIS, line=1.15)

    txt(s, 7.30, 4.18, 2.4, 0.45, "0,349", 24, ROJO, font=DISPLAY)
    txt(s, 7.30, 4.60, 5.0, 0.5, "F1 macro de bolsa · recall de la negra 0,058", 10.5, GRIS, line=1.15)

    rect(s, M, 5.55, CONTENIDO, 1.0, fill=PANEL)
    rect(s, M, 5.55, 0.06, 1.0, fill=AMARILLO)
    txt(
        s,
        M + 0.24,
        5.70,
        11.2,
        0.8,
        "Con abstención, el B acepta el 57,7 % y sube al 49,0 % de material. "
        "El umbral filtra ruido; no repara el cambio de dominio.",
        13,
        TINTA,
        line=1.2,
    )

    notas(
        s,
        [
            ("INTEGRADO · 8:30–9:30 (dominio)", GUIONES / "guion_sustentacion_integrado_9m30s.md", "8:30", (0, 1)),
            ("INDIVIDUAL JOSÉ · 8:00–9:00", GUIONES / "guion_individual_jose_9m.md", "8:00", None),
        ],
    )
    return s


def cierre(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, 0, 0, ANCHO, ALTO, fill=AZUL)
    rect(s, 0, 0, 0.30, ALTO, fill=AMARILLO)

    txt(s, 1.05, 1.00, 6.0, 0.28, "12 · CIERRE", 10, AMARILLO, bold=True, spacing=1.8)
    txt(s, 1.05, 1.35, 10.8, 1.1, "Un sistema que sabe decir «no sé»", 40, BLANCO, font=DISPLAY, line=0.95)

    ideas = [
        ("01", "Separar la predicción del material de la regla normativa."),
        ("02", "Calibrar el umbral sobre validación y congelarlo antes de evaluar."),
        ("03", "Medir el límite y ponerlo en la interfaz, no esconderlo."),
    ]
    for i, (numero, idea) in enumerate(ideas):
        y = 3.05 + i * 0.72
        txt(s, 1.05, y + 0.03, 0.5, 0.25, numero, 9, AMARILLO, bold=True, spacing=1.2)
        txt(s, 1.70, y, 10.4, 0.45, idea, 15.5, BLANCO, line=1.1)

    txt(s, 1.05, 5.55, 3.0, 0.8, "Gracias.", 36, AMARILLO, font=DISPLAY)
    txt(
        s,
        1.05,
        6.55,
        9.0,
        0.3,
        "residuos.open-laboratories.com · Universidad de La Salle",
        10.5,
        "9FB3C6",
    )

    notas(
        s,
        [
            ("INTEGRADO · 8:30–9:30 (cierre)", GUIONES / "guion_sustentacion_integrado_9m30s.md", "8:30", (1, 9)),
            ("INDIVIDUAL JOSÉ · 9:00–9:30", GUIONES / "guion_individual_jose_9m.md", "9:00", None),
            ("INDIVIDUAL ARIEL · 8:20–9:20", GUIONES / "guion_individual_ariel_9m.md", "8:20", None),
        ],
    )
    return s


def main():
    prs = Presentation()
    prs.slide_width = Inches(ANCHO)
    prs.slide_height = Inches(ALTO)

    portada(prs)
    problema(prs)
    datos(prs)
    proyeccion(prs)
    modelos(prs)
    umbral(prs)
    resultados(prs)
    por_clase(prs)
    bolsas(prs)
    relevo(prs)
    arquitectura(prs)
    interfaz(prs)
    abstencion(prs)
    pruebas(prs)
    despliegue(prs)
    dominio(prs)
    cierre(prs)

    for i, slide in enumerate(prs.slides, start=1):
        if i not in (1, 10, 17):
            pie(slide, i)

    prs.save(SALIDA)
    print(f"Guardado: {SALIDA.name} · {len(prs.slides)} diapositivas")


if __name__ == "__main__":
    main()
