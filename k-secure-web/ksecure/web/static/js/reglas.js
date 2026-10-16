import { RIESGOS, api, nombreTipo } from "./api.js";
import { aviso, el, icono } from "./ui.js";

const $ = (id) => document.getElementById(id);

// Opciones en palabras; por dentro son los parámetros del validador.
const VALIDACIONES = [
  { id: "ninguna", titulo: "No", texto: "Basta con que tenga la forma de los ejemplos." },
  { id: "modulo11", titulo: "Dígito verificador", texto: "El último carácter se calcula como en el RUT (Módulo 11)." },
  { id: "luhn", titulo: "Número de tarjeta", texto: "Se valida como las tarjetas de crédito (Luhn)." },
];
const CERTEZAS = [
  { valor: 90, titulo: "Muy seguro", texto: "Algo con esta forma casi siempre es este dato." },
  { valor: 70, titulo: "Probable", texto: "Suele serlo, pero a veces es otra cosa." },
  { valor: 45, titulo: "Dudoso", texto: "Se parece a otros números o códigos." },
];
const NIVELES = { HIGH: "alta", MEDIUM: "media", LOW: "baja" };
const PLANTILLAS = [
  { nombre: "Pasaporte", ejemplos: ["F12345678", "P98765432"], palabras_positivas: ["pasaporte"], riesgo: "Restringido" },
  { nombre: "Ficha clínica", ejemplos: ["FC-123456", "FC-9876543"], palabras_positivas: ["ficha", "paciente"], riesgo: "Restringido" },
  { nombre: "N° de socio", ejemplos: ["SOC00123", "SOC99812"], palabras_positivas: ["socio"], riesgo: "Confidencial" },
  { nombre: "Código de empleado", ejemplos: ["EMP-0042", "EMP-1290"], palabras_positivas: ["empleado", "trabajador"], riesgo: "Interno" },
];
const NUEVA = { nombre: "", descripcion: "", ejemplos: [], patron: "", validacion: "ninguna", palabras_positivas: [],
  palabras_negativas: [], requiere_contexto: false, confianza: 70, riesgo: "Confidencial", visibles: 4, activa: true };

const tituloRegla = (r) => r.descripcion || r.nombre;
const certeza = (n) => CERTEZAS.reduce((a, b) => (Math.abs(b.valor - n) < Math.abs(a.valor - n) ? b : a));

// "Ficha clínica" -> "FICHA_CLINICA": el nombre técnico que aparece en los resultados.
function nombreTecnico(texto) {
  const base = texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 45);
  return /^[A-Z]/.test(base) ? base : base && `DATO_${base}`;
}

// Igual que mask_keep_last en Python: oculta todo salvo los últimos caracteres.
function enmascarar(texto, visibles) {
  const total = [...texto].filter((c) => /[\p{L}\p{N}]/u.test(c)).length;
  let vistos = 0;
  return [...texto].map((c) => {
    if (!/[\p{L}\p{N}]/u.test(c)) return c;
    vistos += 1;
    return vistos > total - visibles ? c : "*";
  }).join("");
}

// --- Piezas de formulario --------------------------------------------------------------
// Palabras como etiquetas: se escriben y se agregan con Enter o coma.
function campoEtiquetas(id, iniciales, placeholder, alCambiar = () => {}) {
  const palabras = [...iniciales];
  const input = el("input", { id, placeholder, autocomplete: "off" });
  const caja = el("div", { class: "etiquetas", onclick: () => input.focus() });
  const pintar = () => {
    caja.replaceChildren(...palabras.map((p, i) => el("span", { class: "etiqueta" }, p,
      el("button", { type: "button", "aria-label": `Quitar ${p}`, onclick: () => { palabras.splice(i, 1); pintar(); alCambiar(); } }, icono("x")))), input);
  };
  const agregar = () => {
    for (const p of input.value.split(",").map((x) => x.trim().toLowerCase()).filter(Boolean)) {
      if (!palabras.includes(p)) palabras.push(p);
    }
    input.value = "";
    pintar();
    alCambiar();
    input.focus();
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); agregar(); }
    if (e.key === "Backspace" && !input.value && palabras.length) { palabras.pop(); pintar(); alCambiar(); input.focus(); }
  });
  input.addEventListener("blur", () => input.value.trim() && agregar());
  pintar();
  return { nodo: caja, valores: () => [...palabras] };
}

function grupoOpciones(nombre, opciones, actual, alCambiar = () => {}) {
  return el("div", { class: "opciones", role: "radiogroup" }, opciones.map((o) =>
    el("label", { class: `opcion ${o.clase || ""}` },
      el("input", { type: "radio", name: nombre, value: o.valor, checked: String(o.valor) === String(actual), onchange: alCambiar }),
      el("strong", {}, o.titulo), el("span", {}, o.texto))));
}

const elegido = (form, nombre) => form.querySelector(`input[name="${nombre}"]:checked`)?.value;

function interruptor(marcado, etiqueta, alCambiar) {
  const input = el("input", { type: "checkbox", checked: marcado, "aria-label": etiqueta });
  input.addEventListener("change", () => alCambiar(input.checked));
  return el("label", { class: "switch" }, input, el("span", { class: "pista" }), el("span", { class: "muted" }, marcado ? "Activa" : "Apagada"));
}

// --- Asistente para crear o editar una regla ------------------------------------------
function abrirAsistente(regla = NUEVA) {
  let paso = 1;
  let patronManual = Boolean(regla.id) && !(regla.ejemplos || []).length;  // reglas antiguas: patrón escrito a mano
  let patronGenerado = regla.patron;

  // Paso 1: qué dato
  const nombre = el("input", { id: "a-nombre", value: tituloRegla(regla), placeholder: "Ej: Pasaporte", autocomplete: "off" });
  const tecnico = el("div", { class: "nombre-tecnico" });
  const positivas = campoEtiquetas("a-positivas", regla.palabras_positivas, "Escribe una palabra y presiona Enter");
  const plantillas = el("div", { class: "ejemplos" }, el("span", { class: "muted", style: "font-size:.78rem" }, "O parte de un ejemplo:"),
    PLANTILLAS.map((p) => el("button", { type: "button", onclick: () => usarPlantilla(p) }, p.nombre)));

  // Paso 2: cómo se ve
  const ejemplos = [0, 1, 2].map((i) => el("input", {
    id: `a-ejemplo-${i}`, value: (regla.ejemplos || [])[i] || "", autocomplete: "off", spellcheck: "false",
    placeholder: ["Ej: F12345678", "Otro ejemplo (opcional)", "Otro más (opcional)"][i], style: "font-family:ui-monospace,monospace",
  }));
  const forma = el("div", { class: "forma", "aria-live": "polite" });
  const patron = el("input", { id: "a-patron", value: regla.patron, spellcheck: "false", style: "font-family:ui-monospace,monospace" });
  const regenerar = el("button", { class: "btn btn-sm", type: "button" }, "Volver a usar los ejemplos");

  // Paso 3: riesgo y prueba
  const visibles = el("input", { id: "a-visibles", type: "range", min: 0, max: 8, value: Math.min(regla.visibles, 8) });
  const vistaPrevia = el("span", { class: "vista-previa" });
  const soloConContexto = el("input", { type: "checkbox", checked: regla.requiere_contexto });
  const negativas = campoEtiquetas("a-negativas", regla.palabras_negativas, "Ej: folio, código");
  const texto = el("textarea", { id: "a-texto", rows: 4 });
  const resultados = el("ul", { class: "prueba-resultados", "aria-live": "polite" });
  const error = el("p", { class: "error-form", "aria-live": "polite" });

  const ejemplosEscritos = () => ejemplos.map((e) => e.value.trim()).filter(Boolean);

  function actualizarNombre() {
    const t = nombreTecnico(nombre.value);
    tecnico.replaceChildren(t ? "En los resultados aparecerá como " : "", t ? el("code", {}, t) : "");
  }

  let esperaPatron;
  function actualizarForma() {
    clearTimeout(esperaPatron);
    if (patronManual) {
      forma.className = "forma";
      forma.replaceChildren(icono("info"), el("span", {}, "Usando el patrón escrito a mano (ver Avanzado)."));
      return;
    }
    if (!ejemplosEscritos().length) {
      forma.className = "forma";
      forma.replaceChildren(icono("info"), el("span", {}, "Escribe un ejemplo y te muestro qué va a buscar K-Secure."));
      return;
    }
    esperaPatron = setTimeout(async () => {
      try {
        const r = await api("/reglas/patron", { method: "POST", json: { ejemplos: ejemplosEscritos() } });
        patronGenerado = r.patron;
        patron.value = r.patron;
        forma.className = "forma";
        forma.replaceChildren(icono("check"), el("span", {}, "K-Secure buscará: ", el("strong", {}, r.descripcion)));
      } catch (e) {
        forma.className = "forma error";
        forma.replaceChildren(icono("info"), el("span", {}, e.message));
      }
    }, 250);
  }

  function actualizarVistaPrevia() {
    vistaPrevia.textContent = enmascarar(ejemplosEscritos()[0] || "F12345678", Number(visibles.value));
  }

  function usarPlantilla(p) {
    nombre.value = p.nombre;
    ejemplos.forEach((e, i) => { e.value = p.ejemplos[i] || ""; });
    form.querySelector(`input[name="riesgo"][value="${p.riesgo}"]`).checked = true;
    const nueva = campoEtiquetas("a-positivas", p.palabras_positivas, "Escribe una palabra y presiona Enter");
    positivas.nodo.replaceWith(nueva.nodo);
    Object.assign(positivas, nueva);
    patronManual = false;
    actualizarNombre();
    actualizarForma();
  }

  const datos = () => ({
    nombre: nombreTecnico(nombre.value), descripcion: nombre.value.trim(), ejemplos: ejemplosEscritos(),
    patron: patron.value || patronGenerado, validacion: elegido(form, "validacion"), riesgo: elegido(form, "riesgo"),
    confianza: Number(elegido(form, "certeza")), visibles: Number(visibles.value),
    palabras_positivas: positivas.valores(), palabras_negativas: negativas.valores(),
    requiere_contexto: soloConContexto.checked, activa: regla.activa,
  });

  let esperaPrueba;
  function probar() {
    clearTimeout(esperaPrueba);
    esperaPrueba = setTimeout(async () => {
      try {
        const encontrados = await api("/reglas/probar", { method: "POST", json: { regla: { ...datos(), nombre: datos().nombre || "PRUEBA" }, texto: texto.value } });
        error.textContent = "";
        resultados.replaceChildren(...(encontrados.length
          ? encontrados.map((m) => el("li", {},
            el("div", {}, el("code", {}, m.texto), "  →  ", el("code", {}, m.enmascarado), "  ", el("span", { class: `badge risk-${m.riesgo}` }, m.riesgo)),
            el("div", { class: "muted" }, `Confianza ${NIVELES[m.nivel]} (${m.confianza}%)`,
              m.contexto.length ? ` · porque dice "${m.contexto.join('", "')}"` : "",
              m.validacion_ok ? "" : " · no pasó la validación")))
          : [el("li", { class: "muted" }, "No encontró nada en este texto. Prueba escribiendo uno de tus ejemplos.")]));
      } catch (e) {
        error.textContent = e.message;
      }
    }, 300);
  }

  // --- Pasos ---
  const stepper = el("ol", { class: "stepper" }, ["¿Qué dato?", "¿Cómo se ve?", "Riesgo y prueba"].map((t, i) => el("li", {}, el("span", {}, String(i + 1)), t)));
  const pasos = [
    el("section", { class: "paso" },
      regla.id ? null : plantillas,
      el("h3", { class: "paso-titulo" }, "¿Cómo se llama el dato que quieres detectar?"),
      nombre, tecnico,
      el("h3", { class: "paso-titulo" }, "¿Qué palabras suelen aparecer cerca?"),
      el("p", { class: "ayuda" }, "Si aparecen cerca del dato (o como nombre de la columna), K-Secure confía más en que lo encontró."),
      positivas.nodo),
    el("section", { class: "paso", hidden: true },
      el("h3", { class: "paso-titulo" }, "Escribe ejemplos del dato, tal como aparecen"),
      el("p", { class: "ayuda" }, "Con 2 ejemplos K-Secure entiende mejor: si una parte se repite igual (como «FC-»), la toma como fija."),
      el("div", { class: "grid", style: "gap:8px" }, ejemplos),
      forma,
      el("h3", { class: "paso-titulo" }, "¿Tiene alguna comprobación matemática?"),
      grupoOpciones("validacion", VALIDACIONES.map((v) => ({ valor: v.id, titulo: v.titulo, texto: v.texto })), regla.validacion),
      el("details", { class: "avanzado", open: patronManual },
        el("summary", {}, "Avanzado: escribir el patrón a mano (expresión regular)"),
        el("div", { class: "campo" }, el("label", { for: "a-patron" }, "Patrón"), patron),
        regenerar)),
    el("section", { class: "paso", hidden: true },
      el("h3", { class: "paso-titulo" }, "¿Qué tan grave sería que se filtre?"),
      grupoOpciones("riesgo", RIESGOS.map((r) => ({ valor: r.id, titulo: r.id, texto: r.descripcion, clase: `risk-${r.id}` })), regla.riesgo),
      el("h3", { class: "paso-titulo" }, "¿Qué tan seguro es que algo con esa forma sea este dato?"),
      grupoOpciones("certeza", CERTEZAS, certeza(regla.confianza).valor),
      el("h3", { class: "paso-titulo" }, "¿Cuánto se muestra en los resultados?"),
      el("div", { style: "display:flex;gap:16px;align-items:center;flex-wrap:wrap" },
        el("div", { style: "flex:1;min-width:200px" }, el("label", { for: "a-visibles" }, "Caracteres visibles al final"), visibles),
        vistaPrevia),
      el("details", { class: "avanzado" },
        el("summary", {}, "Más opciones"),
        el("label", { class: "switch", style: "margin:4px 0 14px" }, soloConContexto, el("span", { class: "pista" }), "Avisar solo si aparece una de las palabras de contexto"),
        el("div", { class: "campo" }, el("label", { for: "a-negativas" }, "Palabras que indican que NO es este dato"), negativas.nodo)),
      el("h3", { class: "paso-titulo" }, "Pruébala"),
      el("p", { class: "ayuda" }, "Pega un texto real o de ejemplo y mira qué encontraría."),
      texto, resultados),
  ];

  const atras = el("button", { class: "btn", type: "button" }, "← Atrás");
  const siguiente = el("button", { class: "btn btn-primary", type: "button" }, "Siguiente →");
  const guardar = el("button", { class: "btn btn-primary", type: "submit" }, icono("check"), "Guardar regla");

  function irA(n) {
    if (n > paso && paso === 1 && !nombreTecnico(nombre.value)) return (error.textContent = "Ponle un nombre al dato");
    if (n > paso && paso === 2 && !(patron.value || patronGenerado)) return (error.textContent = "Escribe al menos un ejemplo del dato");
    error.textContent = "";
    paso = n;
    pasos.forEach((p, i) => { p.hidden = i + 1 !== n; });
    [...stepper.children].forEach((li, i) => { li.classList.toggle("actual", i + 1 === n); li.classList.toggle("hecho", i + 1 < n); });
    atras.style.visibility = n === 1 ? "hidden" : "visible";
    siguiente.hidden = n === 3;
    guardar.hidden = n !== 3;
    if (n === 3) {
      const ej = ejemplosEscritos()[0] || "";
      if (!texto.value) texto.value = `${positivas.valores()[0] || "dato"}: ${ej}\nOtro texto sin el dato`;
      actualizarVistaPrevia();
      probar();
    }
  }

  const form = el("form", { class: "asistente", method: "dialog" },
    el("h2", {}, regla.id ? `Editar: ${tituloRegla(regla)}` : "Nueva regla"),
    stepper, ...pasos, error,
    el("div", { class: "pie" },
      atras,
      el("div", { style: "display:flex;gap:10px" },
        el("button", { class: "btn", type: "button", onclick: () => d.close() }, "Cancelar"), siguiente, guardar)));

  nombre.addEventListener("input", actualizarNombre);
  ejemplos.forEach((e) => e.addEventListener("input", () => { actualizarForma(); actualizarVistaPrevia(); }));
  patron.addEventListener("input", () => { patronManual = true; actualizarForma(); });
  regenerar.addEventListener("click", () => { patronManual = false; actualizarForma(); });
  visibles.addEventListener("input", actualizarVistaPrevia);
  form.addEventListener("input", () => paso === 3 && probar());
  form.addEventListener("change", () => paso === 3 && probar());
  atras.addEventListener("click", () => irA(paso - 1));
  siguiente.addEventListener("click", () => irA(paso + 1));
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
  actualizarNombre();
  actualizarForma();
  irA(1);
  d.showModal();
  nombre.focus();
}

// --- Tarjetas --------------------------------------------------------------------------
function tarjetaRegla(r) {
  const guardar = (cambios) => api(`/reglas/${r.id}`, { method: "PUT", json: { ...r, ...cambios } })
    .then(cargar).catch((e) => aviso(e.message, "error"));
  const validacion = VALIDACIONES.find((v) => v.id === r.validacion);
  return el("article", { class: `card card-hover regla-card risk-${r.riesgo} ${r.activa ? "" : "apagada"}` },
    el("div", { class: "cabecera" },
      el("div", {}, el("h3", {}, tituloRegla(r)), el("code", { style: "font-size:.75rem" }, r.nombre)),
      interruptor(r.activa, `Activar ${tituloRegla(r)}`, (activa) => guardar({ activa }))),
    el("div", { class: "palabras" }, r.ejemplos.length ? `Ej: ${r.ejemplos.join(" · ")}` : el("code", {}, r.patron)),
    el("div", { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center" },
      el("span", { class: "badge" }, r.riesgo),
      el("span", { class: "palabras" }, certeza(r.confianza).titulo, r.validacion !== "ninguna" ? ` · ${validacion.titulo.toLowerCase()}` : "")),
    r.palabras_positivas.length > 0 && el("div", { class: "palabras" }, "Palabras: ", r.palabras_positivas.join(", ")),
    el("div", { class: "acciones" },
      el("button", { class: "btn btn-sm", type: "button", onclick: () => abrirAsistente(r) }, icono("lapiz"), "Editar"),
      el("button", { class: "btn btn-sm btn-danger", type: "button", onclick: async () => {
        if (!confirm(`¿Borrar la regla "${tituloRegla(r)}"? Los escaneos anteriores no cambian.`)) return;
        await api(`/reglas/${r.id}`, { method: "DELETE" });
        aviso("Regla borrada");
        cargar();
      } }, icono("basura"), "Borrar")));
}

function tarjetaIncluido(v) {
  const guardar = (cambios) => api(`/reglas/incluidas/${v.nombre}`, {
    method: "PUT", json: { activo: v.activo, palabras_positivas: v.palabras_positivas, palabras_negativas: v.palabras_negativas, ...cambios },
  }).then(cargar).catch((e) => aviso(e.message, "error"));

  return el("article", { class: `card card-hover regla-card ${v.activo ? "" : "apagada"}` },
    el("div", { class: "cabecera" },
      el("h3", {}, nombreTipo(v.nombre)),
      interruptor(v.activo, `Activar ${nombreTipo(v.nombre)}`, (activo) => guardar({ activo }))),
    el("p", { class: "muted", style: "margin:0;font-size:.92rem" }, v.descripcion),
    v.palabras_positivas.length > 0 && el("div", { class: "palabras" }, "Tus palabras: ", v.palabras_positivas.join(", ")),
    el("div", { class: "acciones" },
      el("button", { class: "btn btn-sm", type: "button", onclick: () => editarPalabras(v, guardar) }, icono("lapiz"), "Palabras de contexto")));
}

function editarPalabras(v, guardar) {
  const suben = campoEtiquetas("p-suben", v.palabras_positivas, "Escribe una palabra y presiona Enter");
  const bajan = campoEtiquetas("p-bajan", v.palabras_negativas, "Ej: folio, código");
  const form = el("form", { method: "dialog" },
    el("h2", {}, `Palabras para ${nombreTipo(v.nombre)}`),
    el("p", { class: "muted" }, "Se suman a las que K-Secure ya trae. Sirven también como nombres de columna."),
    el("div", { class: "campo" }, el("label", { for: "p-suben" }, "Si aparecen cerca, confirman que es el dato"), suben.nodo),
    el("div", { class: "campo" }, el("label", { for: "p-bajan" }, "Si aparecen cerca, indican que NO lo es"), bajan.nodo),
    el("details", { class: "avanzado", style: "margin-bottom:16px" },
      el("summary", {}, "Ver las palabras que ya trae"),
      el("p", { class: "muted", style: "margin:0;font-size:.88rem" }, v.palabras_base.join(", ") || "Este validador no usa palabras de contexto.")),
    el("div", { class: "acciones" },
      el("button", { class: "btn", type: "button", onclick: () => d.close() }, "Cancelar"),
      el("button", { class: "btn btn-primary", type: "submit" }, "Guardar")));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await guardar({ palabras_positivas: suben.valores(), palabras_negativas: bajan.valores() });
    d.close();
  });
  const d = el("dialog", {}, form);
  d.addEventListener("close", () => d.remove());
  document.body.append(d);
  d.showModal();
}

// --- Carga -------------------------------------------------------------------------------
async function cargar() {
  const { incluidos, personalizadas } = await api("/reglas");
  $("incluidos").replaceChildren(...incluidos.map(tarjetaIncluido));
  $("personalizadas").replaceChildren(...(personalizadas.length
    ? personalizadas.map(tarjetaRegla)
    : [el("div", { class: "card vacio", style: "grid-column:1/-1" },
      el("div", { class: "icon-badge" }, icono("reglas")),
      el("h3", {}, "¿Necesitas detectar otro tipo de dato?"),
      el("p", {}, "Pasaportes, fichas clínicas, N° de socio… Solo escribe un par de ejemplos y K-Secure arma la regla."),
      el("button", { class: "btn btn-primary", type: "button", onclick: () => abrirAsistente() }, icono("mas"), "Crear mi primera regla"))]));
}

$("nueva").append(icono("mas"), "Nueva regla");
$("nueva").addEventListener("click", () => abrirAsistente());
cargar();
