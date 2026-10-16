import { RIESGOS, api, nombreTipo } from "./api.js";
import { aviso, el, icono } from "./ui.js";

const $ = (id) => document.getElementById(id);
const VALIDACIONES = {
  ninguna: "Ninguna (solo el patrón)",
  modulo11: "Módulo 11 (dígito verificador, como el RUT)",
  luhn: "Luhn (como las tarjetas)",
};
const EJEMPLOS = [
  { nombre: "PASAPORTE", descripcion: "Pasaporte chileno", patron: "\\b[A-Z]\\d{8}\\b", palabras_positivas: ["pasaporte"], riesgo: "Restringido" },
  { nombre: "FICHA_CLINICA", descripcion: "N° de ficha clínica", patron: "\\bFC-?\\d{6,8}\\b", palabras_positivas: ["ficha", "paciente"], riesgo: "Restringido" },
  { nombre: "NUMERO_SOCIO", descripcion: "N° de socio de la empresa", patron: "\\bSOC\\d{5}\\b", palabras_positivas: ["socio"], riesgo: "Confidencial" },
  { nombre: "IP_PRIVADA", descripcion: "Direcciones IP internas", patron: "\\b(?:10|192\\.168)(?:\\.\\d{1,3}){2,3}\\b", riesgo: "Interno" },
];
const REGLA_VACIA = { nombre: "", descripcion: "", patron: "", validacion: "ninguna", palabras_positivas: [], palabras_negativas: [],
  requiere_contexto: false, confianza: 70, riesgo: "Confidencial", visibles: 4, activa: true };

const aLista = (texto) => texto.split(",").map((p) => p.trim()).filter(Boolean);
const deLista = (lista) => (lista || []).join(", ");

function interruptor(marcado, etiqueta, alCambiar) {
  const input = el("input", { type: "checkbox", checked: marcado, "aria-label": etiqueta });
  input.addEventListener("change", () => alCambiar(input.checked));
  return el("label", { class: "switch" }, input, el("span", { class: "pista" }), el("span", { class: "muted" }, marcado ? "Activa" : "Apagada"));
}

// --- Validadores incluidos ----------------------------------------------------------
function tarjetaIncluido(v) {
  const guardar = (cambios) => api(`/reglas/incluidas/${v.nombre}`, {
    method: "PUT", json: { activo: v.activo, palabras_positivas: v.palabras_positivas, palabras_negativas: v.palabras_negativas, ...cambios },
  }).then(cargar).catch((e) => aviso(e.message, "error"));

  return el("article", { class: `card card-hover regla-card ${v.activo ? "" : "apagada"}` },
    el("div", { class: "cabecera" },
      el("h3", {}, nombreTipo(v.nombre)),
      interruptor(v.activo, `Activar ${v.nombre}`, (activo) => guardar({ activo }))),
    el("p", { class: "muted", style: "margin:0" }, v.descripcion),
    v.palabras_base.length > 0 && el("div", { class: "palabras" },
      "Contexto: ", v.palabras_base.slice(0, 8).join(", "), v.palabras_base.length > 8 ? "…" : ""),
    v.palabras_positivas.length > 0 && el("div", { class: "palabras" }, el("strong", {}, "+ "), deLista(v.palabras_positivas)),
    v.palabras_negativas.length > 0 && el("div", { class: "palabras" }, el("strong", {}, "− "), deLista(v.palabras_negativas)),
    el("div", { class: "acciones" },
      el("button", { class: "btn btn-sm", type: "button", onclick: () => editarPalabras(v, guardar) }, icono("lapiz"), "Palabras de contexto")));
}

function editarPalabras(v, guardar) {
  const pos = el("input", { id: "pos", value: deLista(v.palabras_positivas), placeholder: "afiliado, socio" });
  const neg = el("input", { id: "neg", value: deLista(v.palabras_negativas), placeholder: "folio, código" });
  const d = el("dialog", {}, el("form", { method: "dialog", onsubmit: async (e) => {
    e.preventDefault();
    await guardar({ palabras_positivas: aLista(pos.value), palabras_negativas: aLista(neg.value) });
    d.close();
  } },
    el("h2", {}, `Contexto de ${nombreTipo(v.nombre)}`),
    el("p", { class: "muted" }, "Separa las palabras con comas. Se suman a las que el validador ya trae."),
    el("div", { class: "campo" }, el("label", { for: "pos" }, "Palabras que suben la confianza"), pos),
    el("div", { class: "campo" }, el("label", { for: "neg" }, "Palabras que la bajan"), neg),
    el("div", { class: "acciones" },
      el("button", { class: "btn", type: "button", onclick: () => d.close() }, "Cancelar"),
      el("button", { class: "btn btn-primary", type: "submit" }, "Guardar"))));
  d.addEventListener("close", () => d.remove());
  document.body.append(d);
  d.showModal();
}

// --- Reglas personalizadas -----------------------------------------------------------
function tarjetaRegla(r) {
  const guardar = (cambios) => api(`/reglas/${r.id}`, { method: "PUT", json: { ...r, ...cambios } })
    .then(cargar).catch((e) => aviso(e.message, "error"));
  return el("article", { class: `card card-hover regla-card risk-${r.riesgo} ${r.activa ? "" : "apagada"}` },
    el("div", { class: "cabecera" },
      el("div", {}, el("h3", {}, r.nombre), el("span", { class: "muted", style: "font-size:.88rem" }, r.descripcion)),
      interruptor(r.activa, `Activar ${r.nombre}`, (activa) => guardar({ activa }))),
    el("code", {}, r.patron),
    el("div", { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center" },
      el("span", { class: "badge" }, r.riesgo),
      el("span", { class: "palabras" }, `${r.confianza}% · ${VALIDACIONES[r.validacion].split(" (")[0]}`)),
    r.palabras_positivas.length > 0 && el("div", { class: "palabras" }, "Contexto: ", deLista(r.palabras_positivas)),
    el("div", { class: "acciones" },
      el("button", { class: "btn btn-sm", type: "button", onclick: () => abrirEditor(r) }, icono("lapiz"), "Editar"),
      el("button", { class: "btn btn-sm btn-danger", type: "button", onclick: async () => {
        if (!confirm(`¿Borrar la regla ${r.nombre}? Los escaneos anteriores no cambian.`)) return;
        await api(`/reglas/${r.id}`, { method: "DELETE" });
        aviso("Regla borrada");
        cargar();
      } }, icono("basura"), "Borrar")));
}

// --- Editor con prueba en vivo ---------------------------------------------------------
function campo(etiqueta, control, ayuda) {
  return el("div", { class: "campo" }, el("label", { for: control.id }, etiqueta), control,
    ayuda && el("div", { class: "muted", style: "font-size:.8rem;margin-top:4px" }, ayuda));
}

function abrirEditor(regla = REGLA_VACIA) {
  const f = {
    nombre: el("input", { id: "f-nombre", required: true, value: regla.nombre, placeholder: "PASAPORTE", autocomplete: "off" }),
    descripcion: el("input", { id: "f-descripcion", value: regla.descripcion, placeholder: "Para qué sirve la regla" }),
    patron: el("input", { id: "f-patron", required: true, value: regla.patron, placeholder: "\\b[A-Z]\\d{8}\\b", spellcheck: "false", style: "font-family:ui-monospace,monospace" }),
    validacion: el("select", { id: "f-validacion" }, Object.entries(VALIDACIONES).map(([k, t]) => el("option", { value: k, selected: k === regla.validacion }, t))),
    riesgo: el("select", { id: "f-riesgo" }, RIESGOS.map((r) => el("option", { value: r.id, selected: r.id === regla.riesgo }, r.id))),
    confianza: el("input", { id: "f-confianza", type: "range", min: 0, max: 100, step: 5, value: regla.confianza }),
    visibles: el("input", { id: "f-visibles", type: "number", min: 0, max: 20, value: regla.visibles }),
    positivas: el("input", { id: "f-positivas", value: deLista(regla.palabras_positivas), placeholder: "pasaporte, viaje" }),
    negativas: el("input", { id: "f-negativas", value: deLista(regla.palabras_negativas), placeholder: "folio, código" }),
    contexto: el("input", { id: "f-contexto", type: "checkbox", checked: regla.requiere_contexto }),
  };
  const valorConfianza = el("strong", {}, `${regla.confianza}%`);
  const texto = el("textarea", { id: "f-texto", rows: 7, placeholder: "Pega aquí un texto de ejemplo…" },
    "Pasaporte del cliente: F12345678\nFolio interno A00000001");
  const resultados = el("ul", { class: "prueba-resultados", "aria-live": "polite" });
  const error = el("p", { class: "error-form", "aria-live": "polite" });

  const datos = () => ({
    nombre: f.nombre.value.trim().toUpperCase(), descripcion: f.descripcion.value, patron: f.patron.value,
    validacion: f.validacion.value, riesgo: f.riesgo.value, confianza: Number(f.confianza.value),
    visibles: Number(f.visibles.value), palabras_positivas: aLista(f.positivas.value),
    palabras_negativas: aLista(f.negativas.value), requiere_contexto: f.contexto.checked, activa: regla.activa,
  });

  let espera;
  const probar = () => {
    clearTimeout(espera);
    espera = setTimeout(async () => {
      if (!f.patron.value) return resultados.replaceChildren(el("li", { class: "muted" }, "Escribe un patrón para probarlo."));
      try {
        // El nombre puede estar vacío mientras se escribe: para probar basta uno provisorio.
        const encontrados = await api("/reglas/probar", { method: "POST", json: { regla: { ...datos(), nombre: datos().nombre || "PRUEBA" }, texto: texto.value } });
        error.textContent = "";
        resultados.replaceChildren(...(encontrados.length
          ? encontrados.map((m) => el("li", {},
            el("div", {}, el("code", {}, m.texto), " → ", el("code", {}, m.enmascarado)),
            el("div", { class: "muted" }, `línea ${m.linea} · ${m.nivel} ${m.confianza}% · ${m.riesgo}`,
              m.contexto.length ? ` · contexto: ${m.contexto.join(", ")}` : "",
              m.validacion_ok ? "" : " · no pasó la validación")))
          : [el("li", { class: "muted" }, "Sin coincidencias en el texto de ejemplo.")]));
      } catch (e) {
        error.textContent = e.message;
        resultados.replaceChildren();
      }
    }, 300);
  };

  const ejemplos = el("div", { class: "ejemplos" }, el("span", { class: "muted", style: "font-size:.78rem" }, "Ejemplos:"),
    EJEMPLOS.map((ej) => el("button", { type: "button", onclick: () => {
      f.nombre.value = ej.nombre; f.descripcion.value = ej.descripcion; f.patron.value = ej.patron;
      f.positivas.value = deLista(ej.palabras_positivas); f.riesgo.value = ej.riesgo;
      probar();
    } }, ej.descripcion)));

  const form = el("form", { method: "dialog" },
    el("h2", {}, regla.id ? `Editar ${regla.nombre}` : "Nueva regla"),
    regla.id ? null : ejemplos,
    el("div", { class: "editor" },
      el("div", {},
        el("div", { class: "form-grid" }, campo("Nombre", f.nombre, "MAYÚSCULAS, ej. FICHA_CLINICA"), campo("Descripción", f.descripcion)),
        campo("Patrón (expresión regular)", f.patron, "\\d = dígito, [A-Z] = letra, {8} = 8 veces, \\b = borde de palabra"),
        el("div", { class: "form-grid" }, campo("Validación extra", f.validacion), campo("Riesgo", f.riesgo)),
        el("div", { class: "form-grid" },
          el("div", { class: "campo" }, el("label", { for: "f-confianza" }, "Confianza base: ", valorConfianza), f.confianza),
          campo("Caracteres visibles al enmascarar", f.visibles)),
        campo("Palabras que suben la confianza", f.positivas, "Separadas por coma. También cuenta el nombre de la columna."),
        campo("Palabras que la bajan", f.negativas),
        el("label", { class: "switch", style: "margin-bottom:8px" }, f.contexto, el("span", { class: "pista" }), "Reportar solo si hay una palabra de contexto cerca")),
      el("div", {},
        campo("Probar con un texto", texto),
        resultados)),
    error,
    el("div", { class: "acciones" },
      el("button", { class: "btn", type: "button", onclick: () => d.close() }, "Cancelar"),
      el("button", { class: "btn btn-primary", type: "submit" }, "Guardar regla")));

  form.addEventListener("input", (e) => {
    if (e.target === f.confianza) valorConfianza.textContent = `${f.confianza.value}%`;
    probar();
  });
  form.addEventListener("change", probar);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api(regla.id ? `/reglas/${regla.id}` : "/reglas", { method: regla.id ? "PUT" : "POST", json: datos() });
      d.close();
      aviso(regla.id ? "Regla actualizada" : "Regla creada: se usará desde el próximo escaneo");
      cargar();
    } catch (err) {
      error.textContent = err.message;
    }
  });

  const d = el("dialog", { class: "ancho" }, form);
  d.addEventListener("close", () => d.remove());
  document.body.append(d);
  d.showModal();
  probar();
}

// --- Carga ---------------------------------------------------------------------------
async function cargar() {
  const { incluidos, personalizadas } = await api("/reglas");
  $("incluidos").replaceChildren(...incluidos.map(tarjetaIncluido));
  $("personalizadas").replaceChildren(...(personalizadas.length
    ? personalizadas.map(tarjetaRegla)
    : [el("div", { class: "card vacio", style: "grid-column:1/-1" },
      el("div", { class: "icon-badge" }, icono("reglas")),
      el("h3", {}, "Todavía no hay reglas personalizadas"),
      el("p", { style: "margin:0" }, "Crea una para detectar un dato nuevo: pasaportes, fichas clínicas, N° de socio…"))]));
}

$("nueva").append(icono("mas"), "Nueva regla");
$("nueva").addEventListener("click", () => abrirEditor());
cargar();
