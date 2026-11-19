# Guion individual — José Arquímedes Soto Montaña

**Duración objetivo:** 9 min 30 s (ventana exigida: 8–10 min)
**Alcance:** arquitectura, dominio, contrato, interfaz, pruebas, despliegue y
seguridad, cambio de dominio, limitaciones y conclusiones.
**Complemento:** los datos, los dos modelos, la calibración del umbral y las
métricas base los cubre el guion de Ariel. No repetir esas partes; solo
referenciarlas.

---

## Reparto y minutaje

| Minuto | Bloque | Apoyo visual |
|---|---|---|
| 0:00–0:50 | Apertura: del modelo a la persona | Portada |
| 0:50–2:20 | Arquitectura: cuatro capas y un contrato | Diagrama de componentes |
| 2:20–4:10 | Interfaz y demostración | Capturas de veredicto y lote |
| 4:10–5:10 | La abstención en la práctica | Captura con τ = 0,90 |
| 5:10–6:10 | Pruebas y reproducibilidad | Tabla de suites |
| 6:10–8:00 | Despliegue, CI/CD y seguridad | Captura del pipeline |
| 8:00–9:00 | Cambio de dominio y límites | Tabla TrashNet |
| 9:00–9:30 | Cierre | Conclusiones |

**Ritmo:** el guion tiene unas 1.435 palabras habladas; sin demostración son
9 min 15 s–9 min 35 s a 150–155 palabras por minuto. La demo en vivo puede consumir
20–30 segundos: ten la captura de respaldo abierta por si falla la red y, si te
pasas, aplica los recortes del final.

---

## Guion

### 0:00–0:50 — Apertura

Buenos días. Soy José Arquímedes Soto Montaña. Ariel les mostró el modelo, el
umbral y las cifras. A mí me toca la otra mitad: cómo un clasificador que acierta
el 83,6 % del material y se abstiene cuando no sabe se convierte en algo que una
persona usa desde el celular, y cómo se opera sin romper nada.

La pregunta de ingeniería es esta: ¿cómo llevamos esa decisión a una aplicación
real sin esconder el error?

### 0:50–2:20 — Arquitectura

El sistema tiene cuatro capas y una regla: el dominio no depende de nada.

La capa de dominio declara los nueve materiales, las tres bolsas y la función
`decidir(probs, tau)`. No importa FastAPI ni ONNX. La capa de inferencia carga el
ONNX, preprocesa la imagen y devuelve probabilidades. La capa HTTP expone el contrato y sirve los estáticos. La
interfaz es una aplicación Rust con Leptos compilada a WebAssembly.

El contenedor final combina el WASM y el runtime de Python en una sola imagen. Esa
decisión es deliberada: no hay CORS, no hay un segundo servicio que operar y el
frontend y la API comparten origen.

El contrato tiene cuatro rutas. `/api/health` responde el modelo activo y el número
de clases. `/api/catalogo` publica materiales, bolsas, τ sugerido y las métricas del
modelo. `/api/predict` recibe un archivo y un τ opcional y devuelve una decisión.
`/api/predict-lote` recibe varios archivos y agrega conteos por bolsa, por material
y de abstenidos. Los archivos se limitan a 12 MB y se rechazan con 400 si no se
pueden decodificar.

La función `decidir` devuelve el material ganador, la bolsa de mayor masa, la
confianza, el top-3 y las probabilidades por bolsa. Si la confianza es menor que τ,
el material se devuelve como nulo y la respuesta marca `abstenido=true`; la bolsa
sugerida sigue siendo la de mayor masa, pero la interfaz la presenta como una
sugerencia a revisar, no como un veredicto.

### 2:20–4:10 — Interfaz y demostración

La dirección visual es un cartel de imprenta: papel cálido, bordes negros de dos
píxeles, sombra dura y tipografía Archivo Black para el veredicto. El bloque del
veredicto toma el color de la bolsa, pero también escribe su nombre: el color nunca
es la única señal. Eso importa para daltonismo y para una foto impresa en blanco y
negro.

El control de exigencia va de 0,30 a 0,90, en pasos de 0,01, y arranca en el τ que
publica el catálogo: 0,63. Está visible sin hacer scroll. Debajo hay una frase en
lenguaje llano: “Si el material ganador no llega a 0,63 de confianza, la app no
elige bolsa: te pide revisar. Ese corte es el umbral de abstención, y existe porque
un residuo mal clasificado contamina la bolsa entera.”

El panel muestra la confianza, las tres probabilidades mayores y la masa por bolsa.
El lote acepta varias fotos y resume cuántas van a cada bolsa y cuántas quedaron sin
decidir. Al pie se imprime la exactitud real del modelo activo, leída de
`metrics.json`; si el archivo falta, la frase no se muestra. La aplicación nunca
inventa una cifra.

*[Demostración: subir una foto clara, señalar material, bolsa, confianza y top-3.
Luego subir una foto ambigua y mostrar la abstención. Si no hay red, usar las
capturas.]*

En el teléfono, el selector de archivos abre la cámara o la galería, y por eso el
despliegue exige HTTPS. La vista móvil es la misma aplicación, no una versión
recortada.

### 4:10–5:10 — La abstención en la práctica

Cuando subimos el umbral a 0,90 y la foto no es clara, el veredicto cambia: “El
modelo duda. Ninguna clase supera el umbral. Revisa si el residuo está limpio y
seco, o consulta la guía de tu punto ecológico antes de elegir la bolsa.”

La bolsa de mayor masa sigue apareciendo, pero como sugerencia a revisar, no como
veredicto. Ese matiz es el corazón del proyecto: el sistema no decide por el
ciudadano cuando no tiene evidencia. En la demostración se ve con una foto ambigua:
la barra de confianza no alcanza, el bloque se vuelve gris y la aplicación pide
revisar.

Y hay una razón técnica: la softmax de una red moderna suele ser sobreconfiada. Un
modelo que siempre dice 0,99 no puede callar de forma selectiva. Por eso el umbral
se calibra en validación y se congela, y por eso la aplicación publica la exactitud
real del modelo que está decidiendo.

### 5:10–6:10 — Pruebas y reproducibilidad

El repositorio tiene 35 pruebas en cuatro suites y corren en menos de un segundo.
La suite de datos verifica la huella dHash, la deduplicación, la estratificación y
la reproducibilidad de la partición. La de dominio cubre la proyección a bolsas, la
conservación de la masa de probabilidad, la abstención, el borde exactamente igual
a τ y el top-3. La de imagen comprueba la forma NHWC, el rango [−1, 1], el orden RGB
y la escala de grises. La de inferencia cubre el doble softmax y el contrato,
incluidos los lotes y los archivos inválidos.

Esas pruebas son el primer paso del pipeline: si fallan, la imagen no se publica.
La cadena completa son siete scripts y un manifiesto; la partición es determinista
y las cifras del informe se regeneran con `s06_evaluar.py`. Esa cadena es más
valiosa que cualquier resultado puntual, porque convierte cada afirmación en algo
que otro equipo puede repetir.

### 6:10–8:00 — Despliegue, CI/CD y seguridad

La imagen se construye en dos etapas. Una imagen de Rust compila el WASM con
`trunk`; una `python:3.12-slim` instala las dependencias, copia la API, los modelos
y el WASM, crea un usuario sin privilegios y declara un `HEALTHCHECK` contra
`/api/health`. La imagen final pesa 471 MB.

El contenedor no publica puertos: solo lo alcanza Traefik por la red interna `web`,
que es el único punto de entrada y el que termina TLS. Let’s Encrypt emite el
certificado y HTTP redirige a HTTPS con 301. La imagen se publica en GHCR.

El despliegue lo ejecuta un usuario `deploy-residuos` con `ForceCommand`: solo puede
invocar `residuos-deploy <tag>`, y el wrapper valida el tag contra una allowlist. Una
llave comprometida no entrega una shell. Las credenciales no viven en el
repositorio: el archivo `.env` se materializa desde OpenBao y el tag desplegado
queda registrado en `.release.env`.

El CI corre las pruebas, escanea secretos con gitleaks y publica la imagen. El
despliegue se dispara con un tag `vX.Y.Z` o con una ejecución manual que indica el
tag de forma explícita. Como el puerto SSH público está cerrado, el runner entra por
un nodo efímero de Tailscale. Una ejecución completa tarda alrededor de un minuto:
17 segundos de pruebas, 30 de imagen y 14 de despliegue.

En el VPS, la inferencia de una imagen tarda entre 5 y 12 milisegundos en CPU,
incluido el preprocesado.

### 8:00–9:00 — Cambio de dominio y límites

La prueba externa es la que pone los pies en la tierra. En TrashNet, con fondo
blanco y otra distribución, la exactitud de material del Modelo B cae al 42,4 %. La
exactitud de bolsa parece alta, 92,9 %, pero está inflada: 2.390 de las 2.527
imágenes van a la blanca. La F1 macro de bolsa es 0,349 y el recall de la negra,
0,058.

Con abstención, el B acepta el 57,7 % y sube al 49,0 % de material. El umbral filtra
algo de ruido, pero no repara el cambio de dominio. La conclusión honesta es que el
modelo no generaliza a un dominio fotográfico distinto sin ajuste, y que la
exactitud de bolsa no se debe leer sin la matriz.

Las limitaciones son claras: una foto por objeto, sin detección ni segmentación;
dominio de relleno sanitario; clases ambiguas como plástico, metal y no
aprovechable; umbral global; y ningún estudio con usuarios. El trabajo futuro es
detección y segmentación de múltiples objetos, calibración por clase o por bolsa,
predicción conforme y el modelo en el dispositivo con ONNX Runtime Web, para que la
foto no salga del teléfono.

### 9:00–9:30 — Cierre

En conclusión: construimos un sistema completo que separa la predicción del material
de la regla normativa, calibra el umbral sobre validación, lo evalúa una sola vez
sobre prueba y lo despliega con TLS, contenedor sin privilegios y CI/CD. El
prototipo no reemplaza la norma ni la decisión de la autoridad ambiental, pero
demuestra que un sistema puede decir “no sé” cuando no sabe. Esa es la conducta más
honesta frente a un residuo que puede contaminar una bolsa entera.

Muchas gracias.

---

## Ampliaciones (solo si vas por debajo de 8 minutos)

⊕ **Sobre la elección de Rust y Leptos.** El cliente se compila a WebAssembly y se
sirve desde el mismo contenedor que la API. No hay un framework de JavaScript en el
medio ni CORS; el binario y el HTML viajan juntos y la interfaz queda como un
artefacto más de la imagen.

⊕ **Sobre el costo de un solo contenedor.** Es una decisión KISS: un servicio, un
puerto interno, un `health check` y un `docker compose`. Para este alcance, separar
frontend y backend habría agregado un segundo despliegue y un CORS que mantener sin
beneficio medible.

## Recortes (solo si te pasas de 10 minutos)

- Omite la lista de las cuatro suites y di “35 pruebas en menos de un segundo”.
- Omite los tiempos del pipeline; basta con “alrededor de un minuto”.
- Reduce la demostración a la captura de abstención.

## Preguntas previsibles

**¿Por qué no Kubernetes?** Porque el alcance es un servicio con un contenedor y un
VPS. Kubernetes habría agregado complejidad operativa sin mejorar ninguna métrica
del proyecto; `docker compose` y Traefik resuelven lo mismo con menos superficie.

**¿Cómo protegen los secretos?** No están en el repositorio: el `.env` se
materializa desde OpenBao, gitleaks escanea cada push, el usuario de despliegue
tiene `ForceCommand` con allowlist de tags y el SSH público está cerrado; el CI
entra por Tailscale.

**¿Qué pasa si el modelo no carga?** La API falla al arrancar, el `HEALTHCHECK` no
responde y el contenedor queda `unhealthy`; el wrapper de despliegue verifica el
health check antes de dar el tag por bueno.

**¿Por qué el frontend está en Rust?** Porque el proyecto ya tenía esa decisión y
Leptos compila a WASM sin runtime de JavaScript. La interfaz es un artefacto
estático que se sirve desde el mismo origen, sin CORS ni un segundo servicio.

**¿La aplicación guarda las fotos?** No. La respuesta incluye el veredicto, las
probabilidades y la latencia; la imagen se procesa en memoria y no se almacena.
