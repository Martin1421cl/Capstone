import { RIESGOS, api, nombreTipo } from "./api.js";
import { aviso, contarHasta, el, formatoFecha, icono, revelarHallazgo } from "./ui.js";

const $ = (id) => document.getElementById(id);
const id = new URLSearchParams(location.search).get("id");
const SEGUNDOS_VISIBLE = 20;
const filtros = { riesgo: "", tipo: "", buscar: "", pagina: 1 };

let detalle;
try {
  detalle = await api(`/escaneos/${id}`);
} catch {
  $("titulo").textContent = "Escaneo no encontrado";
  document.querySelectorAll(".section, #kpis").forEach((s) => s.remove());
  throw new Error("escaneo no encontrado");
}

// --- Encabezado ------------------------------------------------------------------
document.title = `${detalle.origen_nombre} · K-Secure`;
$("titulo").textContent = detalle.origen_nombre;
$("meta").textContent = `${detalle.origen_tipo === "bd" ? "Base de datos" : "Archivos"} · ${formatoFecha(detalle.fecha)}`;
$("borrar").hidden = false;
$("borrar").addEventListener("click", async () => {
  if (!confirm("¿Borrar este escaneo y todos sus hallazgos?")) return;
  await api(`/escaneos/${id}`, { method: "DELETE" });
  location.href = "/historial.html";
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
      onclick: () => { $("filtro-buscar").value = c.columna; filtros.buscar = c.columna; recargar(); $("hallazgos").scrollIntoView({ behavior: "smooth", block: "center" }); },
    },
      el("div", { class: "fuente" }, c.fuente),
      el("div", { class: "nombre" }, c.columna),
      el("div", { class: "pie" }, el("span", {}, nombreTipo(c.tipo)), el("span", { class: "badge" }, c.riesgo)),
      el("div", { class: "barra", style: "margin-top:12px" }, barra),
      el("div", { class: "muted", style: "font-size:.82rem;margin-top:6px" },
        `${c.porcentaje}% de las filas (${c.filas_con_datos.toLocaleString("es-CL")})`));
  }));
}

// --- Errores ----------------------------------------------------------------------------
if (detalle.errores.length) {
  $("sec-errores").hidden = false;
  $("errores").append(...detalle.errores.map((e) => el("li", {}, e)));
}

// --- Tabla de hallazgos -------------------------------------------------------------------
RIESGOS.forEach((r) => $("filtro-riesgo").append(el("option", { value: r.id }, r.id)));
Object.keys(detalle.por_tipo).forEach((t) => $("filtro-tipo").append(el("option", { value: t }, nombreTipo(t))));

function celdaValor(h) {
  const texto = el("span", {}, h.valor);
  const boton = el("button", { class: "btn btn-icon btn-sm", type: "button", "aria-label": "Ver dato original" }, icono("ojo"));
  const celda = el("span", { class: "valor" }, texto, boton);
  boton.addEventListener("click", async () => {
    try {
      const original = await revelarHallazgo(h.id);
      if (original == null) return;
      texto.textContent = original;
      celda.classList.add("revelado");
      boton.replaceChildren(icono("ojoNo"));
      setTimeout(() => {
        texto.textContent = h.valor;
        celda.classList.remove("revelado");
        boton.replaceChildren(icono("ojo"));
      }, SEGUNDOS_VISIBLE * 1000);
    } catch (e) {
      aviso(e.message, "error");
    }
  });
  return celda;
}

async function recargar() {
  const q = new URLSearchParams({ ...filtros, por_pagina: 50 });
  const datos = await api(`/escaneos/${id}/hallazgos?${q}`);
  $("hallazgos").replaceChildren(...(datos.items.length
    ? datos.items.map((h, i) => el("tr", { style: `animation-delay:${Math.min(i, 15) * 25}ms` },
      el("td", {}, el("div", {}, h.columna ? `${h.fuente}.${h.columna}` : h.fuente),
        el("div", { class: "muted", style: "font-size:.8rem" }, h.posicion)),
      el("td", {}, nombreTipo(h.tipo)),
      el("td", {}, celdaValor(h)),
      el("td", {}, el("span", { class: `badge risk-${h.riesgo}` }, h.riesgo)),
      el("td", {}, `${h.nivel_confianza} · ${h.confianza}%`),
      el("td", { class: "muted" }, h.contexto || "—")))
    : [el("tr", {}, el("td", { colspan: 6, class: "vacio" }, "Sin hallazgos con estos filtros"))]));

  const paginas = Math.max(1, Math.ceil(datos.total / datos.por_pagina));
  $("info-pagina").textContent = `${datos.total.toLocaleString("es-CL")} hallazgos · página ${datos.pagina} de ${paginas}`;
  $("anterior").disabled = datos.pagina <= 1;
  $("siguiente").disabled = datos.pagina >= paginas;
}

$("filtro-riesgo").addEventListener("change", (e) => { filtros.riesgo = e.target.value; filtros.pagina = 1; marcarKpi(); recargar(); });
$("filtro-tipo").addEventListener("change", (e) => { filtros.tipo = e.target.value; filtros.pagina = 1; recargar(); });
let espera;
$("filtro-buscar").addEventListener("input", (e) => {
  clearTimeout(espera);
  espera = setTimeout(() => { filtros.buscar = e.target.value.trim(); filtros.pagina = 1; recargar(); }, 300);
});
$("anterior").addEventListener("click", () => { filtros.pagina--; recargar(); });
$("siguiente").addEventListener("click", () => { filtros.pagina++; recargar(); });

recargar();
