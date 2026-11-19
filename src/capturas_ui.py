"""Capturas de la interfaz para el informe (Playwright + Chromium).

Requiere la aplicación servida (por defecto en http://127.0.0.1:8077) y el
Chromium de Playwright instalado. Genera PNG en `docs/capturas/02-app/`:

    01-escritorio-inicio.png      1440x900, vista completa
    02-escritorio-veredicto.png   tras subir una foto
    03-escritorio-lote.png        con nueve fotos procesadas
    04-escritorio-abstencion.png  umbral en 0.90, sin decidir
    05-detalle-umbral.png         recorte del ajuste de exigencia
    06-detalle-veredicto.png      recorte del veredicto y sus barras
    07-movil-inicio.png           390x844, vista completa
    08-movil-veredicto.png

Al terminar el modelo real, se regeneran apuntando al servidor definitivo:

    .\\\\.venv\\\\Scripts\\\\python.exe src\\\\capturas_ui.py --base http://127.0.0.1:8077
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "capturas" / "02-app"
REALWASTE = RAIZ / "datos" / "realwaste" / "realwaste-main" / "RealWaste"

ESCRITORIO = {"width": 1440, "height": 900}
MOVIL = {"width": 390, "height": 844}


def foto(clase: str, indice: int = 0) -> Path:
    """Una imagen real de la clase indicada (RealWaste)."""
    carpeta = REALWASTE / clase
    archivos = sorted(
        p for p in carpeta.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not archivos:
        raise RuntimeError(f"sin imágenes en {carpeta}")
    return archivos[indice % len(archivos)]


def abrir(page: Page, base: str) -> None:
    page.goto(base, wait_until="load")
    page.wait_for_selector(".zona", timeout=30_000)
    try:
        page.wait_for_function("document.fonts.status === 'loaded'", timeout=10_000)
    except Exception:
        pass  # una fuente remota lenta no debe tumbar la captura
    page.wait_for_timeout(350)


def captura(page: Page, nombre: str, completa: bool = True) -> None:
    destino = SALIDA / nombre
    page.screenshot(path=str(destino), full_page=completa, animations="disabled")
    print(f"  {destino.relative_to(RAIZ)}")


def recorte(page: Page, selector: str, nombre: str, margen: int = 18) -> None:
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(120)
    caja = page.locator(selector).bounding_box()
    if caja is None:
        raise RuntimeError(f"sin caja para {selector}")
    destino = SALIDA / nombre
    page.screenshot(
        path=str(destino),
        full_page=True,
        animations="disabled",
        clip={
            "x": max(0, caja["x"] - margen),
            "y": max(0, caja["y"] - margen),
            "width": caja["width"] + margen * 2,
            "height": caja["height"] + margen * 2,
        },
    )
    print(f"  {destino.relative_to(RAIZ)}")


def subir_una(page: Page, ruta: Path) -> None:
    page.set_input_files("input[type=file] >> nth=0", str(ruta))
    page.wait_for_selector(".veredicto", timeout=30_000)
    page.wait_for_timeout(900)  # barras: retardo escalonado + animación


def fijar_tau(page: Page, valor: str) -> None:
    page.locator("input.rango").evaluate(
        """(el, v) => {
            el.value = v;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        valor,
    )


def escritorio(navegador, base: str) -> None:
    contexto = navegador.new_context(
        viewport=ESCRITORIO, device_scale_factor=2, locale="es-CO"
    )
    page = contexto.new_page()

    abrir(page, base)
    captura(page, "01-escritorio-inicio.png")

    subir_una(page, foto("Plastic", 2))
    captura(page, "02-escritorio-veredicto.png")

    subir_lote = [
        foto("Cardboard", 1),
        foto("Food Organics", 2),
        foto("Glass", 3),
        foto("Metal", 1),
        foto("Miscellaneous Trash", 2),
        foto("Paper", 3),
        foto("Plastic", 4),
        foto("Textile Trash", 1),
        foto("Vegetation", 2),
    ]
    page.set_input_files(
        ".lote input[type=file]", [str(p) for p in subir_lote]
    )
    page.wait_for_selector(".chips", timeout=60_000)
    page.wait_for_timeout(500)
    captura(page, "03-escritorio-lote.png")

    recorte(page, ".ajuste", "05-detalle-umbral.png")
    recorte(page, ".resultado", "06-detalle-veredicto.png")

    # Abstención: papel arrugado que el Modelo B resuelve con 0.33 de confianza,
    # así el umbral máximo del control (0.90) lo deja sin decisión. Se recarga la
    # página para que el lote anterior no acompañe la captura.
    abrir(page, base)
    fijar_tau(page, "0.90")
    subir_una(page, foto("Paper", 7))
    page.wait_for_selector(".abstencion", timeout=30_000)
    page.wait_for_timeout(500)
    captura(page, "04-escritorio-abstencion.png")

    contexto.close()


def movil(navegador, base: str) -> None:
    contexto = navegador.new_context(
        viewport=MOVIL, device_scale_factor=3, locale="es-CO", is_mobile=True
    )
    page = contexto.new_page()

    abrir(page, base)
    captura(page, "07-movil-inicio.png")

    subir_una(page, foto("Paper", 3))
    captura(page, "08-movil-veredicto.png")

    contexto.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capturas de la interfaz para el informe")
    parser.add_argument("--base", default="http://127.0.0.1:8077")
    arguments = parser.parse_args()

    SALIDA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(args=["--hide-scrollbars"])
        print("Escritorio 1440x900")
        escritorio(navegador, arguments.base)
        print("Móvil 390x844")
        movil(navegador, arguments.base)
        navegador.close()
    print(f"Listo: {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
