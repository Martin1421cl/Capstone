import { RIESGOS, api, nombreTipo } from "./api.js";
import { aviso, campoTexto, confirmar, contarHasta, dialogo, el, formatoFecha, icono, plural, puede, revelarHallazgo } from "./ui.js";

const $ = (id) => document.getElementById(id);
const id = new URLSearchParams(location.search).get("id");
const SEGUNDOS_VISIBLE = 20;
const POR_PAGINA = 15;
const filtros = { riesgo: "", tipo: "", buscar: "", revision: "", pagina: 1, orden: "riesgo", invertir: false };
// Revisión de hallazgos (RF-16)
const REVISION = { pendiente: "Pendiente", confirmado: "Confirmado", falso_positivo: "Falso positivo" };
const REVISION_PLURAL = { pendiente: ["pendiente", "pendientes"], confirmado: ["confirmado", "confirmados"],
  falso_positivo: ["falso positivo", "falsos positivos"] };
const FILTROS_REVISION = [["pendiente", "Pendientes"], ["confirmado", "Confirmados"], ["falso_positivo", "Falsos positivos"],
  ["sin_falsos", "Sin falsos positivos"]];
let totalFiltrado = 0;  // cuántos hallazgos cumplen los filtros: lo usa "Revisar los N del filtro"
// Vista de hallazgos: "tipos" (una columna por tipo de dato) o "detalle" (una fila por hallazgo).
// Se recuerda en este navegador; si el navegador no deja guardar, parte en "tipos".
const CLAVE_VISTA = "ksecure.vistaHallazgos";
let vista = "tipos";
try { if (localStorage.getItem(CLAVE_VISTA) === "detalle") vista = "detalle"; } catch { /* sin almacenamiento */ }
// Cómo se lee cada orden, normal e invertido.
const ORDENES = {
  riesgo: ["Riesgo", "mayor primero", "menor primero"],
  tipo: ["Tipo", "RUT, tarjetas, cuentas…", "al revés"],
  confianza: ["Confianza", "mayor primero", "menor primero"],
  ubicacion: ["Dónde", "en orden del archivo", "al revés"],
};

let detalle;
try {
  detalle = await api(`/escaneos/${id}`);
} catch {
  $("titulo").textContent = "Escaneo no encontrado";
  document.querySelectorAll(".section, #kpis, #revision").forEach((s) => s.remove());
  document.getElementById("exportar").remove();
  throw new Error("escaneo no encontrado");
}

// --- Encabezado ------------------------------------------------------------------
document.title = `${detalle.origen_nombre} · K-Secure`;
$("titulo").textContent = detalle.origen_nombre;
if (!puede("Auditor")) document.querySelector("#sec-hallazgos .section-title p").textContent = "Enmascarados: tu rol permite ver los resultados, no los originales.";
$("meta").textContent = `${detalle.origen_tipo === "bd" ? "Base de datos" : "Archivos"} · ${formatoFecha(detalle.fecha)}`;
$("borrar").hidden = !puede("Auditor");  // el Visor solo mira
$("borrar").addEventListener("click", async () => {
  const ok = await confirmar({
    titulo: "¿Borrar este escaneo?",
    detalle: detalle.origen_nombre,
    texto: `Se eliminan sus ${plural(detalle.total, "hallazgo")} y los originales cifrados. No se puede deshacer.`,
    textoBoton: "Borrar escaneo",
    peligro: true,
  });
  if (!ok) return;
  try {
    await api(`/escaneos/${id}`, { method: "DELETE" });
    location.href = "/historial.html";
  } catch (e) {
    aviso(e.message, "error");
  }
});

// --- Tarjetas por riesgo (al hacer clic filtran la tabla) ---------------------------
$("kpis").append(...RIESGOS.map((r) => {
  const valor = el("div", { class: "valor" }, "0");
  const kpi = el("button", {
    type: "button", class: `card card-hover kpi risk-${r.id} entrar`,
    "aria-pressed": "false", onclick: () => {
      filtros.riesgo = filtros.riesgo === r.id ? "" : r.id;
      $("filtro-riesgo").value = filtros.riesgo;
      marcarKpi();
      recargar();
    },
  }, el("div", { class: "etiqueta" }, r.id), valor, el("p", { class: "descripcion" }, r.descripcion));
  kpi.dataset.riesgo = r.id;
  contarHasta(valor, detalle.por_riesgo[r.id]);
  return kpi;
}));

function marcarKpi() {
  for (const k of $("kpis").children) {
    const activo = k.dataset.riesgo === filtros.riesgo;
    k.classList.toggle("activo", activo);
    k.setAttribute("aria-pressed", String(activo));
  }
}

// --- Por tipo y qué se revisó ---------------------------------------------------------
const maxTipo = Math.max(1, ...Object.values(detalle.por_tipo));
$("por-tipo").append(...(Object.keys(detalle.por_tipo).length
  ? Object.entries(detalle.por_tipo).map(([tipo, n]) => {
    const barra = el("span");
    requestAnimationFrame(() => { barra.style.width = `${(100 * n) / maxTipo}%`; });
    return el("div", { class: "tipo-fila" },
      el("strong", {}, nombreTipo(tipo)), el("div", { class: "barra" }, barra), el("span", { class: "n" }, String(n)));
  })
  : [el("p", { class: "muted" }, "No se encontraron datos sensibles. 🎉")]));

const revisado = detalle.origen_tipo === "bd" || detalle.filas_revisadas
  ? [["Tablas", detalle.fuentes], ["Filas", detalle.filas_revisadas], ["Columnas sensibles", detalle.columnas.length]]
  : [["Archivos con hallazgos", detalle.fuentes], ["Hallazgos", detalle.total], ["No se pudieron leer", detalle.errores.length]];
$("revisado").append(...revisado.map(([texto, n]) =>
  el("div", { class: "tipo-fila", style: "grid-template-columns:1fr auto" },
    el("span", { class: "muted" }, texto), el("strong", {}, Number(n).toLocaleString("es-CL")))));

// --- Columnas sensibles (bases de datos) -------------------------------------------------
if (detalle.columnas.length) {
  $("sec-columnas").hidden = false;
  $("columnas").append(...detalle.columnas.map((c) => {
    const barra = el("span");
    requestAnimationFrame(() => { barra.style.width = `${c.porcentaje}%`; });
    return el("button", {
      type: "button", class: `card card-hover columna-card risk-${c.riesgo}`,
     
      title: "Ver los hallazgos de esta columna",
      onclick: () => {
        $("filtro-buscar").value = c.columna;
        filtros.buscar = c.columna;
        filtros.pagina = 1;
        recargar();
        $("sec-hallazgos").scrollIntoView({ behavior: "smooth", block: "start" });
      },
    },
      el("div", { class: "fuente" }, c.fuente),
      el("div", { class: "nombre" }, c.columna),
      el("div", { class: "pie" }, el("span", {}, nombreTipo(c.tipo)), el("span", { class: "badge" }, c.riesgo)),
      el("div", { class: "barra", style: "margin-top:12px" }, barra),
      el("div", { class: "muted", style: "font-size:.82rem;margin-top:6px" },
        `${c.porcentaje}% de las filas (${c.filas_con_datos.toLocaleString("es-CL")})`));
  }));
}

// --- Avance de la revisión (RF-16) ----------------------------------------------------------
function pintarRevision(r) {
  const total = r.pendiente + r.confirmado + r.falso_positivo;
  const revisados = r.confirmado + r.falso_positivo;
  const pct = (n) => (total ? (100 * n) / total : 0);
  const filtrarPor = (estado) => () => {
    filtros.revision = filtros.revision === estado ? "" : estado;
    $("filtro-revision").value = filtros.revision;
    filtros.pagina = 1;
    recargar();
    $("sec-hallazgos").scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const chip = (estado, n) => el("button", {
    type: "button", class: `chip-revision rev-${estado}`, onclick: filtrarPor(estado),
    "aria-pressed": String(filtros.revision === estado), title: `Ver solo los ${REVISION_PLURAL[estado][1]}`,
  }, el("strong", {}, n.toLocaleString("es-CL")), ` ${REVISION_PLURAL[estado][n === 1 ? 0 : 1]}`);
  $("revision").replaceChildren(
    el("div", { class: "revision-titulo" },
      el("h2", {}, "Revisión"),
      el("span", { class: "muted" }, total
        ? `${revisados.toLocaleString("es-CL")} de ${total.toLocaleString("es-CL")} revisados (${Math.round(pct(revisados))} %)`
        : "Sin hallazgos que revisar")),
    el("div", { class: "barra-revision", role: "img",
      "aria-label": `${r.confirmado} confirmados, ${r.falso_positivo} falsos positivos, ${r.pendiente} pendientes` },
      el("span", { class: "rev-confirmado", style: `width:${pct(r.confirmado)}%` }),
      el("span", { class: "rev-falso_positivo", style: `width:${pct(r.falso_positivo)}%` })),
    el("div", { class: "chips-revision" }, chip("confirmado", r.confirmado), chip("falso_positivo", r.falso_positivo),
      chip("pendiente", r.pendiente)),
    puede("Auditor") && total
      ? el("p", { class: "muted ayuda-revision" }, "Marca cada hallazgo en la vista Detalle, o todos los del filtro con «Revisar…». Queda en la bitácora.")
      : null);
}
let resumenRevision = detalle.revision;
pintarRevision(resumenRevision);

async function actualizarResumenRevision() {
  resumenRevision = (await api(`/escaneos/${id}`)).revision;
  pintarRevision(resumenRevision);
}

// --- Errores ----------------------------------------------------------------------------
if (detalle.errores.length) {
  $("sec-errores").hidden = false;
  $("errores").append(...detalle.errores.map((e) => el("li", {}, e)));
}

// --- Tabla de hallazgos -------------------------------------------------------------------
RIESGOS.forEach((r) => $("filtro-riesgo").append(el("option", { value: r.id }, r.id)));
Object.keys(detalle.por_tipo).forEach((t) => $("filtro-tipo").append(el("option", { value: t }, nombreTipo(t))));
FILTROS_REVISION.forEach(([valor, texto]) => $("filtro-revision").append(el("option", { value: valor }, texto)));

// Marcar un hallazgo. El falso positivo pide el motivo (opcional), que queda en la bitácora.
async function marcar(h, estado) {
  let nota = null;
  if (estado === "falso_positivo") {
    const datos = await dialogo("¿Falso positivo?", `${nombreTipo(h.tipo)} ${h.valor} · ${h.columna ? `${h.fuente}.${h.columna}` : h.fuente}`,
      [campoTexto("nota", "Motivo (opcional)", { required: false, ayuda: "Ej.: es un número de pedido, son datos de prueba." })],
      "Marcar falso positivo", async (form) => ({ nota: new FormData(form).get("nota") }), { iconoNombre: "x" });
    if (!datos) return;
    nota = datos.nota;
  }
  try {
    await api(`/escaneos/${id}/hallazgos/${h.id}/revision`, { method: "PUT", json: { estado, nota } });
    aviso(estado === "pendiente" ? "Vuelve a estar pendiente" : `Marcado como ${REVISION[estado].toLowerCase()}`);
    await Promise.all([recargar(), actualizarResumenRevision()]);
  } catch (e) {
    aviso(e.message, "error");
  }
}

function celdaRevision(h) {
  const boton = (ic, texto, estado) => el("button", {
    type: "button", class: "btn btn-icon btn-sm", "aria-label": texto, title: texto, onclick: () => marcar(h, estado) }, icono(ic));
  const quien = h.revision === "pendiente" ? null
    : el("div", { class: "muted rev-info", title: h.nota || "" }, `@${h.revisado_por}`, h.nota ? ` · «${h.nota}»` : "");
  return el("div", { class: "celda-revision" },
    el("div", {}, el("span", { class: `badge rev-${h.revision}` }, REVISION[h.revision]), quien),
    puede("Auditor") ? el("div", { class: "rev-acciones" },
      h.revision !== "confirmado" ? boton("check", "Confirmar: sí es un dato sensible", "confirmado") : null,
      h.revision !== "falso_positivo" ? boton("x", "Falso positivo", "falso_positivo") : null,
      h.revision !== "pendiente" ? boton("deshacer", "Volver a pendiente", "pendiente") : null) : null);
}

// "Revisar los N del filtro": marca de una vez todo lo que se ve con los filtros actuales (ej. una columna).
function actualizarRevisarVarios() {
  const b = $("revisar-varios");
  b.hidden = !puede("Auditor") || totalFiltrado === 0;
  b.replaceChildren(icono("check"), `Revisar ${totalFiltrado === 1 ? "este" : `estos ${totalFiltrado.toLocaleString("es-CL")}`}…`);
}

$("revisar-varios").addEventListener("click", async () => {
  const opcion = (valor, titulo, texto, marcada = false) => el("label", { class: `opcion` },
    el("input", { type: "radio", name: "estado", value: valor, checked: marcada, required: true }),
    el("strong", {}, titulo), el("span", {}, texto));
  const hecho = await dialogo(`Revisar ${plural(totalFiltrado, "hallazgo")}`,
    "Se marcan todos los que cumplen los filtros de la tabla, no solo los de esta página.",
    [el("div", { class: "campo" }, el("label", {}, "Marcar como"), el("div", { class: "opciones" },
      opcion("confirmado", "Confirmado", "Sí son datos sensibles.", true),
      opcion("falso_positivo", "Falso positivo", "No son datos sensibles."),
      opcion("pendiente", "Pendiente", "Deshace la revisión."))),
    campoTexto("nota", "Motivo (opcional)", { required: false })],
    "Marcar", async (form) => {
      const { estado, nota } = Object.fromEntries(new FormData(form));
      const { riesgo, tipo, buscar, revision } = filtros;
      return api(`/escaneos/${id}/revision`, { method: "POST", json: { estado, nota, riesgo, tipo, buscar, revision } });
    }, { iconoNombre: "check", clase: "ancho-medio" });
  if (!hecho) return;
  aviso(`${plural(hecho.marcados, "hallazgo")} ${hecho.marcados === 1 ? "marcado" : "marcados"}`);
  await Promise.all([recargar(), actualizarResumenRevision()]);
});

// Valor enmascarado con los asteriscos (y los separadores que los siguen) en gris tenue:
// así destaca la parte del dato que sí se ve. "****-****-****-7484" → solo "7484" en blanco.
function valorEnmascarado(v) {
  const tenue = (i) => v[i] === "*" || ("-.· ".includes(v[i]) && v[i - 1] === "*");
  const partes = [];
  for (let i = 0; i < v.length;) {
    let j = i + 1;
    while (j < v.length && tenue(j) === tenue(i)) j++;
    partes.push(tenue(i) ? el("span", { class: "mascara" }, v.slice(i, j)) : v.slice(i, j));
    i = j;
  }
  return partes;
}

// El ojo solo aparece para quien puede ver originales (Auditor o Admin).
const botonOjo = () => !puede("Auditor") ? null
  : el("button", { class: "btn btn-icon btn-sm", type: "button", "aria-label": "Ver dato original" }, icono("ojo"));

// El ojo pide la clave de auditor y muestra el original 20 segundos en "texto"; "marca" se pinta mientras tanto.
function conRevelar(h, texto, boton, marca) {
  const enmascarar = () => texto.replaceChildren(...valorEnmascarado(h.valor));
  enmascarar();
  boton?.addEventListener("click", async () => {
    try {
      const original = await revelarHallazgo(h.id);
      if (original == null) return;
      texto.textContent = original;
      marca.classList.add("revelado");
      boton.replaceChildren(icono("ojoNo"));
      setTimeout(() => {
        enmascarar();
        marca.classList.remove("revelado");
        boton.replaceChildren(icono("ojo"));
      }, SEGUNDOS_VISIBLE * 1000);
    } catch (e) {
      aviso(e.message, "error");
    }
  });
}

function celdaValor(h) {
  const texto = el("span");
  const boton = botonOjo();
  const celda = el("span", { class: "valor" }, texto, boton);
  conRevelar(h, texto, boton, celda);
  return celda;
}

// Encabezados ordenables: un clic ordena por esa columna, otro clic invierte el orden.
for (const th of document.querySelectorAll("th[data-orden]")) {
  const boton = el("button", { type: "button", class: "orden" }, th.textContent, el("span", { class: "flecha", "aria-hidden": "true" }));
  boton.addEventListener("click", () => {
    filtros.invertir = filtros.orden === th.dataset.orden ? !filtros.invertir : false;
    filtros.orden = th.dataset.orden;
    filtros.pagina = 1;
    recargar();
  });
  th.replaceChildren(boton);
}

function marcarOrden() {
  for (const th of document.querySelectorAll("th[data-orden]")) {
    const activo = th.dataset.orden === filtros.orden;
    th.classList.toggle("activo", activo);
    th.querySelector(".flecha").textContent = activo ? (filtros.invertir ? "↑" : "↓") : "↕";
    if (activo) th.setAttribute("aria-sort", filtros.invertir ? "descending" : "ascending");
    else th.removeAttribute("aria-sort");
  }
  const [nombre, normal, invertido] = ORDENES[filtros.orden];
  $("info-orden").textContent = vista === "tipos"
    ? "Cada columna parte por el mayor riesgo"
    : `Ordenado por ${nombre.toLowerCase()}: ${filtros.invertir ? invertido : normal}`;
}

// --- Vista por tipo: una columna por tipo de dato -------------------------------------------
// Una celda: el dato a la izquierda, dónde está debajo, y el ojo siempre en el borde derecho.
// Si su riesgo es distinto al de la columna (ej. un RUT de empresa en la columna RUT), se marca.
function celdaTipo(h, riesgoColumna) {
  // Dónde está, corto: "kna1.stcd1" (sin el "archivo.db ›") o "contrato.docx · línea 4". Lo completo va en el tooltip.
  const tabla = h.fuente.split(" › ").pop();
  const corto = h.columna ? `${tabla}.${h.columna}` : `${h.fuente} · ${h.posicion}`;
  const completo = h.columna ? `${h.fuente}.${h.columna} · ${h.posicion}` : corto;
  const distinto = h.riesgo !== riesgoColumna;
  const texto = el("span", { class: "valor-texto" });
  const boton = botonOjo();
  conRevelar(h, texto, boton, texto);
  const revision = h.revision === "pendiente" ? "" : `\nRevisión: ${REVISION[h.revision]} (@${h.revisado_por})${h.nota ? ` · ${h.nota}` : ""}`;
  return el("div", {
    class: `celda-tipo rev-${h.revision}`,
    title: `${h.valor}\n${completo}\n${h.riesgo} · confianza ${h.nivel_confianza} ${h.confianza}%${revision}`,
  },
    el("div", { class: "info" },
      texto,
      el("div", { class: "donde" }, el("span", { class: "lugar" }, corto),
        distinto ? el("span", { class: `riesgo-celda risk-${h.riesgo}` }, `· ${h.riesgo}`) : null)),
    boton);
}

// Sin barras de desplazamiento: se muestran las columnas que caben completas (240px o más cada una)
// y las flechas ‹ › del encabezado pasan a los demás tipos. Hacia abajo se mueve solo la página,
// con los encabezados pegados arriba.
const ANCHO_COLUMNA = 240;
let datosTipos = null;    // última respuesta de /por-tipo: las flechas mueven columnas sin volver a pedirla
let primeraColumna = 0;   // índice del primer tipo a la vista
let tiposAnteriores = "";

const caben = () => {
  const ancho = $("vista-tipos").clientWidth || document.querySelector("main .container").clientWidth;
  return Math.max(1, Math.floor(ancho / ANCHO_COLUMNA));
};

function botonFlecha(paso) {
  const atras = paso < 0;
  return el("button", {
    type: "button", class: "btn btn-icon btn-sm flecha-tipos",
    "aria-label": atras ? "Ver los tipos anteriores" : "Ver más tipos", title: atras ? "Tipos anteriores" : "Más tipos",
    onclick: () => { primeraColumna += paso * caben(); pintarTipos(); },
  }, icono(atras ? "flechaIzq" : "flecha"));
}

async function cargarTipos() {
  const { riesgo, tipo, buscar, revision, pagina } = filtros;
  const q = new URLSearchParams({ riesgo, tipo, buscar, revision, pagina, por_pagina: POR_PAGINA });
  datosTipos = await api(`/escaneos/${id}/por-tipo?${q}`);
  totalFiltrado = datosTipos.total;
  actualizarRevisarVarios();
  // Si cambió qué tipos hay (otro filtro), se vuelve al primero; al cambiar de página se mantiene.
  const tipos = datosTipos.columnas.map((c) => c.tipo).join();
  if (tipos !== tiposAnteriores) primeraColumna = 0;
  tiposAnteriores = tipos;
  pintarTipos();
  const n = datosTipos.columnas.length;
  paginar(datosTipos.pagina, datosTipos.paginas,
    `${datosTipos.total.toLocaleString("es-CL")} hallazgos en ${n === 1 ? "1 tipo" : `${n} tipos`}`);
}

function pintarTipos() {
  if (!datosTipos) return;
  const todas = datosTipos.columnas;
  const visibles = Math.min(caben(), Math.max(1, todas.length));
  primeraColumna = Math.min(Math.max(0, primeraColumna), Math.max(0, todas.length - visibles));
  const columnas = todas.slice(primeraColumna, primeraColumna + visibles);
  const hayAntes = primeraColumna > 0;
  const hayDespues = primeraColumna + visibles < todas.length;

  $("cabecera-tipos").replaceChildren(...(columnas.length
    ? columnas.map((c, i) => el("th", { scope: "col", class: `risk-${c.riesgo}` },
      el("div", { class: "cabeza-tipo" },
        i === 0 && hayAntes ? botonFlecha(-1) : null,
        el("div", { class: "col-tipo" },
          el("span", { class: "nombre" }, nombreTipo(c.tipo)),
          el("span", { class: "meta" },
            el("span", { class: "badge" }, c.riesgo),
            `${c.total.toLocaleString("es-CL")} ${c.total === 1 ? "dato" : "datos"}`)),
        i === columnas.length - 1 && hayDespues ? botonFlecha(1) : null)))
    : [el("th", { scope: "col" }, "Tipo de dato")]));

  // Todas las columnas a la vista miden lo mismo (ver .tabla-tipos en el CSS).
  $("vista-tipos").querySelector("table").style.setProperty("--columnas", Math.max(1, columnas.length));

  const filas = Math.max(0, ...columnas.map((c) => c.items.length));
  const celda = (c, h) => !h ? el("td")
    : el("td", h.riesgo !== c.riesgo ? { class: `excepcion risk-${h.riesgo}` } : {}, celdaTipo(h, c.riesgo));
  $("filas-tipos").replaceChildren(...(filas
    ? Array.from({ length: filas }, (_, i) => el("tr", { style: `animation-delay:${Math.min(i, 15) * 25}ms` },
      columnas.map((c) => celda(c, c.items[i]))))
    : [el("tr", {}, el("td", { colspan: Math.max(1, columnas.length), class: "vacio" }, "Sin hallazgos con estos filtros"))]));

  const rango = columnas.length === 1 ? `tipo ${primeraColumna + 1}`
    : `tipos ${primeraColumna + 1}–${primeraColumna + columnas.length}`;
  $("info-orden").textContent = todas.length > visibles
    ? `Cada columna parte por el mayor riesgo · ${rango} de ${todas.length}`
    : "Cada columna parte por el mayor riesgo";
}

// Los encabezados se pegan justo bajo el menú del sitio, que en celular es más alto.
const fijarAltoMenu = () => document.documentElement.style.setProperty(
  "--alto-menu", `${document.querySelector(".site-header")?.offsetHeight || 0}px`);
fijarAltoMenu();
let esperaAncho;
addEventListener("resize", () => {
  clearTimeout(esperaAncho);
  esperaAncho = setTimeout(() => { fijarAltoMenu(); if (vista === "tipos") pintarTipos(); }, 150);
});

// --- Vista de detalle: una fila por hallazgo -------------------------------------------------
async function cargarDetalle() {
  const q = new URLSearchParams({ ...filtros, por_pagina: POR_PAGINA });
  const datos = await api(`/escaneos/${id}/hallazgos?${q}`);
  totalFiltrado = datos.total;
  actualizarRevisarVarios();
  $("hallazgos").replaceChildren(...(datos.items.length
    ? datos.items.map((h, i) => el("tr", { class: `rev-${h.revision}`, style: `animation-delay:${Math.min(i, 15) * 25}ms` },
      el("td", {}, el("div", {}, h.columna ? `${h.fuente}.${h.columna}` : h.fuente),
        el("div", { class: "muted", style: "font-size:.8rem" }, h.posicion)),
      el("td", {}, nombreTipo(h.tipo)),
      el("td", {}, celdaValor(h)),
      el("td", {}, el("span", { class: `badge risk-${h.riesgo}` }, h.riesgo)),
      el("td", {}, `${h.nivel_confianza} · ${h.confianza}%`),
      el("td", { class: "muted" }, h.contexto || "—"),
      el("td", {}, celdaRevision(h))))
    : [el("tr", {}, el("td", { colspan: 7, class: "vacio" }, "Sin hallazgos con estos filtros"))]));

  const paginas = Math.max(1, Math.ceil(datos.total / datos.por_pagina));
  paginar(datos.pagina, paginas, `${datos.total.toLocaleString("es-CL")} hallazgos`);
}

function paginar(pagina, paginas, texto) {
  $("info-pagina").textContent = `${texto} · página ${pagina} de ${paginas}`;
  $("anterior").disabled = pagina <= 1;
  $("siguiente").disabled = pagina >= paginas;
}

function marcarVista() {
  for (const b of document.querySelectorAll(".vistas button")) b.setAttribute("aria-pressed", String(b.dataset.vista === vista));
  $("vista-tipos").hidden = vista !== "tipos";
  $("vista-detalle").hidden = vista !== "detalle";
}

// --- Exportar (CSV, JSON, PDF) con los mismos filtros de la pantalla, siempre enmascarado ------------
const FORMATOS = [
  ["csv", "CSV", "Para abrir en Excel"],
  ["json", "JSON", "Para otros sistemas (por ejemplo un DLP)"],
  ["pdf", "PDF", "Reporte para compartir"],
];
const enlacesExportar = FORMATOS.map(([formato, nombre, texto]) =>
  el("a", { role: "menuitem", download: "", "data-formato": formato },
    icono("bajar"), el("span", {}, el("strong", {}, nombre), el("small", { class: "muted" }, texto))));
const notaExportar = el("p", { class: "nota" });
$("exportar-boton").prepend(icono("bajar"));
$("exportar-menu").append(notaExportar, ...enlacesExportar);
document.addEventListener("click", (ev) => { if (!$("exportar").contains(ev.target)) $("exportar").open = false; });
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") $("exportar").open = false; });
for (const a of enlacesExportar) a.addEventListener("click", () => { $("exportar").open = false; });

function actualizarExportar() {
  const { riesgo, tipo, buscar, revision } = filtros;
  const textoRevision = Object.fromEntries(FILTROS_REVISION)[revision]?.toLowerCase();
  const activos = [riesgo && `riesgo ${riesgo}`, tipo && nombreTipo(tipo), buscar && `«${buscar}»`, textoRevision].filter(Boolean);
  notaExportar.textContent = activos.length
    ? `Con los filtros actuales: ${activos.join(" · ")}. Siempre enmascarado.`
    : `Los ${plural(detalle.total, "hallazgo")}, siempre enmascarados.`;
  for (const a of enlacesExportar) {
    const q = new URLSearchParams({ formato: a.dataset.formato, riesgo, tipo, buscar, revision, desfase: new Date().getTimezoneOffset() });
    a.href = `/api/escaneos/${id}/exportar?${q}`;
  }
}

async function recargar() {
  marcarVista();
  marcarOrden();
  actualizarExportar();
  pintarRevision(resumenRevision);  // marca el estado elegido en el recuadro de revisión
  await (vista === "tipos" ? cargarTipos() : cargarDetalle());
}

for (const b of document.querySelectorAll(".vistas button")) {
  b.addEventListener("click", () => {
    if (b.dataset.vista === vista) return;
    vista = b.dataset.vista;
    filtros.pagina = 1;
    try { localStorage.setItem(CLAVE_VISTA, vista); } catch { /* sin almacenamiento: no se recuerda */ }
    recargar();
  });
}

$("filtro-riesgo").addEventListener("change", (e) => { filtros.riesgo = e.target.value; filtros.pagina = 1; marcarKpi(); recargar(); });
$("filtro-tipo").addEventListener("change", (e) => { filtros.tipo = e.target.value; filtros.pagina = 1; recargar(); });
$("filtro-revision").addEventListener("change", (e) => { filtros.revision = e.target.value; filtros.pagina = 1; recargar(); });
let espera;
$("filtro-buscar").addEventListener("input", (e) => {
  clearTimeout(espera);
  espera = setTimeout(() => { filtros.buscar = e.target.value.trim(); filtros.pagina = 1; recargar(); }, 300);
});
$("anterior").addEventListener("click", () => { filtros.pagina--; recargar(); });
$("siguiente").addEventListener("click", () => { filtros.pagina++; recargar(); });

recargar();
