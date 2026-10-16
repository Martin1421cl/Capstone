import { api } from "./api.js";
import { tarjetaEscaneo } from "./tarjetas.js";
import { aviso, el, icono } from "./ui.js";

const lista = document.getElementById("lista");

function vacio() {
  return el("div", { class: "card vacio" },
    el("div", { class: "icon-badge" }, icono("historial")),
    el("h3", {}, "Todavía no hay escaneos"),
    el("p", {}, "Empieza escaneando archivos o conectando una base de datos."),
    el("div", { class: "hero-actions", style: "justify-content:center" },
      el("a", { class: "btn btn-primary", href: "/archivos.html" }, "Escanear archivos"),
      el("a", { class: "btn", href: "/base-datos.html" }, "Conectar base de datos")));
}

async function cargar() {
  const escaneos = await api("/escaneos");
  lista.replaceChildren(...(escaneos.length
    ? escaneos.map((e) => tarjetaEscaneo(e, {
      alBorrar: async () => {
        if (!confirm(`¿Borrar "${e.origen_nombre}" y todos sus hallazgos?`)) return;
        await api(`/escaneos/${e.id}`, { method: "DELETE" });
        aviso("Escaneo borrado");
        cargar();
      },
    }))
    : [vacio()]));
}

cargar();
