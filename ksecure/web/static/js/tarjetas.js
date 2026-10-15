// Tarjeta de un escaneo, usada en Inicio (últimos) y en Historial.
import { RIESGOS } from "./api.js";
import { el, formatoFecha, icono } from "./ui.js";

export function tarjetaEscaneo(e, { alBorrar } = {}) {
  const barras = el("div", { class: "mini-barras", "aria-hidden": "true" },
    RIESGOS.map((r) => el("span", {
      class: `risk-${r.id}`,
      style: `width:${e.total ? (100 * e.por_riesgo[r.id]) / e.total : 0}%`,
    })));
  const resumen = RIESGOS.filter((r) => e.por_riesgo[r.id]).map((r) => `${e.por_riesgo[r.id]} ${r.id.toLowerCase()}`);

  return el("article", { class: "card card-hover escaneo-card entrar" },
    el("div", { class: "icon-badge" }, icono(e.origen_tipo === "bd" ? "bd" : "archivo")),
    el("div", {},
      el("h3", {}, el("a", { href: `/resultados.html?id=${e.id}` }, e.origen_nombre)),
      el("div", { class: "meta" }, `${formatoFecha(e.fecha)} · ${resumen.join(" · ") || "sin hallazgos"}`),
      el("div", { style: "margin-top:10px;max-width:420px" }, barras)),
    el("div", { style: "display:flex;gap:14px;align-items:center" },
      el("div", { class: "total" }, String(e.total), el("small", {}, "hallazgos")),
      alBorrar && el("button", {
        class: "btn btn-danger btn-icon", type: "button", "aria-label": `Borrar ${e.origen_nombre}`,
        onclick: alBorrar,
      }, icono("basura"))));
}
