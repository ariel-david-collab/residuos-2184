# Decisiones técnicas

Registro corto de por qué el prototipo está armado así. Cada decisión incluye
la alternativa que se descartó y el motivo, porque el informe las necesita
justificadas y no basta con que funcionen.

## D1 — Un clasificador de materiales, no de bolsas

**Decisión:** el modelo predice las 9 clases de material de RealWaste; la bolsa
sale de una tabla normativa.

**Por qué:** la bolsa no es una propiedad visual del objeto, es una regla de la
Resolución 2184 de 2019 (`blanca` = plástico, vidrio, metal, papel, cartón;
`verde` = orgánicos y vegetación; `negra` = mezcla y textil). Si el modelo
aprendiera las bolsas, tendría 3 clases con menos señal y la aplicación quedaría
atada a la norma vigente: un cambio normativo obligaría a reentrenar.

**Ventaja medida:** la proyección también permite mostrar `P(bolsa)` aunque el
material esté poco claro, y evaluar a nivel de bolsa, que es la decisión real.

## D2 — Abstención con umbral calibrado

**Decisión:** si `max P(material) < τ`, la aplicación no decide y lo dice.

**Por qué:** un residuo mal clasificado contamina la bolsa completa; el costo de
adivinar es mayor que el de pedir revisión. `τ` se calibra en validación
buscando el punto de la curva cobertura–exactitud que sostiene ≥ 92 % de
exactitud a nivel de bolsa, y se congela antes de tocar `test`.

**Descartado:** decidir siempre por `argmax`. Da 100 % de cobertura y esconde los
errores justo en los casos ambiguos.

## D3 — Frontend en Rust y backend en Python

**Decisión:** Leptos (Rust → WASM) para la interfaz; FastAPI + ONNX Runtime para
la inferencia.

**Por qué:** el preprocesado es el punto donde este tipo de proyecto falla en
silencio. Al quedar la evaluación, la calibración y la API en el mismo lenguaje,
la misma función `preprocesar()` produce las imágenes de `test` y las que llegan
por HTTP; no hay dos implementaciones que se puedan desincronizar.

**Descartado:** Rust también en el backend (`axum` + `ort`). Es viable y más
liviano, pero reimplementa el preprocesado en otro lenguaje y añade CGO a cambio
de nada que la evaluación del proyecto mida. Se descartó Go por la misma razón.

## D4 — Un solo contenedor para interfaz y API

**Decisión:** el build de `trunk` y el runtime de Python se combinan en una
imagen multi-stage; FastAPI sirve los estáticos y la API bajo el mismo origen.

**Por qué:** elimina CORS, reduce la superficie a un solo servicio y hace que el
despliegue en el VPS sea `docker compose up -d`. El proxy inverso del servidor
solo tiene que apuntar a `:8080`.

**Descartado:** servir el WASM con Nginx y la API aparte. Añade configuración y
un origen cruzado para ganar nada a esta escala.

## D5 — Modelo de demostración en lugar de pesos falsos

**Decisión:** mientras no exista un `.onnx` entrenado, el backend usa una
heurística de color marcada explícitamente como *demostración* en la interfaz.

**Por qué:** permite construir y probar la aplicación completa antes de entrenar,
sin presentar números inventados como si fueran del modelo. El día que se
copie `models/modelB_improved.onnx`, el backend lo carga solo y la interfaz no
cambia.

**Descartado:** un ONNX con pesos aleatorios. Produciría salidas sin sentido pero
con apariencia de modelo real, que es peor que declarar la limitación.

## D6 — Azure Custom Vision queda fuera del camino crítico

**Decisión:** el endpoint principal corre en el VPS; Azure no se usa para la
demo principal.

**Por qué:** el recurso del curso ya existe (`ai-animales-ariel-2026`, S0 en
`westus2`), pero cobra por predicción y el servicio está anunciado para retiro el
25 de septiembre de 2028, sin admisión de recursos nuevos. Un endpoint que
depende de crédito estudiantil no sirve para un video que hay que poder repetir.

**Consecuencia documentada:** la plataforma de entrenamiento (Teachable Machine)
no expone API para modelos exportados; por eso el modelo se sirve como
microservicio propio. Es una decisión de arquitectura, no un faltante.

## D7 — Dirección visual: cartel de imprenta

**Decisión:** la interfaz usa un lenguaje de cartel: papel cálido, bordes negros
de 2 px, sombra dura sin difuminar, tipografía Archivo Black para el veredicto y
ni un solo gradiente.

**Por qué:** la primera versión (manchas de color animadas, radios de 22 px,
sombras difusas) es el lenguaje por defecto de cualquier generador de interfaces:
se ve amable y no dice nada del proyecto. Aquí el dato central es una decisión
normativa, y el cartel la trata como un sello: el bloque del veredicto toma el
color de la bolsa y el nombre se lee a 50 px. La interfaz deja de competir con el
resultado y pasa a anunciarlo.

**Descartado:** el minimalismo de espacio negativo puro, que se ve elegante pero
esconde la confianza y el top-3; y la consola monoespaciada, que es atractiva para
quien evalua el proyecto y hostil para el ciudadano que separa en casa.

**Consecuencia:** el color de la bolsa manda en el veredicto. Como el verde es a
la vez color de marca y color de la bolsa de orgánicos, el bloque siempre lleva el
nombre escrito; el color nunca es la única señal.

## D8 — Capturas generadas por script, no por ventanas

**Decisión:** todo el material gráfico del informe se produce con programas del
repositorio: `s02_eda.py` para las figuras, `capturas_ui.py` para la interfaz
(Playwright, Chromium headless, 1440×900 y 390×844) y `capturas_consola.py` para
los logs, que dibuja el `.txt` literal como una terminal. El `.txt` se conserva al
lado del PNG.

**Por qué:** una foto de la terminal depende del tamaño de la ventana, del tema
del sistema y de la hora; si hay que repetir una cifra, no se puede. Con un
script, la figura y el texto que la acompaña se regeneran juntos y cualquier
número del informe se rastrea hasta el archivo que lo produjo. Además, las
capturas de la interfaz se pueden volver a tomar contra el servidor real cuando
exista el modelo entrenado, sin rehacer el informe.

**Consecuencia:** `capturas_ui.py` acepta `--base` para apuntar a cualquier
instancia. La franja de la barra de scroll se elimina con `--hide-scrollbars`. El
README de `docs/capturas/` declara que el modelo activo es la heurística de
demostración mientras no haya pesos en `models/`.

## D9 - Una sola normalización de entrada para los dos modelos

**Decisión:** el Modelo B se entrena con media y desvío 0,5, que es exactamente
`px / 127.5 - 1`, la misma normalización que ya usa `api/imagen.py` para el
Modelo A.

**Por qué:** MobileNetV3 se preentrena con la media y el desvío de ImageNet. Usar
esos valores habría obligado a que la API eligiera la normalización según el
modelo cargado: dos caminos de preprocesado y una fuente silenciosa de error si
algún día se cambia `PREFERIDOS`. Con una sola normalización, el vector que arma
la API sirve para cualquiera de los dos ONNX y la comparación A/B mide modelos,
no diferencias de preprocesado.

**Consecuencia:** el ajuste fino parte de pesos de ImageNet normalizados de otro
modo, pero lo absorbe en la primera época. El preprocesado de evaluación
(`Resize((224, 224))` estirado) es el mismo que aplica `api/imagen.py`, así que
las cifras de validación y de la aplicación son comparables.

## D10 - El umbral calibrado lo publica el archivo, no el código

**Decisión:** `src/s05_calibrar_umbral.py` escribe `models/umbral.json` con el
barrido completo de cobertura y exactitud. La API lee ese archivo al arrancar y
usa su `tau` como valor inicial; si el archivo no existe, cae en 0.55.

**Por qué:** el umbral es un resultado del experimento, no una constante de
programación. Si viviera en el código, cada recalibración exigiría editar,
recompilar la imagen y volver a desplegar; así se sustituye un JSON y el informe
puede citar la misma cifra que muestra la aplicación.

## D11 - El umbral se calibra sobre material, no sobre bolsa

**Decisión:** τ* es el menor umbral cuya exactitud de **material** entre lo
aceptado llega al 90 %. Con el Modelo B eso da τ = 0.63, que acepta el 77,6 % de
las imágenes con 90,0 % de material correcto y 96,5 % de bolsa correcta. La curva
completa con las dos métricas queda en `models/umbral.json`.

**Por qué:** cinco de las nueve clases van a la bolsa blanca, así que acertar la
bolsa es fácil aunque el material esté mal. Calibrado sobre bolsa, el barrido
elige τ = 0.30 con 92,5 % de acierto, pero acepta el 99,7 % de las imágenes: el
mecanismo de abstención queda decorativo. Calibrado sobre material, el umbral
hace el trabajo para el que existe: callar cuando el modelo no distingue un
cartón de un plástico, aunque ambos vayan a la misma bolsa.

**Consecuencia:** el informe reporta las dos curvas. La aplicación sigue
mostrando el material y su bolsa, y el umbral sugerido en el control de
exigencia es el que sale de aquí, no una constante escrita a mano.

## D12 - La evaluación externa compara materiales compartidos, no las seis clases

**Decisión:** `src/s06_evaluar.py` evalúa `test/` una sola vez, con el τ de
`models/umbral.json` aplicado por igual a los dos modelos. En TrashNet, la
exactitud de material se mide solo sobre las cinco clases que existen en
RealWaste (cardboard, glass, metal, paper, plastic); `trash` se excluye porque es
una mezcla y no un material. A nivel de bolsa sí entran las seis, con `trash` en
la bolsa negra.

**Por qué:** `trash` de TrashNet agrupa residuos mezclados de cualquier tipo, sin
un material único al que comparar; incluirlo en el denominador de material
castigaría al modelo por no acertar una etiqueta que no existe en su catálogo.
En cambio, para la decisión normativa sí tiene destino: la bolsa negra. Aplicar
el mismo τ a A y B mantiene la comparación honesta: la diferencia de cobertura
es una propiedad del modelo, no del umbral.

**Consecuencia:** el informe reporta la matriz de materiales de 5 clases (con una
sexta columna «otro» para las predicciones fuera del conjunto compartido) y la
matriz de bolsas de 3 clases sobre las 2.527 imágenes.

## D13 - El ONNX de Teachable Machine ya trae softmax; no se repite

**Decisión:** `api/inferencia.py` detecta al cargar si la salida cruda del ONNX
ya es una distribución (componentes no negativas y suma 1) y, en ese caso, la usa
tal cual. Solo aplica softmax cuando el archivo entrega logits.

**Por qué:** el SavedModel de Teachable Machine termina en una capa softmax y
`tf2onnx` la conserva; el modelo de PyTorch termina en logits. Al aplicar softmax
a una salida que ya lo era, el Modelo A quedaba con una distribución aplanada: su
probabilidad máxima nunca pasaba de 0,63 en `test/` y la bolsa predicha era
siempre la blanca (la suma de cinco clases le ganaba a cualquier clase
individual). La exactitud de material no se movía —el argmax es invariante a una
softmax monótona—, pero la abstención y la proyección a bolsas sí.

**Consecuencia:** con la corrección, el Modelo A pasa de 63,7 % a 91,9 % de
exactitud de bolsa en `test/`, su log-loss baja de 1,60 a 0,98 y su abstención
deja de ser total. `api/tests/test_inferencia.py` cubre los dos casos con grafos
ONNX mínimos, para que la regresión no vuelva.

## D14 - La exactitud del modelo se muestra en la app, no se esconde

**Decisión:** `/api/catalogo` publica `metricas` —imágenes de `test/` y
exactitud de material y de bolsa del modelo activo— leídas de
`models/metrics.json`, y la interfaz muestra al pie una frase con esas cifras.

**Por qué:** el plan hablaba de una pestaña de resultados que nunca existió, y
una tabla comparativa A/B no le dice nada al ciudadano que va a usar la app. Una
línea con la exactitud real del modelo que está decidiendo sí: da contexto al
veredicto, sostiene la promesa de abstención y evita que la interfaz parezca
infallable. Se descartó la pestaña por coste y por ruido; el detalle completo
vive en el informe y en `models/metrics.json`.

**Consecuencia:** si `metrics.json` falta o no contiene al modelo activo, la
frase no se muestra; la app nunca inventa una cifra. La cifra se publica al
arrancar la API, igual que τ, así que un modelo nuevo exige reiniciar el
servicio.

## D15 - El despliegue reutiliza el patrón de VPS-Infrastructure

**Decisión:** la app se despliega como una imagen de GHCR detrás del Traefik que
ya corre en el VPS, sin publicar puertos. El `.env` de producción se materializa
desde OpenBao (`secret/residuos/prod`, campo `content`), el tag aprobado vive en
`.release.env` y el CI entra por SSH como `deploy-residuos`, un usuario con
`ForceCommand` que solo puede ejecutar `residuos-deploy <tag>`.

**Por qué:** el VPS ya tiene proxy, TLS, OpenBao y un patrón de deploy probado;
duplicar nginx o abrir un puerto habría añadido superficie y deriva. La app no
maneja credenciales, pero centralizar igual su `.env` deja el servidor
reemplazable y evita archivos editados a mano. El tag pineado hace que un
`docker compose up -d` posterior no vuelva a `:latest`, y el gate por tag
(`vX.Y.Z`) separa "publicar imagen" de "desplegar".

**Consecuencia:** `main` solo publica; desplegar exige un tag o un
`workflow_dispatch` con `deploy_tag`. El rollback es volver a ejecutar el wrapper
con el SHA anterior. `deploy/compose.yaml` y `deploy/setup-deploy-user.sh`
quedan versionados, y `docs/despliegue.md` es el runbook.
