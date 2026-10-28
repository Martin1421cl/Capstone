// Bitácora (RF-17), solo Admin: quién hizo qué y cuándo. Solo lectura.
import { api } from "./api.js";
import { contarHasta, el, formatoFecha, icono } from "./ui.js";

const $ = (id) => document.getElementById(id);
const POR_PAGINA = 25;
const filtros = { categoria: "", persona: "", dias: "30", buscar: "", pagina: 1 };

// Color de cada categoría (las alertas siempre en rojo).
const CLASE = { "Alertas": "alertas", "Sesión": "sesion", "Cuentas": "cuentas", "Datos originales": "datos",
  "Escaneos": "escaneos", "Revisión": "revision", "Reglas": "reglas" };
const clase = (categoria) => `cat-${CLASE[categoria] || "sesion"}`;

// En 24 horas y con segundos: en una bitácora importa el orden exacto.
const fechaCorta = (iso) => new Date(iso).toLocaleString("es-CL", {
  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });

// --- Cifras de los últimos 7 días (al hacer clic filtran la tabla) ------------------------------
const TARJETAS = [
  { campo: "alertas", categoria: "Alertas", titulo: "Alertas", texto: "Contraseñas o claves de auditor incorrectas y bloqueos." },
  { campo: "datos_vistos", categoria: "Datos originales", titulo: "Datos originales vistos", texto: "Cada vez que alguien usó la clave de auditor." },
  { campo: "escaneos", categoria: "Escaneos", titulo: "Escaneos", texto: "Archivos y bases de datos revisados." },
  { campo: "ingresos", categoria: "Sesión", titulo: "Ingresos", texto: "Veces que alguien entró a K-Secure." },
];

const resumen = await api("/bitacora/resumen");
$("kpis").append(...TARJETAS.map((t) => {
  const valor = el("div", { class: "valor" }, "0");
  const tarjeta = el("button", {
    type: "button", class: `card card-hover kpi ${clase(t.categoria)} entrar`, "aria-pressed": "false",
    onclick: () => {
      const activa = filtros.categoria === t.categoria && filtros.dias === "7";
      filtros.categoria = activa ? "" : t.categoria;
      filtros.dias = activa ? "30" : "7";
      sincronizarControles();
      recargar();
    },
  }, el("div", { class: "etiqueta" }, t.titulo), valor, el("p", { class: "descripcion" }, t.texto));
  tarjeta.dataset.categoria = t.categoria;
  contarHasta(valor, resumen[t.campo]);
  return tarjeta;
}));

// --- Filtros --------------------------------------------------------------------------------------
$("filtro-categoria").append(...resumen.categorias.map((c) =>
  el("option", { value: c }, c === "Alertas" ? "Solo alertas" : c)));

const cuentas = await api("/usuarios");
$("filtro-persona").append(...cuentas.map((u) => el("option", { value: u.id }, `${u.nombre} (@${u.usuario})`)));

function sincronizarControles() {
  $("filtro-categoria").value = filtros.categoria;
  $("filtro-persona").value = filtros.persona;
  $("filtro-dias").value = filtros.dias;
  for (const t of $("kpis").children) {
    const activa = t.dataset.categoria === filtros.categoria && filtros.dias === "7";
    t.classList.toggle("activo", activa);
    t.setAttribute("aria-pressed", String(activa));
  }
}

for (const [id, campo] of [["filtro-categoria", "categoria"], ["filtro-persona", "persona"], ["filtro-dias", "dias"]]) {
  $(id).addEventListener("change", () => { filtros[campo] = $(id).value; sincronizarControles(); recargar(); });
}
let espera;
$("filtro-buscar").addEventListener("input", () => {
  clearTimeout(espera);
  espera = setTimeout(() => { filtros.buscar = $("filtro-buscar").value.trim(); recargar(); }, 300);
});

// --- Tabla ------------------------------------------------------------------------------------------
function quien(e) {
  if (!e.usuario) return el("span", { class: "muted" }, e.accion === "ingreso_desconocido" ? "Desconocido" : "Sistema");
  return el("div", {}, el("strong", {}, e.nombre), el("div", { class: "muted" }, `@${e.usuario}`));
}

function fila(e, i) {
  const verEscaneo = e.escaneo_id && e.accion !== "escaneo_borrado"
    ? [" · ", el("a", { href: `/resultados.html?id=${e.escaneo_id}` }, "ver escaneo")] : null;
  return el("tr", { class: e.alerta ? "alerta" : "", style: `animation-delay:${Math.min(i, 15) * 20}ms` },
    el("td", { "data-label": "Cuándo", title: formatoFecha(e.fecha) }, fechaCorta(e.fecha)),
    el("td", { "data-label": "Quién" }, quien(e)),
    el("td", { "data-label": "Qué pasó" },
      el("span", { class: `badge ${clase(e.alerta ? "Alertas" : e.categoria)}` }, e.titulo)),
    el("td", { "data-label": "Detalle", class: "detalle" }, e.detalle || "—", verEscaneo),
    el("td", { "data-label": "IP", class: "muted ip" }, e.ip || "—"));
}

function consulta(extra = {}) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries({ ...filtros, ...extra })) if (v !== "" && v != null) q.set(k, v);
  return q;
}

async function cargar() {
  const datos = await api(`/bitacora?${consulta({ por_pagina: POR_PAGINA })}`);
  $("eventos").replaceChildren(...(datos.eventos.length ? datos.eventos.map(fila)
    : [el("tr", {}, el("td", { colspan: 5, class: "vacio" }, "Sin eventos con estos filtros"))]));
  $("info-pagina").textContent = `${datos.total.toLocaleString("es-CL")} ${datos.total === 1 ? "evento" : "eventos"} · página ${datos.pagina} de ${datos.paginas}`;
  $("anterior").disabled = datos.pagina <= 1;
  $("siguiente").disabled = datos.pagina >= datos.paginas;
  // La descarga lleva los mismos filtros (sin la página) y la hora de este computador.
  $("descargar").href = `/api/bitacora/csv?${consulta({ pagina: "", desfase: new Date().getTimezoneOffset() })}`;
}

function recargar() {
  filtros.pagina = 1;
  cargar();
}

$("anterior").addEventListener("click", () => { filtros.pagina -= 1; cargar(); });
$("siguiente").addEventListener("click", () => { filtros.pagina += 1; cargar(); });
$("descargar").append(icono("bajar"), "Descargar CSV");

sincronizarControles();
cargar();
