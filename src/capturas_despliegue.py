"""Capturas del despliegue para el informe (Playwright + Chromium).

No fotografía ventanas: abre las páginas públicas y guarda el PNG en
`docs/capturas/06-despliegue/`. Los logs de terminal salen de
`capturas_consola.py` a partir de los `.txt` de la misma carpeta.

Uso:

    .\\.venv\\Scripts\\python.exe src\\capturas_despliegue.py
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "capturas" / "06-despliegue"

SITIO = "https://residuos.open-laboratories.com"
ACCIONES = "https://github.com/ariel-david-collab/residuos-2184/actions"
RUN_DEPLOY = "https://github.com/ariel-david-collab/residuos-2184/actions/runs/44471900312"
PAQUETE = "https://github.com/ariel-david-collab/residuos-2184/pkgs/container/residuos-2184"

ESCRITORIO = {"width": 1440, "height": 900}
MOVIL = {"width": 390, "height": 844}


def captura(page: Page, nombre: str, completa: bool = True) -> None:
    destino = SALIDA / nombre
    page.screenshot(path=str(destino), full_page=completa, animations="disabled")
    print(f"  {destino.relative_to(RAIZ)}")


def abrir(page: Page, url: str, selector: str, timeout: int = 60_000) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    page.wait_for_selector(selector, timeout=timeout)
    page.wait_for_timeout(600)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        navegador = p.chromium.launch()

        # ── Sitio en producción: escritorio y móvil ──
        contexto = navegador.new_context(
            viewport=ESCRITORIO, device_scale_factor=2, locale="es-CO"
        )
        page = contexto.new_page()
        abrir(page, SITIO, ".zona")
        try:
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=10_000)
        except Exception:
            pass
        page.wait_for_timeout(400)
        captura(page, "01-sitio-escritorio.png")
        contexto.close()

        contexto = navegador.new_context(
            viewport=MOVIL, device_scale_factor=3, locale="es-CO", is_mobile=True
        )
        page = contexto.new_page()
        abrir(page, SITIO, ".zona")
        page.wait_for_timeout(400)
        captura(page, "02-sitio-movil.png")
        contexto.close()

        # ── GitHub Actions y GHCR (páginas públicas) ──
        contexto = navegador.new_context(
            viewport=ESCRITORIO, device_scale_factor=2, locale="es-CO"
        )
        page = contexto.new_page()
        abrir(page, ACCIONES, "main")
        captura(page, "03-actions.png")

        abrir(page, PAQUETE, "main")
        captura(page, "04-ghcr.png")

        # Run del deploy manual: imagen + despliegue, ambos en verde
        abrir(page, RUN_DEPLOY, "text=Despliegue en el VPS")
        captura(page, "05-run-deploy.png")
        contexto.close()

        navegador.close()


if __name__ == "__main__":
    main()
