# Guion individual — Ariel David Herrera Ahumada

**Duración objetivo:** 9 min 30 s (ventana exigida: 8–10 min)
**Alcance:** problema y norma, datos y preparación, los dos modelos, calibración del
umbral y resultados experimentales.
**Complemento:** la arquitectura, la interfaz, las pruebas, el despliegue, el cambio
de dominio y las conclusiones los cubre el guion de José. No repetir esas partes.

---

## Reparto y minutaje

| Minuto | Bloque | Apoyo visual |
|---|---|---|
| 0:00–0:50 | Apertura: la norma y el costo del error | Portada |
| 0:50–2:20 | Datos: RealWaste, deduplicación y partición | Tabla 1 (RealWaste) |
| 2:20–3:20 | Proyección normativa y por qué separar material y bolsa | Tabla 2 (proyección) |
| 3:20–5:00 | Modelo A vs. Modelo B | Tabla 3 (configuración) |
| 5:00–6:20 | Calibración del umbral τ = 0,63 | Fig. cobertura–exactitud |
| 6:20–8:20 | Resultados: material, bolsa, abstención y costo del error | Tablas 4–6 y matrices |
| 8:20–9:20 | Cierre y puente a José | Conclusiones |

**Ritmo:** el guion tiene unas 1.455 palabras habladas; a 150 palabras por minuto
son 9 min 40 s. Si hablas más despacio, aplica los recortes del final; si te quedas
corto, tienes dos ampliaciones marcadas con ⊕.

---

## Guion

### 0:00–0:50 — Apertura

Buenos días. Soy Ariel David Herrera Ahumada y este es el proyecto de grado que
desarrollamos con José Arquímedes Soto Montaña para la Maestría en Inteligencia
Artificial de la Universidad de La Salle.

En Colombia, la separación en la fuente es la primera barrera para que el material
aprovechable no termine enterrado. La Resolución 2184 de 2019 fijó tres bolsas:
blanca para aprovechables, verde para orgánicos y negra para no aprovechables. La
norma es clara; la decisión frente a un objeto concreto no lo es. ¿Un vaso de papel
con café va en la blanca? ¿Una bolsa que contuvo comida? Y el error tiene un costo
alto: un solo residuo contaminado puede invalidar una bolsa entera.

Por eso el problema no es solo clasificar el material, sino decidir si la evidencia
alcanza para decidir. Nuestro sistema hace dos cosas por separado: predice el
material con una red convolucional y traduce esa predicción a la bolsa con una
tabla normativa. Si la confianza no alcanza, se abstiene. Yo les voy a contar los
datos, los modelos y los resultados; José les mostrará cómo eso se convierte en una
aplicación real.

*[Pausa breve. Pasar a la diapositiva de datos.]*

### 0:50–2:20 — Datos

Trabajamos con RealWaste: 4.752 imágenes de 524×524 tomadas en el punto de
recepción de un relleno sanitario, en nueve clases de material. El desbalance es
fuerte: Plástico tiene 921 imágenes y Textil 318, casi tres a uno. Esa asimetría
obliga a compensar las clases en la pérdida del Modelo B.

Antes de partir, deduplicamos. Calculamos una huella dHash de 64 bits sobre cada
imagen y eliminamos las que tenían distancia de Hamming menor o igual a 6 respecto
de una ya conservada. Quitamos 535 imágenes, el 11,3 %, y quedaron 4.217. La
partición se hizo después, estratificada por clase y con semilla fija: 2.951 para
entrenamiento, 633 para validación y 633 para prueba, un 70/15/15.

El manifiesto `datos/manifiesto.csv` es la fuente de verdad: cada fila declara la
ruta, la clase, el material, la bolsa y la parte, y ningún script vuelve a repartir.
Eso evita la fuga más común en estos conjuntos: la misma foto, o una variante
redimensionada, en entrenamiento y en prueba. La partición está cubierta por
pruebas que verifican que ninguna clase quede vacía en validación o prueba.

Para la prueba externa usamos TrashNet: 2.527 imágenes de seis clases, tomadas
sobre fondo blanco y con iluminación controlada. No participa en entrenamiento ni
en calibración; se usa una sola vez, al final, para medir el cambio de dominio.

*[Señalar la tabla de conteos por clase. No leer las nueve filas: basta con el
contraste Plástico–Textil y el total.]*

### 2:20–3:20 — Proyección normativa

Las nueve clases se proyectan a tres bolsas con una tabla declarada en el dominio:
Cartón, Vidrio, Metal, Papel y Plástico van a la blanca; Orgánicos y Vegetación a
la verde; No aprovechable y Textil a la negra.

Esta separación es la decisión de diseño más importante del trabajo. Primero,
permite comparar el modelo con la literatura de materiales. Segundo, un cambio en
la norma se resuelve editando la tabla, sin reentrenar. Tercero, obliga a reportar
dos niveles de métrica.

Y aquí hay una trampa que conviene decir en voz alta: como el 63,6 % del corpus va
a la bolsa blanca, la exactitud de bolsa es alta incluso cuando el material está
mal. Un modelo que confunde cartón con plástico acierta la bolsa. Por eso el umbral
se calibra sobre material y no sobre bolsa.

### 3:20–5:00 — Los dos modelos

Comparamos dos caminos con la misma partición y la misma normalización.

El Modelo A es la línea base sin código: Teachable Machine, con 180 imágenes por
clase, redimensionadas a 224×224, y la configuración predeterminada de la
herramienta: 50 épocas, lote de 16 y tasa de aprendizaje 0,001. En total ve 1.620
imágenes.

El Modelo B es MobileNetV3-Small preentrenada en ImageNet. Congelamos todos los
pesos y descongelamos los dos últimos bloques de características y el clasificador.
Entrenamos 12 épocas con AdamW, tasa 3×10⁻⁴, decaimiento de peso 10⁻⁴ y
planificador coseno, lote de 32 y semilla 42. Usamos entropía cruzada con pesos
inversos a la frecuencia de cada clase para compensar el desbalance, y aumento
moderado: recorte aleatorio con escala 0,65–1,0, volteo horizontal, rotación de
hasta 15 grados y variación de brillo, contraste y saturación de 0,2.

La diferencia de datos es deliberada: el A representa el límite de una herramienta
sin código con 180 ejemplos por clase; el B, lo que se obtiene con todo el corpus.
Los dos se normalizan igual, con media y desviación 0,5, es decir `x/127,5 − 1`,
para que la comparación mida modelos y no preprocesados.

Un detalle que documentamos: el SavedModel de Teachable Machine ya trae softmax y
`tf2onnx` la conserva. La API detecta si la salida cruda ya es una distribución y
no la vuelve a normalizar. Es un error sutil que habría aplastado las
probabilidades y habría vuelto inútil el umbral; quedó cubierto con una prueba.

*[Pausa. Pasar a la diapositiva del umbral.]*

### 5:00–6:20 — Calibración del umbral

El umbral se elige en validación y se congela antes de tocar prueba. Buscamos el
menor τ que sostenga al menos 90 % de exactitud de material entre las imágenes
aceptadas. Ese valor es 0,63.

En validación, τ = 0,63 acepta el 77,6 % de las imágenes, con 90,0 % de material y
96,5 % de bolsa correctos. La curva cobertura–exactitud muestra el compromiso: al
subir τ baja la cobertura y sube la exactitud condicional.

Si hubiéramos calibrado sobre bolsa, el barrido habría elegido 0,30: acepta el
99,7 % de las imágenes y la abstención queda decorativa. Calibrar sobre material
hace que el sistema calle cuando no distingue un cartón de un plástico, aunque los
dos vayan a la misma bolsa. Es una decisión de riesgo, no una propiedad del modelo:
preferimos perder cobertura antes que decidir sin evidencia.

### 6:20–8:20 — Resultados

En las 633 imágenes de prueba, el Modelo B supera al A en todas las métricas.
Exactitud de material: 83,6 % frente a 78,2 %. De bolsa: 94,9 % frente a 91,9 %.
F1 macro: 0,841 frente a 0,777. AUC macro: 0,987 frente a 0,971. La diferencia más
grande está en log-loss: 0,450 frente a 0,976. Eso importa porque un modelo
sobreconfiado no puede callar de forma selectiva; sus probabilidades no sirven para
decidir cuándo abstenerse.

Por clase, el B va de 0,968 en Vegetación a 0,746 en No aprovechable. El caso del
Plástico es el más instructivo: precisión 0,881 pero recall 0,712, porque 18 de sus
125 imágenes se predicen como Metal. Cuando el modelo declara plástico acierta; lo
que falla es reconocerlo en todas sus formas.

A nivel de bolsa, la blanca alcanza F1 0,968, la verde 0,952 y la negra 0,873. La
negra es la más difícil: 18 de sus 107 casos se escapan a blanca o verde. Es el
punto débil del sistema y no podemos declararlo confiable.

Con τ = 0,63, el B decide en el 80,9 % de los casos y, entre esos, acierta el 91,8 %
del material y el 98,2 % de la bolsa. El A, con el mismo umbral, decide en el 92,3 %
pero solo acierta el 81,5 % del material: su confianza no está calibrada y el
umbral no lo protege. Esa es la diferencia entre tener un buen clasificador y tener
un clasificador que sabe cuándo no sabe.

La tabla de costo asimétrico lo aterriza. Sin abstención, el B manda 18 residuos de
la negra a aprovechables, el 16,8 % de esa bolsa, y 6 aprovechables a la negra, el
1,5 %. El A manda 21 y 18. El error peligroso es el primero, porque contamina el
flujo aprovechable, y ahí los dos modelos están cerca: alrededor de uno de cada
cinco. La abstención no repara esa frontera, pero evita decidir cuando la evidencia
es débil.

*[Bajar el ritmo en las dos últimas frases. Son la idea que debe quedar.]*

### 8:20–9:20 — Cierre y puente

En resumen: separar la predicción del material de la regla normativa nos permitió
comparar los modelos con métricas de la literatura y reportar la decisión que
realmente le importa al ciudadano. El Modelo B es mejor en todo, sobre todo en
calibración, que es lo que hace útil la abstención. Y el sistema es honesto sobre su
límite: cuando el dominio cambia, la exactitud de material cae al 42 %, como verá
José. Ese límite no se esconde: se mide, se reporta y se pone en la interfaz.

José les va a mostrar cómo un modelo con ese límite se convierte en una aplicación
que dice “no sé” en lugar de adivinar, y cómo se despliega en un VPS real.

Muchas gracias.

---

## Ampliaciones (solo si vas por debajo de 8 minutos)

⊕ **Sobre el AUC y el recall de Plástico.** Un AUC de 0,970 con recall de 0,712 no
es contradictorio: el modelo ordena bien las probabilidades, pero el `argmax` deja
fuera casos que están cerca del segundo lugar. El AUC mide separación; el recall,
la decisión con un umbral implícito de 0,5.

⊕ **Sobre el sesgo normativo del corpus.** El 63,6 % de las imágenes va a la
blanca, el 19,4 % a la verde y el 17,0 % a la negra. La estratificación conserva
esa proporción en las tres particiones, y por eso la exactitud de bolsa no se puede
comparar con la de material sin decir qué se está midiendo.

## Recortes (solo si te pasas de 10 minutos)

- Omite la lista completa de aumentos y di “aumento moderado y pesos por clase”.
- Omite el detalle del doble softmax; José lo menciona en pruebas.
- Reduce la tabla de costo a la frase “el error peligroso es negra→aprovechable y
  ahí los dos modelos están cerca: uno de cada cinco”.

## Preguntas previsibles

**¿Por qué no entrenaron con TrashNet?** Porque es un dominio distinto y se reserva
como prueba externa. Entrenar con él inflaría la métrica y eliminaría la única
medición de generalización que tenemos.

**¿El B gana por arquitectura o por más datos?** Por las dos, y la comparación no
pretende aislarlas: mide lo que obtiene un equipo por cada camino. El B además usa
aumento, pesos por clase y ajuste fino, que el A no puede usar.

**¿Por qué dHash y no otra huella?** Es barata de calcular, robusta a
redimensionados y suficiente para detectar ráfagas y variantes. El umbral 6 es
parte del script y la deduplicación está cubierta por pruebas.

**¿Por qué τ se calibró sobre material y no sobre bolsa?** Porque cinco de las
nueve clases comparten la blanca. Calibrado sobre bolsa, el barrido elige 0,30,
acepta el 99,7 % y la abstención deja de proteger.

**¿La abstención no baja demasiado la cobertura?** Sí, y es deliberado: con
τ = 0,63 el B decide en el 80,9 % de los casos. Preferimos ese 19 % de “no sé”
antes que decidir con evidencia débil y contaminar una bolsa.
