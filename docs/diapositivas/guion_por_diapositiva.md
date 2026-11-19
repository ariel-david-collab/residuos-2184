# Guion por diapositiva

Este es el texto que se dice en cada diapositiva, en orden. Las notas del
orador del `.pptx` se generan desde este archivo, así que cada diapositiva
muestra únicamente lo que corresponde decir allí.

- **Recorrido completo:** 17 diapositivas, ~10:50.
- **Si necesitas 9:30:** salta las diapositivas 8 y 9 (van juntas) y pasa de la
  7 a la 10. El resto del guion se mantiene.
- Los guiones individuales de `docs/guiones/` siguen disponibles para una
  entrega por separado.

---

## 1 · Portada

Ariel: Buenos días. Somos Ariel David Herrera Ahumada y José Arquímedes Soto Montaña, de la Maestría en Inteligencia Artificial de la Universidad de La Salle. En Colombia, la Resolución 2184 de 2019 fijó tres bolsas: blanca para aprovechables, verde para orgánicos y negra para no aprovechables. La norma es clara; la decisión frente a un objeto concreto no lo es.

## 2 · La norma es clara; la decisión, no

Ariel: ¿Un vaso de papel con café va en la blanca? ¿Y una bolsa de plástico que contuvo comida? ¿Y un empaque multicapa? El error cuesta caro: un solo residuo contaminado puede invalidar una bolsa entera. Por eso nuestro sistema no solo clasifica el material: también decide si la evidencia alcanza para decidir.

## 3 · Datos

Ariel: Trabajamos con RealWaste: 4.752 imágenes de relleno sanitario en nueve clases, con un desbalance fuerte entre Plástico, 921 imágenes, y Textil, 318. Deduplicamos con una huella dHash de 64 bits y quitamos 535 imágenes, el 11,3 %. La partición estratificada quedó en 2.951 para entrenamiento, 633 para validación y 633 para prueba. El manifiesto CSV es la fuente de verdad y ningún script vuelve a repartir, así que no hay fugas entre entrenamiento y prueba. TrashNet queda aparte: 2.527 imágenes solo para prueba externa; no entrena ni calibra.

## 4 · Nueve materiales, tres bolsas

Ariel: Las nueve clases se proyectan a tres bolsas con una tabla declarada en el dominio: Cartón, Vidrio, Metal, Papel y Plástico a la blanca; Orgánicos y Vegetación a la verde; No aprovechable y Textil a la negra. Esa separación permite comparar el modelo con la literatura, cambiar la norma sin reentrenar y reportar dos niveles. Y evita una trampa: como el 63,6 % del corpus va a la blanca, la exactitud de bolsa es alta incluso cuando el material está mal. Por eso el umbral se calibra sobre material.

## 5 · Dos caminos, la misma vara

Ariel: Comparamos dos caminos con la misma partición y la misma normalización. El Modelo A es la línea base sin código: Teachable Machine, 180 imágenes por clase, 50 épocas, lote 16 y tasa 0,001. El Modelo B es MobileNetV3-Small preentrenada en ImageNet: descongelamos los dos últimos bloques y el clasificador, entrenamos 12 épocas con AdamW, tasa 3×10⁻⁴, planificador coseno, pesos por clase y aumento moderado. El A representa el límite de una herramienta sin código con 180 ejemplos por clase; el B, lo que se obtiene con todo el corpus. Los dos usan la misma normalización, x/127,5 − 1, para que la comparación mida modelos y no preprocesados.

## 6 · Umbral τ = 0,63

Ariel: El umbral se elige en validación y se congela antes de tocar prueba. Buscamos el menor τ que sostenga al menos 90 % de exactitud de material entre las imágenes aceptadas: 0,63. En validación acepta el 77,6 % con 90,0 % de material y 96,5 % de bolsa. Si lo hubiéramos calibrado sobre bolsa, el barrido habría elegido 0,30 y habría aceptado el 99,7 %: la abstención quedaría decorativa. Calibrar sobre material hace que el sistema calle cuando no distingue un cartón de un plástico, aunque ambos vayan a la misma bolsa.

## 7 · El Modelo B gana en todo

Ariel: En las 633 imágenes de prueba, el B supera al A en todo: 83,6 % de material frente a 78,2; 94,9 % de bolsa frente a 91,9; F1 macro 0,841 frente a 0,777; AUC 0,987 frente a 0,971. La diferencia más grande es el log-loss, 0,450 frente a 0,976: las probabilidades del B sí sirven para decidir cuándo abstenerse. A nivel de bolsa, la negra es el punto débil: 18 de sus 107 casos se escapan. Con τ = 0,63 el B decide en el 80,9 % y acierta 91,8 % de material y 98,2 % de bolsa; el A decide en el 92,3 % pero solo acierta 81,5 % del material. Esa es la diferencia entre un buen clasificador y uno que sabe cuándo no sabe.

## 8 · Acierta cuando decide; falla al reconocer

Ariel: [Diapositiva opcional si vas justo de tiempo.] Por clase, el B va de 0,968 en Vegetación a 0,746 en No aprovechable. El caso del Plástico es el más instructivo: precisión 0,881 pero recall 0,712, porque 18 de sus 125 imágenes se predicen como Metal. Cuando el modelo declara plástico acierta; lo que falla es reconocerlo en todas sus formas. El AUC mide separación entre clases; el recall, la decisión con un umbral implícito de 0,5.

## 9 · La bolsa negra es el punto débil

Ariel: A nivel de bolsa, la blanca alcanza F1 0,968, la verde 0,952 y la negra 0,873. La negra es la más difícil: 18 de sus 107 casos se escapan a blanca o verde. La tabla de costo asimétrico lo aterriza: sin abstención, el B manda 18 residuos de la negra a aprovechables, el 16,8 % de esa bolsa, y 6 aprovechables a la negra, el 1,5 %. El error peligroso es el primero, porque contamina el flujo aprovechable. La abstención no repara esa frontera, pero evita decidir cuando la evidencia es débil.

## 10 · Relevo

Ariel: José les va a mostrar cómo ese modelo se convierte en una aplicación que dice “no sé” en lugar de adivinar, y cómo se despliega en un VPS real.

## 11 · Cuatro capas y una regla

José: Gracias, Ariel. La pregunta de ingeniería es cómo llevar esa decisión a una persona sin esconder el error. El sistema tiene cuatro capas: dominio, inferencia, HTTP e interfaz. El dominio declara los nueve materiales, las tres bolsas y la función decidir(probs, tau); no importa FastAPI ni ONNX. La interfaz es Rust con Leptos compilada a WebAssembly, y el contenedor final combina el WASM y el runtime de Python en una sola imagen: no hay CORS ni un segundo servicio que operar. El contrato tiene cuatro rutas: health, catalogo, predict y predict-lote.

## 12 · El veredicto se lee en color y en palabra

José: La interfaz es un cartel de imprenta: papel cálido, bordes negros de dos píxeles y Archivo Black para el veredicto. El bloque toma el color de la bolsa pero también escribe su nombre: el color nunca es la única señal. El control de exigencia va de 0,30 a 0,90, arranca en 0,63 y está visible sin scroll, con una frase en lenguaje llano que explica el corte. El panel muestra confianza, top-3 y masa por bolsa; el lote resume cuántas fotos van a cada bolsa y cuántas quedaron sin decidir. Al pie se imprime la exactitud real del modelo, leída de metrics.json; si falta, la frase no se muestra. La aplicación nunca inventa una cifra. [Demo: foto clara → veredicto.]

## 13 · El modelo duda

José: [Demo: subir el umbral a 0,90 y usar una foto ambigua.] Cuando el umbral sube a 0,90 y la foto no es clara, el veredicto cambia: “El modelo duda. Ninguna clase supera el umbral. Revisa si el residuo está limpio y seco, o consulta la guía de tu punto ecológico antes de elegir la bolsa.” La bolsa de mayor masa sigue apareciendo, pero como sugerencia a revisar, no como veredicto. Ese matiz es el corazón del trabajo.

## 14 · 35 pruebas, cuatro suites

José: El repositorio tiene 35 pruebas en cuatro suites y corren en menos de un segundo: datos, dominio, imagen e inferencia. Cubren la deduplicación, la proyección a bolsas, el borde exactamente igual a τ, la forma NHWC en [−1, 1], el orden RGB y el doble softmax. Son el primer paso del pipeline: si fallan, la imagen no se publica. La cadena completa son siete scripts y un manifiesto; la partición es determinista y las cifras del informe se regeneran con s06_evaluar.py.

## 15 · Un contenedor, ningún puerto público

José: La imagen se construye en dos etapas y pesa 471 MB. Corre como usuario sin privilegios y no publica puertos: solo la alcanza Traefik por la red interna web, que termina TLS. Let’s Encrypt emite el certificado y HTTP redirige a HTTPS con 301. La imagen se publica en GHCR. El despliegue lo ejecuta un usuario con ForceCommand: solo puede invocar residuos-deploy <tag>, y el wrapper valida el tag contra una allowlist; una llave comprometida no entrega una shell. Las credenciales se materializan desde OpenBao y el tag queda en .release.env. El CI corre pruebas, escanea secretos con gitleaks y publica la imagen; el despliegue se dispara con un tag vX.Y.Z o manual con el tag explícito. El runner entra por Tailscale porque el SSH público está cerrado. Una ejecución completa tarda alrededor de un minuto y la inferencia, entre 5 y 12 milisegundos en CPU.

## 16 · Cuando el dominio cambia, la métrica se cae

José: La prueba externa pone los pies en la tierra. En TrashNet, la exactitud de material del B cae al 42,4 %. La exactitud de bolsa parece alta, 92,9 %, pero está inflada: 2.390 de las 2.527 imágenes van a la blanca; la F1 macro de bolsa es 0,349 y el recall de la negra, 0,058. Con abstención, el B acepta el 57,7 % y sube al 49,0 %: el umbral filtra ruido, pero no repara el cambio de dominio. Las limitaciones son claras: una foto por objeto, dominio de relleno sanitario, clases ambiguas y ningún estudio con usuarios.

## 17 · Cierre

José: En conclusión: separamos la predicción del material de la regla normativa, calibramos el umbral sobre validación, lo evaluamos una sola vez sobre prueba y lo desplegamos con TLS, contenedor sin privilegios y CI/CD. El prototipo no reemplaza la norma ni la decisión de la autoridad ambiental, pero demuestra que un sistema puede decir “no sé” cuando no sabe. Esa es la conducta más honesta frente a un residuo que puede contaminar una bolsa entera. Muchas gracias.
