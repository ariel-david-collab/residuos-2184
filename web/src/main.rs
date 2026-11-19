//! Interfaz del clasificador normativo de residuos.
//!
//! Tres estados: reposo (zona de carga), analizando y veredicto. El veredicto
//! responde con la bolsa de la Resolución 2184, no solo con el material.

use std::collections::BTreeMap;

use gloo_net::http::Request;
use leptos::mount::mount_to_body;
use leptos::prelude::*;
use serde::Deserialize;
use wasm_bindgen::JsCast;
use wasm_bindgen_futures::spawn_local;
use web_sys::{Blob, DragEvent, File, FormData, HtmlInputElement, Url};

// ---------------------------------------------------------------- contrato API

#[derive(Clone, Debug, Deserialize)]
#[allow(dead_code)]
struct Top {
    clase: String,
    material: String,
    p: f64,
}

#[derive(Clone, Debug, Deserialize)]
#[allow(dead_code)]
struct Prediccion {
    archivo: String,
    material: Option<String>,
    clase: Option<String>,
    bolsa: String,
    bolsa_nombre: String,
    bolsa_rotulo: String,
    bolsa_detalle: String,
    bolsa_color: String,
    bolsa_borde: String,
    bolsa_texto: String,
    confianza: f64,
    abstenido: bool,
    top3: Vec<Top>,
    bolsas_prob: BTreeMap<String, f64>,
    latencia_ms: f64,
}

#[derive(Clone, Debug, Deserialize)]
#[allow(dead_code)]
struct Lote {
    total: usize,
    por_bolsa: BTreeMap<String, usize>,
    por_material: BTreeMap<String, usize>,
    abstenidos: usize,
    latencia_ms: f64,
    resultados: Vec<Prediccion>,
}

#[derive(Clone, Debug)]
enum Estado {
    Reposo,
    Cargando,
    Listo(Prediccion),
    Error(String),
}

// ---------------------------------------------------------------- red

fn archivos_de(lista: &web_sys::FileList) -> Vec<File> {
    (0..lista.length()).filter_map(|i| lista.get(i)).collect()
}

fn acento(bolsa: &str) -> &'static str {
    match bolsa {
        "verde" => "#16a34a",
        "negra" => "#18181b",
        _ => "#ffffff",
    }
}

async fn enviar_uno(archivo: &File, tau: f64) -> Result<Prediccion, String> {
    let datos = FormData::new().map_err(|_| "no se pudo preparar el envío".to_string())?;
    datos
        .append_with_blob_and_filename("archivo", archivo.unchecked_ref::<Blob>(), &archivo.name())
        .map_err(|_| "no se pudo adjuntar la imagen".to_string())?;
    datos
        .append_with_str("tau", &format!("{tau:.2}"))
        .map_err(|_| "no se pudo adjuntar el umbral".to_string())?;

    let respuesta = Request::post("/api/predict")
        .body(datos)
        .map_err(|e| format!("{e:?}"))?
        .send()
        .await
        .map_err(|e| format!("{e:?}"))?;

    if !respuesta.ok() {
        return Err(format!("el servidor respondió {}", respuesta.status()));
    }
    respuesta
        .json::<Prediccion>()
        .await
        .map_err(|e| format!("{e:?}"))
}

async fn enviar_lote(archivos: &[File], tau: f64) -> Result<Lote, String> {
    let datos = FormData::new().map_err(|_| "no se pudo preparar el envío".to_string())?;
    for a in archivos {
        datos
            .append_with_blob_and_filename("archivos", a.unchecked_ref::<Blob>(), &a.name())
            .map_err(|_| "no se pudo adjuntar una imagen".to_string())?;
    }
    datos
        .append_with_str("tau", &format!("{tau:.2}"))
        .map_err(|_| "no se pudo adjuntar el umbral".to_string())?;

    let respuesta = Request::post("/api/predict-lote")
        .body(datos)
        .map_err(|e| format!("{e:?}"))?
        .send()
        .await
        .map_err(|e| format!("{e:?}"))?;

    if !respuesta.ok() {
        return Err(format!("el servidor respondió {}", respuesta.status()));
    }
    respuesta.json::<Lote>().await.map_err(|e| format!("{e:?}"))
}

fn procesar_uno(
    archivos: Vec<File>,
    tau: f64,
    estado: RwSignal<Estado>,
    vista: RwSignal<Option<String>>,
    ultimo: RwSignal<Option<File>>,
) {
    let Some(archivo) = archivos.into_iter().next() else {
        return;
    };
    if let Ok(url) = Url::create_object_url_with_blob(archivo.unchecked_ref::<Blob>()) {
        vista.set(Some(url));
    }
    ultimo.set(Some(archivo.clone()));
    estado.set(Estado::Cargando);

    spawn_local(async move {
        match enviar_uno(&archivo, tau).await {
            Ok(p) => estado.set(Estado::Listo(p)),
            Err(e) => estado.set(Estado::Error(e)),
        }
    });
}

// ---------------------------------------------------------------- piezas

fn icono_subida() -> impl IntoView {
    view! {
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 16.5V4.5M12 4.5 7.2 9.3M12 4.5l4.8 4.8"
                stroke="#0a0a0a" stroke-width="2.2" stroke-linecap="square" />
            <path d="M4.5 15.5v2.7a2.3 2.3 0 0 0 2.3 2.3h10.4a2.3 2.3 0 0 0 2.3-2.3v-2.7"
                stroke="#0a0a0a" stroke-width="2.2" />
        </svg>
    }
}

fn icono_bolsa(color: &str, tinta: &str) -> impl IntoView {
    let relleno = color.to_string();
    let linea = tinta.to_string();
    view! {
        <svg class="bolsa-ico" viewBox="0 0 64 72" aria-hidden="true">
            <path
                d="M22.5 25.5c0-10.2 19-10.2 19 0"
                fill="none"
                stroke=linea.clone()
                stroke-width="3.5"
                stroke-linecap="round"
            />
            <path
                d="M11 26h42l-3.4 36.2a4.2 4.2 0 0 1-4.2 3.8H18.6a4.2 4.2 0 0 1-4.2-3.8L11 26Z"
                fill=relleno
                stroke=linea
                stroke-width="3.5"
                stroke-linejoin="round"
            />
        </svg>
    }
}

fn icono_alerta() -> impl IntoView {
    view! {
        <svg width="17" height="17" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <rect x="1" y="1" width="18" height="18" stroke="#3d2c00" stroke-width="2" />
            <path d="M10 5.5v6" stroke="#3d2c00" stroke-width="2.2" stroke-linecap="square" />
            <rect x="9" y="13.6" width="2" height="2" fill="#3d2c00" />
        </svg>
    }
}

// ---------------------------------------------------------------- app

#[component]
fn App() -> impl IntoView {
    let estado = RwSignal::new(Estado::Reposo);
    let vista = RwSignal::new(Option::<String>::None);
    let ultimo = RwSignal::new(Option::<File>::None);
    let tau = RwSignal::new(0.55_f64);
    let modelo = RwSignal::new("demostración".to_string());
    let metricas = RwSignal::new(Option::<(u64, f64, f64)>::None);
    let arrastrando = RwSignal::new(false);
    let lote = RwSignal::new(Option::<Lote>::None);
    let lote_cargando = RwSignal::new(false);
    let lote_error = RwSignal::new(Option::<String>::None);

    spawn_local(async move {
        if let Ok(r) = Request::get("/api/health").send().await {
            if let Ok(v) = r.json::<serde_json::Value>().await {
                if let Some(nombre) = v.get("modelo").and_then(|m| m.as_str()) {
                    modelo.set(nombre.to_string());
                }
            }
        }
        // El umbral y la exactitud los publica la API desde models/.
        if let Ok(r) = Request::get("/api/catalogo").send().await {
            if let Ok(v) = r.json::<serde_json::Value>().await {
                if let Some(sugerido) = v.get("tau_sugerido").and_then(|t| t.as_f64()) {
                    tau.set(sugerido.clamp(0.30, 0.90));
                }
                if let Some(m) = v.get("metricas").filter(|m| !m.is_null()) {
                    let imagenes = m.get("imagenes").and_then(|x| x.as_u64());
                    let material = m.get("exactitud_material").and_then(|x| x.as_f64());
                    let bolsa = m.get("exactitud_bolsa").and_then(|x| x.as_f64());
                    if let (Some(n), Some(mat), Some(bol)) = (imagenes, material, bolsa) {
                        metricas.set(Some((n, mat, bol)));
                    }
                }
            }
        }
    });

    let reiniciar = move |_| {
        if let Some(url) = vista.get_untracked() {
            Url::revoke_object_url(&url).ok();
        }
        vista.set(None);
        ultimo.set(None);
        estado.set(Estado::Reposo);
    };

    view! {
        <div class="marco">
            <header class="top">
                <a class="marca" href="/">
                    <span class="sello">"R"</span>
                    <span class="marca-txt">
                        <b>"Residuos 2184"</b>
                        <span class="marca-sub">"Clasificación con destino normativo"</span>
                    </span>
                </a>
                <span class="estado">
                    <i class="punto"></i>
                    {move || format!("modelo · {}", modelo.get())}
                </span>
            </header>

            <main>
                <section class="hero">
                    <div class="hero-txt">
                        <p class="ceja">"Resolución 2184 de 2019 · Colombia"</p>
                        <h1 class="titulo">
                            "¿A qué bolsa "
                            <span class="titulo-marca">"va esto?"</span>
                        </h1>
                        <div class="hero-pie">
                            <p class="bajada">
                                "Sube una foto del residuo. El modelo reconoce el material y te dice "
                                "en cuál de las tres bolsas del código de colores va. Si no está "
                                "seguro, no adivina."
                            </p>
                            <ul class="leyenda">
                                <li><i style="background:#ffffff"></i>"Blanca"</li>
                                <li><i style="background:#16a34a"></i>"Verde"</li>
                                <li><i style="background:#18181b"></i>"Negra"</li>
                            </ul>
                        </div>
                    </div>

                    <aside class="ajuste" aria-labelledby="ajuste-t">
                        <div class="ajuste-cab">
                            <span id="ajuste-t">"Exigencia para decidir"</span>
                            <b>{move || format!("{:.2}", tau.get())}</b>
                        </div>
                        <input
                            class="rango"
                            type="range"
                            min="0.30"
                            max="0.90"
                            step="0.01"
                            value=move || format!("{:.2}", tau.get())
                            aria-label="Umbral de abstención"
                            aria-describedby="ajuste-p"
                            style=move || format!("--pct:{:.0}%", (tau.get() - 0.30) / 0.60 * 100.0)
                            on:input=move |ev| {
                                if let Some(t) = ev.target()
                                    .and_then(|t| t.dyn_into::<HtmlInputElement>().ok())
                                {
                                    if let Ok(v) = t.value().parse::<f64>() {
                                        tau.set(v);
                                    }
                                }
                            }
                            on:change=move |_| {
                                if let Some(archivo) = ultimo.get_untracked() {
                                    procesar_uno(
                                        vec![archivo],
                                        tau.get_untracked(),
                                        estado,
                                        vista,
                                        ultimo,
                                    );
                                }
                            }
                        />
                        <div class="escala">
                            <span>"permisivo 0.30"</span>
                            <span>"exigente 0.90"</span>
                        </div>
                        <p class="ajuste-p" id="ajuste-p">
                            "Si el material ganador no llega a "
                            <b>{move || format!("{:.2}", tau.get())}</b>
                            " de confianza, la app no elige bolsa: te pide revisar. Ese corte es el "
                            "umbral de abstención, y existe porque un residuo mal clasificado "
                            "contamina la bolsa entera."
                        </p>
                    </aside>
                </section>

                <section class="panel" aria-live="polite">
                    {move || match estado.get() {
                        Estado::Reposo => view! {
                            <label
                                class=move || if arrastrando.get() { "zona activa" } else { "zona" }
                                on:dragover=move |ev: DragEvent| {
                                    ev.prevent_default();
                                    arrastrando.set(true);
                                }
                                on:dragleave=move |_| arrastrando.set(false)
                                on:drop=move |ev: DragEvent| {
                                    ev.prevent_default();
                                    arrastrando.set(false);
                                    if let Some(dt) = ev.data_transfer() {
                                        if let Some(lista) = dt.files() {
                                            procesar_uno(archivos_de(&lista), tau.get_untracked(), estado, vista, ultimo);
                                        }
                                    }
                                }
                            >
                                <input
                                    type="file"
                                    class="oculto"
                                    accept="image/*"
                                    aria-label="Subir una foto del residuo"
                                    on:change=move |ev| {
                                        if let Some(input) = ev.target()
                                            .and_then(|t| t.dyn_into::<HtmlInputElement>().ok())
                                        {
                                            if let Some(lista) = input.files() {
                                                procesar_uno(archivos_de(&lista), tau.get_untracked(), estado, vista, ultimo);
                                            }
                                            input.set_value("");
                                        }
                                    }
                                />
                                <span class="zona-interior">
                                    <span class="zona-ico">{icono_subida()}</span>
                                    <span class="zona-titulo">"Suelta la foto aquí"</span>
                                    <span class="zona-pista">"o haz clic · JPG, PNG o WEBP"</span>
                                </span>
                            </label>
                        }.into_any(),

                        Estado::Cargando => view! {
                            <div class="cargando">
                                <span class="obra"></span>
                                <p>"Mirando el residuo…"</p>
                            </div>
                        }.into_any(),

                        Estado::Error(mensaje) => view! {
                            <div class="error">
                                <p>"No pude leer esa imagen"</p>
                                <span>{mensaje}</span>
                                <div class="acciones" style="justify-content:center;margin-top:1.1rem">
                                    <button class="boton fantasma" on:click=reiniciar>"Intentar de nuevo"</button>
                                </div>
                            </div>
                        }.into_any(),

                        Estado::Listo(p) => {
                            let estilo_bolsa = format!(
                                "background:{};color:{}",
                                p.bolsa_color, p.bolsa_texto
                            );
                            let foto = vista.get().unwrap_or_default();
                            let material = p.material.clone().unwrap_or_else(|| "Sin decidir".into());
                            let nombre_bolsa = p.bolsa_nombre.clone();
                            let subtitulo = if p.abstenido {
                                "Sin decidir · revisa antes de elegir".to_string()
                            } else {
                                format!("{} · {}", material, p.bolsa_rotulo)
                            };
                            let sticker = if p.abstenido {
                                "No decidido".to_string()
                            } else {
                                format!("{:.0}% seguro", p.confianza * 100.0)
                            };
                            let barras: Vec<_> = p.top3.iter().enumerate().map(|(i, t)| {
                                let ancho = format!("width:{:.1}%", t.p * 100.0);
                                let retardo = format!("animation-delay:{:.2}s", 0.1 + 0.06 * i as f64);
                                view! {
                                    <div class="barra" title=t.clase.clone()>
                                        <div class="barra-nombre">{t.material.clone()}</div>
                                        <b class="barra-pct">{format!("{:.0}%", t.p * 100.0)}</b>
                                        <i class="barra-fill" style=format!("{ancho};{retardo}")></i>
                                    </div>
                                }
                            }).collect_view();

                            view! {
                                <div class="resultado">
                                    <div class="veredicto" style=estilo_bolsa>
                                        <span class="sticker">{sticker}</span>
                                        <div class="veredicto-cab">
                                            {icono_bolsa(&p.bolsa_color, &p.bolsa_texto)}
                                            <div class="veredicto-txt">
                                                <p class="kicker">
                                                    {if p.abstenido { "Bolsa sugerida" } else { "Va en" }}
                                                </p>
                                                <h2 class="bolsa-nombre" title=p.bolsa_detalle.clone()>
                                                    {nombre_bolsa}
                                                </h2>
                                                <p class="material">{subtitulo}</p>
                                            </div>
                                        </div>
                                        <img class="vista" src=foto alt="La foto que analizaste" />
                                    </div>

                                    <div class="barras">{barras}</div>

                                    {p.abstenido.then(|| view! {
                                        <div class="abstencion">
                                            {icono_alerta()}
                                            <span>
                                                <b>"El modelo duda"</b>
                                                "Ninguna clase supera el umbral. Revisa si el residuo "
                                                "está limpio y seco, o consulta la guía de tu punto "
                                                "ecológico antes de elegir la bolsa."
                                            </span>
                                        </div>
                                    })}

                                    <div class="acciones">
                                        <button class="boton" on:click=reiniciar>"Probar con otra foto"</button>
                                    </div>
                                </div>
                            }.into_any()
                        },
                    }}
                </section>

                <section class="lote">
                    <div class="lote-cab">
                        <h2>"Un lote completo"</h2>
                        <p>"Varias fotos a la vez"</p>
                        <label class="enlace">
                            <input
                                type="file"
                                class="oculto"
                                accept="image/*"
                                multiple=true
                                aria-label="Subir varias fotos para el lote"
                                on:change=move |ev| {
                                    if let Some(input) = ev.target()
                                        .and_then(|t| t.dyn_into::<HtmlInputElement>().ok())
                                    {
                                        let mut elegidos = Vec::new();
                                        if let Some(lista) = input.files() {
                                            elegidos = archivos_de(&lista);
                                        }
                                        input.set_value("");
                                        if elegidos.is_empty() {
                                            return;
                                        }
                                        lote_cargando.set(true);
                                        lote_error.set(None);
                                        spawn_local(async move {
                                            match enviar_lote(&elegidos, tau.get_untracked()).await {
                                                Ok(l) => lote.set(Some(l)),
                                                Err(e) => {
                                                    lote.set(None);
                                                    lote_error.set(Some(e));
                                                }
                                            }
                                            lote_cargando.set(false);
                                        });
                                    }
                                }
                            />
                            "Elegir archivos"
                        </label>
                    </div>

                    {move || {
                        if lote_cargando.get() {
                            return view! {
                                <div class="cargando" style="border:0;box-shadow:none;padding:2rem 1rem">
                                    <span class="obra"></span>
                                    <p>"Contando bolsas…"</p>
                                </div>
                            }.into_any();
                        }
                        if let Some(e) = lote_error.get() {
                            return view! {
                                <p class="nota">{format!("No se pudo procesar el lote: {e}")}</p>
                            }.into_any();
                        }
                        match lote.get() {
                            None => view! {
                                <p class="nota">
                                    "Aún no has cargado un lote. Sirve para revisar una bolsa completa "
                                    "o comparar el modelo contra un conjunto etiquetado."
                                </p>
                            }.into_any(),
                            Some(l) => {
                                let blanca = l.por_bolsa.get("blanca").copied().unwrap_or(0);
                                let verde = l.por_bolsa.get("verde").copied().unwrap_or(0);
                                let negra = l.por_bolsa.get("negra").copied().unwrap_or(0);
                                let filas: Vec<_> = l.resultados.iter().take(14).map(|r| {
                                    let color = if r.abstenido { "#d9d7cc" } else { acento(&r.bolsa) };
                                    let etiqueta = if r.abstenido {
                                        "Sin decidir".to_string()
                                    } else {
                                        format!("{} · {}", r.material.clone().unwrap_or_default(), r.bolsa_nombre.clone())
                                    };
                                    view! {
                                        <li>
                                            <span class="nombre-archivo" title=r.archivo.clone()>{r.archivo.clone()}</span>
                                            <span class="veredicto-mini">
                                                <i style=format!("background:{color}")></i>
                                                {etiqueta}
                                            </span>
                                            <span class="pct">{format!("{:.0}%", r.confianza * 100.0)}</span>
                                        </li>
                                    }
                                }).collect_view();

                                view! {
                                    <div>
                                        <div class="chips">
                                            <span class="chip-bolsa">
                                                <i style="background:#ffffff"></i>"Blanca" <b>{blanca}</b>
                                            </span>
                                            <span class="chip-bolsa">
                                                <i style="background:#16a34a"></i>"Verde" <b>{verde}</b>
                                            </span>
                                            <span class="chip-bolsa">
                                                <i style="background:#18181b"></i>"Negra" <b>{negra}</b>
                                            </span>
                                            <span class="chip-bolsa">
                                                "Sin decidir" <b>{l.abstenidos}</b>
                                            </span>
                                        </div>
                                        <ul class="lista">{filas}</ul>
                                        <p class="nota">
                                            {format!(
                                                "{} imágenes · {} sin decidir · {:.0} ms en total",
                                                l.total, l.abstenidos, l.latencia_ms
                                            )}
                                        </p>
                                    </div>
                                }.into_any()
                            }
                        }
                    }}
                </section>

                <p class="nota">
                    "Prototipo académico: reconoce nueve materiales y los proyecta a las tres bolsas "
                    "de la Resolución 2184 de 2019. El umbral de exigencia se calibró sobre el "
                    "conjunto de validación; si el modelo duda, se abstiene."
                </p>
                {move || {
                    metricas
                        .get()
                        .map(|(n, material, bolsa)| {
                            view! {
                                <p class="nota nota-metrica">
                                    {format!(
                                        "Sobre {n} fotos reservadas para prueba, este modelo acierta el {:.1}% del material y el {:.1}% de la bolsa.",
                                        material * 100.0,
                                        bolsa * 100.0,
                                    )}
                                </p>
                            }
                        })
                }}
            </main>
        </div>
    }
}

fn main() {
    mount_to_body(App);
}
