// HU-17: comparar dos escaneos de la misma fuente (qué aumentó, qué disminuyó, qué apareció y qué ya no está).
import { RIESGOS, api, nombreTipo } from "./api.js";
import { aviso, el, formatoFecha, icono, plural } from "./ui.js";

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);

// "+3" en rojo si aumentaron los datos sensibles, "−3" en verde si disminuyeron.
function diferencia(n) {
  if (!n) return el("span", { class: "dif dif-igual" }, "sin cambio");
  return el("span", { class: `dif ${n > 0 ? "dif-sube" : "dif-baja"}` }, `${n > 0 ? "+" : "−"}${Math.abs(n)}`);
}

const opcion = (e) => el("option", { value: e.id }, `#${e.id} · ${e.origen_nombre} · ${formatoFecha(e.fecha)}`);

function tabla(columnas, filas) {
  return el("div", { class: "tabla-wrap" },
    el("table", {},
      el("thead", {}, el("tr", {}, columnas.map((c) => el("th", { scope: "col" }, c)))),
      el("tbody", {}, filas)));
}

function tarjetaRiesgo(r, fila) {
  return el("div", { class: `card kpi kpi-comparar risk-${r.id} entrar` },
    el("div", { class: "kpi-nombre" }, r.id),
    el("div", { class: "valor" }, String(fila.actual)),
    el("p", { class: "descripcion" }, `antes ${fila.anterior} · `, diferencia(fila.diferencia)));
}

const ESTADO_COLUMNA = { nueva: "Nueva", ya_no_esta: "Ya no está", sigue: "Sigue" };
const porcentaje = (p) => (p == null ? "—" : `${p} %`);

function listaHallazgos(titulo, explicacion, datos) {
  const filas = datos.muestra.map((h) => el("tr", {},
    el("td", { "data-label": "Dónde" }, h.columna ? `${h.fuente} › ${h.columna}` : h.fuente, el("br"),
      el("small", { class: "muted" }, h.posicion)),
    el("td", { "data-label": "Tipo" }, nombreTipo(h.tipo)),
    el("td", { "data-label": "Dato" }, el("span", { class: "valor" }, h.valor)),
    el("td", { "data-label": "Riesgo" }, el("span", { class: `badge risk-${h.riesgo}` }, h.riesgo))));
  return el("section", { class: "section" },
    el("div", { class: "section-title" },
      el("h2", {}, `${titulo} (${datos.total})`),
      el("p", { class: "muted", style: "margin:0" }, datos.total > datos.muestra.length
        ? `${explicacion} Se muestran los ${datos.muestra.length} de mayor riesgo.` : explicacion)),
    datos.total ? tabla(["Dónde", "Tipo", "Dato", "Riesgo"], filas)
      : el("div", { class: "card vacio" }, el("p", {}, "Ninguno.")));
}

function mostrar(c) {
  const { anterior, actual } = c;
  $("resultado").replaceChildren(...[
    !c.misma_fuente && el("div", { class: "aviso", style: "margin-top:20px" }, icono("info"),
      el("div", {}, "Estos escaneos no son de la misma fuente (", el("strong", {}, anterior.origen_nombre), " y ",
        el("strong", {}, actual.origen_nombre), "): las diferencias pueden no significar mucho.")),

    el("div", { class: "card entrar resumen-comparar", style: "margin-top:20px" },
      el("div", {}, el("small", { class: "muted" }, "Anterior"),
        el("div", {}, el("a", { href: `/resultados.html?id=${anterior.id}` }, `#${anterior.id}`), ` · ${formatoFecha(anterior.fecha)}`),
        el("strong", {}, plural(c.total.anterior, "hallazgo"))),
      el("div", { class: "flecha-comparar", "aria-hidden": "true" }, icono("flecha")),
      el("div", {}, el("small", { class: "muted" }, "Actual"),
        el("div", {}, el("a", { href: `/resultados.html?id=${actual.id}` }, `#${actual.id}`), ` · ${formatoFecha(actual.fecha)}`),
        el("strong", {}, plural(c.total.actual, "hallazgo"))),
      el("div", { class: "total-comparar" }, diferencia(c.total.diferencia),
        el("small", { class: "muted" }, `${c.nuevos.total} nuevos · ${c.resueltos.total} ya no están · ${c.sin_cambios} iguales`))),

    el("div", { class: "grid grid-4", style: "margin-top:20px" },
      RIESGOS.map((r) => tarjetaRiesgo(r, c.por_riesgo.find((f) => f.clave === r.id)))),

    el("div", { class: "grid grid-2 section", style: "margin-top:24px" },
      el("div", { class: "card" }, el("h2", {}, "Por tipo de dato"),
        c.por_tipo.length ? tabla(["Tipo", "Antes", "Ahora", "Cambio"], c.por_tipo.map((t) => el("tr", {},
          el("td", {}, nombreTipo(t.clave)), el("td", {}, String(t.anterior)), el("td", {}, String(t.actual)),
          el("td", {}, diferencia(t.diferencia)))))
          : el("p", { class: "muted" }, "Ninguno de los dos escaneos tiene hallazgos.")),
      el("div", { class: "card" }, el("h2", {}, "Columnas sensibles"),
        c.columnas.length ? tabla(["Columna", "Antes", "Ahora", ""], c.columnas.map((col) => el("tr", {},
          el("td", {}, el("strong", {}, col.columna), el("br"),
            el("small", { class: "muted" }, `${col.fuente} · ${nombreTipo(col.tipo)}`)),
          el("td", {}, porcentaje(col.anterior)), el("td", {}, porcentaje(col.actual)),
          el("td", {}, el("span", { class: `badge estado-${col.estado}` }, ESTADO_COLUMNA[col.estado])))))
          : el("p", { class: "muted" }, "Solo los escaneos de tablas y planillas tienen columnas."))),

    listaHallazgos("Nuevos", "Datos que aparecen en el escaneo actual y no estaban antes.", c.nuevos),
    listaHallazgos("Ya no están", "Datos del escaneo anterior que ya no aparecen.", c.resueltos),
    el("p", { class: "muted", style: "margin-top:24px;font-size:.85rem" },
      "Se compara por ubicación y valor enmascarado: dos datos distintos con la misma máscara en la misma fila ",
      "cuentan como el mismo."),
  ].filter(Boolean));
}

async function comparar(a, b) {
  if (!a || !b) return;
  if (a === b) { aviso("Elige dos escaneos distintos", "error"); return; }
  history.replaceState(null, "", `?a=${a}&b=${b}`);
  try {
    mostrar(await api(`/escaneos/${a}/comparar/${b}`));
  } catch (err) {
    aviso(err.message, "error");
  }
}

const escaneos = await api("/escaneos");  // del más reciente al más antiguo
if (escaneos.length < 2) {
  $("elegir").hidden = true;
  $("resultado").replaceChildren(el("div", { class: "card vacio", style: "margin-top:20px" },
    el("div", { class: "icon-badge" }, icono("historial")),
    el("h3", {}, "Se necesitan al menos dos escaneos"),
    el("p", {}, "Vuelve a escanear la misma fuente más adelante para ver qué cambió.")));
} else {
  $("sel-a").replaceChildren(...escaneos.map(opcion));
  $("sel-b").replaceChildren(...escaneos.map(opcion));
  // Por defecto: lo que venga en la dirección, o el último escaneo y el anterior de la misma fuente.
  const ultimo = escaneos[0];
  const previo = escaneos.slice(1).find((e) => e.origen_nombre === ultimo.origen_nombre) || escaneos[1];
  $("sel-a").value = params.get("a") || previo.id;
  $("sel-b").value = params.get("b") || ultimo.id;
  $("elegir").addEventListener("submit", (ev) => {
    ev.preventDefault();
    comparar($("sel-a").value, $("sel-b").value);
  });
  comparar($("sel-a").value, $("sel-b").value);
}
