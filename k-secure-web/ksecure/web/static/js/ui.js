// Piezas de interfaz compartidas: sesión, encabezado, íconos, diálogos, avisos y animaciones.
import { api } from "./api.js";

// --- Sesión: quién está conectado y qué puede hacer ------------------------------------
// Visor < Auditor < Admin: cada rol puede todo lo del anterior (igual que en el servidor).
export const ROLES = { Visor: 1, Auditor: 2, Admin: 3 };
export const estadoSesion = await api("/sesion").catch(() => ({ configurado: true, usuario: null, largo_minimo: 10 }));
export const usuario = estadoSesion.usuario;
export const puede = (rol) => (ROLES[usuario?.rol] || 0) >= ROLES[rol];

// Crea un elemento. Los textos van con textContent, nunca como HTML: así un dato
// sacado de un archivo del usuario no puede inyectar código en la página.
export function el(tag, attrs = {}, ...hijos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  e.append(...hijos.flat().filter((h) => h != null && h !== false));
  return e;
}

// Íconos SVG propios (constantes nuestras, por eso pueden ir como HTML).
const ICONOS = {
  archivo: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  bd: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  subir: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  flecha: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  flechaIzq: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  ojo: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  ojoNo: '<path d="M3 3l18 18M10.6 5.1A10.4 10.4 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.2 4.1M6.6 6.6A16.6 16.6 0 0 0 2 12s3.6 7 10 7a9.6 9.6 0 0 0 5.4-1.6"/>',
  basura: '<path d="M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>',
  candado: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  escudo: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  lupa: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  mascara: '<path d="M4 12h3l2-3 3 6 2-3h6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/>',
  historial: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  lapiz: '<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M14 6l4 4"/>',
  mas: '<path d="M12 5v14M5 12h14"/>',
  check: '<path d="M5 12l5 5 9-10"/>',
  reglas: '<path d="M4 6h10M4 12h16M4 18h7"/><circle cx="17" cy="6" r="2"/><circle cx="14" cy="18" r="2"/>',
  salir: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l5-5-5-5M15 12H4"/>',
  usuarios: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 20a6.5 6.5 0 0 0-2.6-5.2"/>',
  llave: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M14.5 8.5l2 2"/>',
  copiar: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  encender: '<path d="M12 3v9"/><path d="M6.3 7.3a8 8 0 1 0 11.4 0"/>',
  correo: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
};

export function icono(nombre) {
  const span = document.createElement("span");
  span.style.display = "contents";
  span.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONOS[nombre]}</svg>`;
  return span.firstChild;
}

// --- Encabezado y pie (iguales en todas las páginas) -------------------------
// Cada página con el rol mínimo que la puede abrir (el servidor también lo revisa).
const PAGINAS = [
  ["inicio", "/", "Inicio", "Visor"],
  ["archivos", "/archivos.html", "Archivos", "Auditor"],
  ["base-datos", "/base-datos.html", "Base de datos", "Auditor"],
  ["historial", "/historial.html", "Historial", "Visor"],
  ["reglas", "/reglas.html", "Reglas", "Visor"],
  ["usuarios", "/usuarios.html", "Usuarios", "Admin"],
];

function montarLayout() {
  const actual = document.body.dataset.pagina;
  document.getElementById("site-header")?.replaceChildren(
    el("div", { class: "container" },
      el("a", { href: "/", class: "brand", "aria-label": "K-Secure, inicio" },
        el("img", { src: "/img/logo.webp", alt: "K-Secure", width: 99, height: 40 })),
      el("nav", { class: "nav", "aria-label": "Principal" },
        PAGINAS.filter(([, , , rol]) => puede(rol)).map(([id, href, texto]) =>
          el("a", { href, "aria-current": id === actual ? "page" : false }, texto))),
      usuario && menuCuenta()));
  document.getElementById("site-footer")?.replaceChildren(
    el("div", { class: "container" },
      "K-Secure · Detección de datos sensibles chilenos · Los datos se muestran siempre enmascarados"));
}

const iniciales = (nombre) => nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();

function menuCuenta() {
  const menu = el("details", { class: "menu-cuenta" },
    el("summary", { "aria-label": `Cuenta de ${usuario.nombre}` },
      el("span", { class: "avatar", "aria-hidden": "true" }, iniciales(usuario.nombre)),
      el("span", { class: "quien" }, el("strong", {}, usuario.nombre), el("small", {}, usuario.rol))),
    el("div", { class: "menu", role: "menu" },
      el("div", { class: "datos" },
        el("strong", {}, usuario.nombre),
        el("span", { class: "muted" }, usuario.correo || `@${usuario.usuario}`),
        el("span", { class: `badge rol-${usuario.rol}` }, usuario.rol)),
      el("button", { type: "button", role: "menuitem", onclick: () => { menu.open = false; cambiarClave(); } },
        icono("candado"), "Cambiar contraseña"),
      el("button", { type: "button", role: "menuitem", onclick: salir }, icono("salir"), "Cerrar sesión")));
  document.addEventListener("click", (ev) => { if (!menu.contains(ev.target)) menu.open = false; });
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") menu.open = false; });
  return menu;
}

export async function salir() {
  await api("/sesion/salir", { method: "POST" }).catch(() => {});
  location.href = "/login.html";
}

function cambiarClave() {
  return dialogo(
    "Cambiar contraseña",
    `Mínimo ${estadoSesion.largo_minimo} caracteres. Se cerrarán tus sesiones en otros navegadores.`,
    [campoClave("actual", "Contraseña actual", "current-password"),
      campoClave("nueva", "Contraseña nueva", "new-password"),
      campoClave("repetir", "Repite la contraseña nueva", "new-password")],
    "Cambiar contraseña",
    async (form) => {
      const { actual, nueva, repetir } = Object.fromEntries(new FormData(form));
      if (nueva !== repetir) throw new Error("Las contraseñas nuevas no coinciden");
      await api("/sesion/cambiar-clave", { method: "POST", json: { actual, nueva } });
      aviso("Contraseña actualizada");
    });
}

// Luz que sigue al mouse dentro de las tarjetas .card-hover.
function seguirMouse() {
  document.addEventListener("pointermove", (ev) => {
    const card = ev.target.closest?.(".card-hover");
    if (!card) return;
    const r = card.getBoundingClientRect();
    card.style.setProperty("--x", `${ev.clientX - r.left}px`);
    card.style.setProperty("--y", `${ev.clientY - r.top}px`);
  });
}

// --- Avisos ----------------------------------------------------------------
export function aviso(mensaje, tipo = "info") {
  document.querySelector(".toast")?.remove();
  const t = el("div", { class: `toast ${tipo}`, role: tipo === "error" ? "alert" : "status" }, mensaje);
  document.body.append(t);
  setTimeout(() => t.remove(), 4500);
}

// --- Pantalla "escaneando" ---------------------------------------------------
export function mostrarEscaneando(texto) {
  const capa = el("div", { class: "escaneando", role: "status" },
    el("div", {},
      el("div", { class: "radar" }, el("img", { src: "/img/escudo.webp", alt: "" })),
      el("h2", {}, "Escaneando…"),
      el("p", { class: "muted" }, texto)));
  document.body.append(capa);
  return () => capa.remove();
}

// --- Diálogos con formulario (clave de auditor, contraseñas, cuentas) -----------
export function dialogo(titulo, texto, campos, textoBoton, alEnviar, { iconoNombre = "candado", clase = "", sinCancelar = false } = {}) {
  return new Promise((resolve) => {
    const error = el("p", { class: "error-form", "aria-live": "polite" });
    const boton = el("button", { class: "btn btn-primary", type: "submit" }, textoBoton);
    const form = el("form", { method: "dialog" },
      el("div", { class: "icon-badge" }, icono(iconoNombre)),
      el("h2", {}, titulo), texto ? el("p", { class: "muted" }, texto) : null,
      campos, error,
      el("div", { class: "acciones" },
        sinCancelar ? null : el("button", { class: "btn", type: "button", onclick: () => d.close() }, "Cancelar"), boton));
    const d = el("dialog", { class: clase }, form);
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      boton.disabled = true;
      try {
        const resultado = await alEnviar(form);
        d.close();
        resolve(resultado);
      } catch (e) {
        error.textContent = e.message;
      } finally {
        boton.disabled = false;
      }
    });
    d.addEventListener("close", () => { d.remove(); resolve(null); });
    document.body.append(d);
    d.showModal();
  });
}

export const campoClave = (name, texto, autocomplete) => el("div", { class: "campo" },
  el("label", { for: name }, texto),
  el("input", { id: name, name, type: "password", required: true, autocomplete }));

export const campoTexto = (name, texto, { type = "text", value = "", autocomplete = "off", required = true,
  readonly = false, ayuda = "" } = {}) => el("div", { class: "campo" },
  el("label", { for: name }, texto),
  el("input", { id: name, name, type, value, autocomplete, required, readonly, spellcheck: "false" }),
  ayuda ? el("p", { class: "ayuda-campo" }, ayuda) : null);

// Se llama antes de escanear: si todavía no hay clave de auditor, pide crearla.
export async function asegurarClaveAuditor() {
  const estado = await api("/auditor");
  if (estado.configurada) return true;
  if (!puede("Admin")) {
    aviso("Todavía no hay clave de auditor. Pide a un administrador que la cree en Usuarios.", "error");
    return false;
  }
  return dialogo(
    "Crea la clave de auditor",
    `Los datos originales se guardan cifrados con esta clave. Sin ella nadie puede verlos, así que guárdala bien. Mínimo ${estado.largo_minimo} caracteres.`,
    [campoClave("clave", "Clave", "new-password"), campoClave("confirmar", "Repite la clave", "new-password")],
    "Crear clave",
    async (form) => {
      const { clave, confirmar } = Object.fromEntries(new FormData(form));
      if (clave !== confirmar) throw new Error("Las claves no coinciden");
      await api("/auditor", { method: "POST", json: { clave } });
      aviso("Clave de auditor creada");
      return true;
    });
}

// Pide la clave y devuelve el dato original, o null si se cancela.
export function revelarHallazgo(id) {
  return dialogo(
    "Ver dato original",
    "Ingresa la clave de auditor. El dato se mostrará por 20 segundos.",
    [campoClave("clave", "Clave de auditor", "current-password")],
    "Ver dato",
    async (form) => (await api(`/hallazgos/${id}/revelar`, {
      method: "POST", json: { clave: new FormData(form).get("clave") } })).valor);
}

// Reemplaza al confirm() del navegador con un diálogo del mismo estilo que el de la clave de auditor.
// Devuelve true si se confirma; Cancelar, Escape o un clic fuera del diálogo devuelven false.
export function confirmar({ titulo, texto, detalle, textoBoton = "Confirmar", peligro = false }) {
  return new Promise((resolve) => {
    let aceptado = false;
    const cancelar = el("button", { class: "btn", type: "button", onclick: () => d.close() }, "Cancelar");
    const aceptar = el("button", {
      class: `btn ${peligro ? "btn-peligro" : "btn-primary"}`, type: "button",
      onclick: () => { aceptado = true; d.close(); },
    }, peligro ? icono("basura") : null, textoBoton);
    const d = el("dialog", { class: "confirmar", "aria-labelledby": "confirmar-titulo", "aria-describedby": "confirmar-texto" },
      el("div", { class: `icon-badge${peligro ? " peligro" : ""}` }, icono(peligro ? "basura" : "info")),
      el("h2", { id: "confirmar-titulo" }, titulo),
      detalle ? el("p", { class: "detalle" }, detalle) : null,
      el("p", { class: "muted", id: "confirmar-texto" }, texto),
      el("div", { class: "acciones" }, cancelar, aceptar));
    d.addEventListener("click", (ev) => {  // clic en el fondo oscuro, fuera del cuadro
      if (ev.target !== d) return;
      const r = d.getBoundingClientRect();
      if (ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) d.close();
    });
    d.addEventListener("close", () => { d.remove(); resolve(aceptado); });
    document.body.append(d);
    d.showModal();
    cancelar.focus();  // en una acción que borra, un Enter apurado no debe borrar
  });
}

// "1 hallazgo" / "1.234 hallazgos"
export const plural = (n, singular, varios = `${singular}s`) =>
  `${Number(n).toLocaleString("es-CL")} ${n === 1 ? singular : varios}`;

// --- Utilidades --------------------------------------------------------------
export function contarHasta(nodo, final, ms = 900) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    nodo.textContent = final.toLocaleString("es-CL");
    return;
  }
  const inicio = performance.now();
  const paso = (t) => {
    const p = Math.min(1, (t - inicio) / ms);
    nodo.textContent = Math.round(final * (1 - (1 - p) ** 3)).toLocaleString("es-CL");
    if (p < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

export const formatoFecha = (iso) => new Date(iso).toLocaleString("es-CL", { dateStyle: "medium", timeStyle: "short" });

montarLayout();
seguirMouse();
