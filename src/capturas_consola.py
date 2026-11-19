"""Capturas de consola: cada log `.txt` se dibuja como una terminal y se guarda en PNG.

El texto se toma literal del archivo (misma salida que produjo el script), con
fondo oscuro, tipografía monoespaciada y un encabezado con el comando ejecutado.
No se fotografían ventanas: el PNG y el `.txt` son el mismo contenido, y el
`.txt` queda como fuente verificable.

Uso:

    .\\\\.venv\\\\Scripts\\\\python.exe src\\\\capturas_consola.py
    .\\\\.venv\\\\Scripts\\\\python.exe src\\\\capturas_consola.py docs\\\\capturas\\\\01-pipeline-datos\\\\salida-s01-datos.txt
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
CAPTURAS = RAIZ / "docs" / "capturas"

# Comando que produjo cada log; si falta, se usa sólo el nombre del archivo.
COMANDOS = {
    "salida-s01-datos.txt": "python src\\s01_datos.py",
    "salida-s02-tm.txt": "python src\\s02_tm.py",
    "salida-s03-conversion.txt": "python src\\s03_convertir_onnx.py",
    "salida-s04-modelo-b.txt": "python src\\s04_modelo_b.py",
    "salida-s05-umbral.txt": "python src\\s05_calibrar_umbral.py",
    "salida-s06-evaluacion.txt": "python src\\s06_evaluar.py",
    "salida-deploy.txt": 'ssh deploy-residuos@srv1007410 "residuos-deploy sha-3b87c8a"',
    "salida-verificacion.txt": "ssh morfeo@srv1007410 'sudo bash verificar.sh'",
}

PLANTILLA = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: #0f1210; color: #dfe4dd;
    font-family: Consolas, "Cascadia Mono", ui-monospace, monospace;
    font-size: 15px; line-height: 1.55;
  }}
  .marco {{ width: 980px; padding: 34px 38px 38px; }}
  .barra {{
    display: flex; align-items: center; gap: 10px;
    padding-bottom: 18px; margin-bottom: 22px; border-bottom: 1px solid #2a312c;
  }}
  .punto {{ width: 11px; height: 11px; border-radius: 50%; background: #39423b; }}
  .ruta {{ margin-left: 8px; color: #7d8a7f; font-size: 13px; letter-spacing: .04em; }}
  .comando {{ color: #9fd18c; margin: 0 0 20px; white-space: pre-wrap; }}
  .comando .signo {{ color: #6b7a6d; }}
  pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; }}
</style></head><body><div class="marco">
  <div class="barra">
    <span class="punto"></span><span class="punto"></span><span class="punto"></span>
    <span class="ruta">{ruta}</span>
  </div>
  <div class="comando"><span class="signo">PS&gt;</span> {comando}</div>
  <pre>{cuerpo}</pre>
</div></body></html>
"""


def capturar(page, txt: Path) -> Path:
    cuerpo = txt.read_text(encoding="utf-8").rstrip("\n")
    if not cuerpo.strip():
        raise RuntimeError(f"{txt} está vacío")
    comando = COMANDOS.get(txt.name, txt.stem)
    destino = txt.with_suffix(".png")
    page.set_content(
        PLANTILLA.format(
            ruta=html.escape(f"docs\\capturas\\{txt.parent.name}\\{txt.name}"),
            comando=html.escape(comando),
            cuerpo=html.escape(cuerpo),
        )
    )
    page.wait_for_timeout(120)
    alto = page.evaluate(
        "Math.ceil(document.querySelector('.marco').getBoundingClientRect().bottom)"
    )
    # El viewport debe cubrir el log completo: `clip` no captura más allá de él.
    page.set_viewport_size({"width": 980, "height": max(alto, 200)})
    page.wait_for_timeout(80)
    page.screenshot(
        path=str(destino),
        clip={"x": 0, "y": 0, "width": 980, "height": alto},
    )
    print(f"  {destino.relative_to(RAIZ) if destino.is_relative_to(RAIZ) else destino}")
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description="Capturas de consola para el informe")
    parser.add_argument("archivos", nargs="*", type=Path, help="logs .txt a capturar")
    args = parser.parse_args()

    archivos = args.archivos or sorted(CAPTURAS.rglob("*.txt"))
    if not archivos:
        raise SystemExit("no hay .txt en docs/capturas")

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(
            args=["--hide-scrollbars", "--window-size=1000,1400"]
        )
        page = navegador.new_page(viewport={"width": 980, "height": 1300}, device_scale_factor=2)
        print("Consola")
        for txt in archivos:
            capturar(page, txt)
        navegador.close()
    print("Listo")


if __name__ == "__main__":
    main()
