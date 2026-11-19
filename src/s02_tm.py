"""Entrena el Modelo A en Teachable Machine y descarga el modelo exportado.

Automatiza el flujo completo con Playwright sobre Edge: crea las nueve clases,
sube el subconjunto `datos/train_tm_224/`, entrena con los hiperparámetros del
plan (50 épocas, lote 16, tasa 0.001), captura cada etapa y descarga el ZIP
exportado (`model.savedmodel/` y `labels.txt`).

    .\\.venv\\Scripts\\python.exe src\\s02_tm.py
    .\\.venv\\Scripts\\python.exe src\\s02_tm.py --prueba

`--prueba` hace una corrida corta (dos clases, ocho imágenes, dos épocas) para
verificar el flujo sin gastar los veinte minutos del entrenamiento real.

Requiere Edge instalado: el Chromium headless de Playwright no monta esta
aplicación (el contenedor de rutas queda en `display:none`).
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

RAIZ = Path(__file__).resolve().parents[1]
TM = "https://teachablemachine.withgoogle.com/train/image"
MUESTRAS = RAIZ / "datos" / "train_tm_224"
MANIFIESTO = RAIZ / "datos" / "manifiesto.csv"
CAPTURAS = RAIZ / "docs" / "capturas" / "03-teachable-machine"
MODELOS = RAIZ / "models"

# El componente guarda su propio <style>: se excluye para leer sólo texto.
TEXTO_LIMPIO = """(el) => {
  if (!el || !el.shadowRoot) return (el && el.textContent || '').trim();
  const caja = document.createElement('div');
  for (const hijo of el.shadowRoot.children) {
    if (hijo.tagName !== 'STYLE' && hijo.tagName !== 'SCRIPT') caja.append(hijo.cloneNode(true));
  }
  return caja.textContent.replace(/\\s+/g, ' ').trim();
}"""

# Con locale es-CO la interfaz se traduce; estos son sus rótulos.
ANADIR = "Añadir una clase"
AVANZADO = "Avanzado"
EXPORTAR = "Exportar modelo"
DESCARGAR = re.compile(r"Descargar( mi)? modelo")
PATRON_MUESTRAS = re.compile(r"(\d+)\s+muestras de imágenes")

# `tm-progress-button` no tiene un <button>: dentro hay un `tm-button` y el
# botón real vive en el shadow de éste. El progreso se publica como atributos
# del host (`value` avanza hasta `max`), no como texto.
PROGRESO = """(el) => {
  const attrs = {};
  for (const a of el.attributes) attrs[a.name] = a.value;
  return {label: attrs.label || '', value: Number(attrs.value || 0), max: Number(attrs.max || 0)};
}"""

# El globo de ayuda tapa los controles y reaparece varias veces durante el
# flujo. Se oculta con CSS, nunca se elimina: la app guarda referencias a él y
# el clic de entrenamiento revienta con "Cannot set properties of null".
OCULTAR_AYUDA = """() => {
  let n = 0;
  function buscar(raiz) {
    for (const el of raiz.querySelectorAll('*')) {
      if (el.tagName === 'TM-ONBOARD-BOX' || el.tagName === 'TM-ONBOARD-MODAL') {
        el.style.setProperty('display', 'none', 'important');
        n++;
      } else if (el.shadowRoot) buscar(el.shadowRoot);
    }
  }
  buscar(document);
  return n;
}"""

# Centro del <button> real, para clicarlo con el ratón (evento confiable).
PUNTO_ENTRENAR = """(el) => {
  const medio = el.shadowRoot && el.shadowRoot.querySelector('tm-button');
  const boton = medio && medio.shadowRoot && medio.shadowRoot.querySelector('button');
  if (!boton) return null;
  const r = boton.getBoundingClientRect();
  return {x: r.x + r.width / 2, y: r.y + r.height / 2};
}"""


def clases_disponibles() -> list[str]:
    return sorted(p.name for p in MUESTRAS.iterdir() if p.is_dir())


def imagenes(clase: str) -> list[Path]:
    return sorted(
        p for p in (MUESTRAS / clase).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )


def imagen_test(clase: str) -> Path:
    """Una foto del conjunto de prueba, para que la vista previa no use train."""
    with MANIFIESTO.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["parte"] == "test" and fila["clase"] == clase:
                return RAIZ / fila["ruta"]
    raise RuntimeError(f"sin imágenes de test para {clase}")


def ocultar_ayuda(page: Page) -> None:
    page.evaluate(OCULTAR_AYUDA)
    page.wait_for_timeout(200)


def captura(page: Page, nombre: str) -> None:
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    destino = CAPTURAS / nombre
    page.screenshot(path=str(destino))
    print(f"  captura: {destino.relative_to(RAIZ)}")


def texto_drawer(page: Page, indice: int) -> str:
    return page.locator("tm-classifier-drawer").nth(indice).evaluate(TEXTO_LIMPIO)


def abrir(page: Page) -> None:
    page.goto(TM, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_selector("tm-progress-button", timeout=60_000)
    page.wait_for_timeout(8_000)
    ocultar_ayuda(page)


def preparar_clases(page: Page, clases: list[str]) -> None:
    """Renombra las clases existentes y añade las que falten."""
    while page.locator("tm-classifier-drawer").count() < len(clases):
        page.get_by_role("button", name=ANADIR).click()
        page.wait_for_timeout(700)
    ocultar_ayuda(page)

    for i, clase in enumerate(clases):
        page.locator("tm-editable-label").nth(i).click()
        page.wait_for_timeout(250)
        entrada = page.locator("tm-editable-label input").nth(i)
        entrada.fill(clase)
        entrada.press("Enter")
        page.wait_for_timeout(250)
    ocultar_ayuda(page)
    puestas = [page.locator("tm-editable-label input").nth(i).input_value() for i in range(len(clases))]
    if puestas != clases:
        raise RuntimeError(f"nombres inesperados: {puestas}")


def subir_muestras(page: Page, clases: list[str], limite: int, espera: int) -> None:
    for i, clase in enumerate(clases):
        archivos = imagenes(clase)[:limite]
        page.locator("input[type=file][multiple]").nth(i).set_input_files([str(p) for p in archivos])
        inicio = time.time()
        listas = 0
        while time.time() - inicio < espera:
            page.wait_for_timeout(1_000)
            coincidencia = PATRON_MUESTRAS.search(texto_drawer(page, i))
            listas = int(coincidencia.group(1)) if coincidencia else 0
            if listas >= len(archivos):
                break
        print(f"  {clase}: {listas}/{len(archivos)} muestras en {int(time.time() - inicio)} s")
        if listas < len(archivos):
            print(f"  aviso: {clase} quedó con {listas} muestras")


def configurar(page: Page, epocas: int, tasa: float) -> None:
    page.get_by_role("button", name=AVANZADO).click()
    page.wait_for_timeout(600)
    campos = page.locator("input[type=number]:visible")
    campos.nth(0).fill(str(epocas))
    campos.nth(1).fill(str(tasa))
    page.wait_for_timeout(400)
    ocultar_ayuda(page)


def entrenar(page: Page, limite_min: int) -> bool:
    """Pulsa "Preparar modelo" y espera a que `value` alcance `max`."""
    boton = page.locator("tm-progress-button").first
    ocultar_ayuda(page)

    punto = boton.evaluate(PUNTO_ENTRENAR)
    if not punto:
        print("  aviso: no se encontró el botón de entrenamiento")
        return False
    page.mouse.click(punto["x"], punto["y"])

    inicio = time.time()
    estado = boton.evaluate(PROGRESO)
    while time.time() - inicio < 30 and estado["max"] == 0:
        page.wait_for_timeout(1_000)
        estado = boton.evaluate(PROGRESO)

    if estado["max"] == 0:
        print("  aviso: el entrenamiento no arrancó")
        return False

    print(f"  entrenando: {estado['max']} épocas")
    if estado["value"] < estado["max"]:
        captura(page, "05-entrenamiento-en-curso.png")

    fin = time.time() + limite_min * 60
    while time.time() < fin:
        estado = boton.evaluate(PROGRESO)
        if estado["value"] >= estado["max"]:
            print(f"  terminado: {estado['label']} ({estado['value']}/{estado['max']})")
            return True
        page.wait_for_timeout(2_000)
    print("  aviso: se agotó el tiempo de entrenamiento")
    return False


def ultimas_clases(page: Page) -> None:
    """Desplaza la última fila de clases al inicio del área visible, sin cortar tarjetas."""
    cajones = page.locator("tm-classifier-drawer")
    if not cajones.count():
        return
    objetivo = cajones.nth(max(0, cajones.count() - 3))
    objetivo.evaluate(
        """(el) => {
            el.scrollIntoView({block: 'start'});
            let padre = el.parentElement;
            while (padre) {
                const estilo = getComputedStyle(padre);
                if (/(auto|scroll)/.test(estilo.overflowY) && padre.scrollHeight > padre.clientHeight) {
                    padre.scrollBy(0, -86);
                    return;
                }
                padre = padre.parentElement;
            }
            window.scrollBy(0, -86);
        }"""
    )
    page.wait_for_timeout(600)


def vista_previa(page: Page, ejemplo: Path) -> None:
    """Cambia la entrada de la vista previa a 'archivo' y sube una foto."""
    panel = page.locator("tm-run").first
    panel.locator("select#select-input").select_option("archivo", force=True)
    page.wait_for_timeout(1_000)
    panel.locator("input[type=file][accept*='image/png']").set_input_files(str(ejemplo))
    page.wait_for_timeout(3_000)


def exportar(page: Page, destino: Path) -> Path:
    page.get_by_role("button", name=EXPORTAR).click()
    page.wait_for_timeout(2_500)
    ocultar_ayuda(page)

    # Pestaña Tensorflow (Keras), no Tensorflow.js.
    page.get_by_text("Tensorflow", exact=True).first.click()
    page.wait_for_timeout(1_000)
    page.get_by_role("radio").nth(1).check()
    page.wait_for_timeout(1_000)
    captura(page, "07-exportacion.png")

    destino.parent.mkdir(parents=True, exist_ok=True)
    for intento in (1, 2):
        try:
            with page.expect_download(timeout=300_000) as info:
                page.get_by_role("button", name=DESCARGAR).click()
            info.value.save_as(str(destino))
            break
        except PlaywrightTimeout:
            if intento == 2:
                raise SystemExit("la descarga del modelo no arrancó")
            print("  aviso: la descarga no arrancó, reintento")
            page.wait_for_timeout(2_000)
    print(f"  modelo: {destino.relative_to(RAIZ)} ({destino.stat().st_size // 1024} KB)")
    return destino


def flujo(page: Page, clases: list[str], limite: int, epocas: int, tasa: float, espera: int, destino: Path) -> None:
    abrir(page)
    captura(page, "01-proyecto-vacio.png")

    preparar_clases(page, clases)
    captura(page, "02-clases-definidas.png")

    subir_muestras(page, clases, limite, espera)
    ocultar_ayuda(page)
    page.locator("tm-classifier-drawer").first.scroll_into_view_if_needed()
    page.wait_for_timeout(600)
    captura(page, "03-muestras-completas.png")
    ultimas_clases(page)
    captura(page, "04-ultimas-clases.png")

    configurar(page, epocas, tasa)
    captura(page, "04b-avanzado.png")

    if not entrenar(page, 120):
        raise SystemExit("el entrenamiento no terminó")
    vista_previa(page, imagen_test(clases[0]))
    ocultar_ayuda(page)
    captura(page, "06-entrenamiento-terminado.png")
    exportar(page, destino)


def main() -> None:
    parser = argparse.ArgumentParser(description="Modelo A en Teachable Machine")
    parser.add_argument("--prueba", action="store_true", help="dos clases, ocho imágenes, dos épocas")
    parser.add_argument("--limite", type=int, default=180, help="imágenes por clase")
    parser.add_argument("--epocas", type=int, default=50)
    parser.add_argument("--tasa", type=float, default=0.001)
    parser.add_argument("--espera", type=int, default=300, help="segundos máximos por clase")
    parser.add_argument("--salida", type=Path, default=MODELOS / "modelA_tm.zip")
    args = parser.parse_args()

    clases = clases_disponibles()
    limite, epocas, espera = args.limite, args.epocas, args.espera
    if args.prueba:
        clases, limite, epocas, espera = clases[:2], 8, 2, 120
        args.salida = MODELOS / "prueba_tm.zip"

    print(f"Clases: {len(clases)} · hasta {limite} imágenes · {epocas} épocas a {args.tasa}")
    with sync_playwright() as pw:
        navegador: Browser = pw.chromium.launch(channel="msedge", args=["--hide-scrollbars"])
        page = navegador.new_page(viewport={"width": 1440, "height": 900}, locale="es-CO")
        try:
            flujo(page, clases, limite, epocas, args.tasa, espera, args.salida)
        finally:
            navegador.close()


if __name__ == "__main__":
    main()
