// Administración de cuentas (solo Admin): crear, editar rol, restablecer contraseña y desactivar.
import { api } from "./api.js";
import { asegurarClaveAuditor, aviso, campoTexto, confirmar, dialogo, el, estadoSesion, icono, usuario } from "./ui.js";

const fechaCorta = (iso) => new Date(iso).toLocaleString("es-CL", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

const $ = (id) => document.getElementById(id);

export const ROLES_INFO = [
  { id: "Admin", titulo: "Admin", resumen: "Administra K-Secure.", corto: "Todo, más cuentas, reglas y la clave de auditor.",
    puede: ["Todo lo del Auditor", "Crear y administrar cuentas", "Cambiar las reglas de detección", "Crear la clave de auditor"] },
  { id: "Auditor", titulo: "Auditor", resumen: "Revisa datos sensibles.", corto: "Escanea, ve originales con la clave y borra escaneos.",
    puede: ["Todo lo del Visor", "Escanear archivos y bases de datos", "Ver un original con la clave de auditor", "Borrar escaneos"] },
  { id: "Visor", titulo: "Visor", resumen: "Solo consulta.", corto: "Solo ve resultados enmascarados y las reglas.",
    puede: ["Ver resultados e historial, siempre enmascarados", "Ver las reglas de detección"] },
];

// --- Diálogos -------------------------------------------------------------------------------

function opcionesRol(actual) {
  return el("div", { class: "campo" },
    el("label", {}, "Rol"),
    el("div", { class: "opciones" }, ROLES_INFO.map((r) =>
      el("label", { class: `opcion rol-${r.id}` },
        el("input", { type: "radio", name: "rol", value: r.id, checked: r.id === actual, required: true }),
        el("strong", {}, r.titulo), el("span", {}, r.corto)))));
}

function mostrarClaveTemporal(cuenta, temporal, titulo) {
  const copiar = el("button", { class: "btn btn-sm", type: "button" }, icono("copiar"), "Copiar");
  copiar.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(temporal);
      copiar.replaceChildren(icono("check"), "Copiada");
    } catch {
      aviso("No se pudo copiar: selecciónala y cópiala a mano", "error");
    }
  });
  return dialogo(titulo, null, [
    el("p", {}, `Entrégale a ${cuenta.nombre} su usuario y esta contraseña temporal. `,
      el("strong", {}, "Se muestra solo esta vez"), ": al entrar deberá crear la suya."),
    el("div", { class: "clave-temporal" },
      el("div", { class: "dato" }, el("small", { class: "muted" }, "Usuario"), el("code", {}, cuenta.usuario)),
      el("div", { class: "dato" }, el("small", { class: "muted" }, "Contraseña temporal"),
        el("div", { class: "con-boton" }, el("code", { class: "grande" }, temporal), copiar))),
  ], "Listo", async () => {}, { iconoNombre: "llave", sinCancelar: true });
}

async function nuevaCuenta() {
  const creada = await dialogo("Nueva cuenta", "Se crea con una contraseña temporal que la persona cambia al entrar.", [
    campoTexto("nombre", "Nombre", { autocomplete: "off" }),
    campoTexto("usuario", "Usuario", { ayuda: "Con él ingresa. Letras, números, punto o guion." }),
    campoTexto("correo", "Correo", { type: "email", ayuda: "Para recuperar la contraseña." }),
    opcionesRol("Visor"),
  ], "Crear cuenta", async (form) => api("/usuarios", { method: "POST", json: Object.fromEntries(new FormData(form)) }),
  { iconoNombre: "usuarios", clase: "ancho-medio" });
  if (!creada) return;
  await mostrarClaveTemporal(creada.usuario, creada.clave_temporal, "Cuenta creada");  // primero mostrarla
  cargar();
}

async function editar(u) {
  const guardada = await dialogo(`Editar a ${u.nombre}`, `Usuario: @${u.usuario}`, [
    campoTexto("nombre", "Nombre", { value: u.nombre }),
    campoTexto("correo", "Correo", { type: "email", value: u.correo || "" }),
    u.id === usuario.id
      ? el("p", { class: "muted" }, "No puedes cambiar tu propio rol.")
      : opcionesRol(u.rol),
  ], "Guardar", async (form) => {
    const datos = Object.fromEntries(new FormData(form));
    return api(`/usuarios/${u.id}`, { method: "PUT", json: { ...datos, rol: datos.rol || u.rol, activo: u.activo } });
  }, { iconoNombre: "lapiz", clase: "ancho-medio" });
  if (guardada) { aviso("Cambios guardados"); cargar(); }
}

async function restablecer(u) {
  const ok = await confirmar({
    titulo: "¿Restablecer la contraseña?",
    detalle: `${u.nombre} · @${u.usuario}`,
    texto: "Se crea una contraseña temporal, se desbloquea la cuenta y se cierran sus sesiones abiertas.",
    textoBoton: "Restablecer",
  });
  if (!ok) return;
  try {
    const r = await api(`/usuarios/${u.id}/restablecer`, { method: "POST" });
    await mostrarClaveTemporal(r.usuario, r.clave_temporal, "Contraseña restablecida");  // primero mostrarla
    cargar();
  } catch (e) {
    aviso(e.message, "error");
  }
}

async function cambiarEstado(u) {
  if (u.activo) {
    const ok = await confirmar({
      titulo: "¿Desactivar esta cuenta?",
      detalle: `${u.nombre} · @${u.usuario}`,
      texto: "No podrá entrar y se cierran sus sesiones. Puedes volver a activarla cuando quieras.",
      textoBoton: "Desactivar",
      peligro: true,
    });
    if (!ok) return;
  }
  try {
    await api(`/usuarios/${u.id}`, { method: "PUT", json: { nombre: u.nombre, correo: u.correo || "", rol: u.rol, activo: !u.activo } });
    aviso(u.activo ? "Cuenta desactivada" : "Cuenta activada");
    cargar();
  } catch (e) {
    aviso(e.message, "error");
  }
}

// --- Tabla ------------------------------------------------------------------------------------

function estado(u) {
  if (!u.activo) return el("span", { class: "estado apagado" }, "Desactivada");
  if (u.bloqueado) return el("span", { class: "estado bloqueado", title: "5 contraseñas incorrectas seguidas. Restablecer la desbloquea." }, "Bloqueada");
  if (u.debe_cambiar_clave) return el("span", { class: "estado pendiente" }, "Clave temporal");
  return el("span", { class: "estado activo" }, "Activa");
}

function fila(u) {
  const soyYo = u.id === usuario.id;
  return el("tr", { class: u.activo ? "" : "inactiva" },
    el("td", { "data-label": "Persona" },
      el("div", { class: "persona" },
        el("span", { class: "avatar", "aria-hidden": "true" }, u.nombre.split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase()),
        el("div", {},
          el("strong", {}, u.nombre, soyYo ? el("span", { class: "muted" }, " (tú)") : null),
          el("div", { class: "muted" }, `@${u.usuario}`, u.correo ? ` · ${u.correo}` : "")))),
    el("td", { "data-label": "Rol" }, el("span", { class: `badge rol-${u.rol}` }, u.rol)),
    el("td", { "data-label": "Estado" }, estado(u)),
    el("td", { "data-label": "Último ingreso", class: "muted" }, u.ultimo_ingreso ? fechaCorta(u.ultimo_ingreso) : "Nunca"),
    el("td", { class: "acciones-fila" },
      el("button", { class: "btn btn-sm", type: "button", onclick: () => editar(u) }, icono("lapiz"), "Editar"),
      // Tu propia contraseña se cambia desde el menú con tu nombre (restablecerla cerraría tu sesión).
      soyYo ? null : el("button", { class: "btn btn-sm", type: "button", onclick: () => restablecer(u) }, icono("llave"), "Restablecer"),
      soyYo ? null : el("button", {
        class: `btn btn-sm ${u.activo ? "btn-danger" : ""}`, type: "button", onclick: () => cambiarEstado(u),
      }, icono("encender"), u.activo ? "Desactivar" : "Activar")));
}

async function cargar() {
  const cuentas = await api("/usuarios");
  $("lista").replaceChildren(...cuentas.map(fila));
}

async function pintarClaveAuditor() {
  const { configurada } = await api("/auditor");
  $("clave-auditor").replaceChildren(...[
    el("div", { class: `icon-badge ${configurada ? "" : "peligro"}` }, icono("llave")),
    el("div", {},
      el("h3", {}, configurada ? "Creada" : "Todavía no se crea"),
      el("p", { class: "muted", style: "margin:0" }, configurada
        ? "Protege los originales de todos los escaneos. Los Auditor la ingresan para ver un dato; no se guarda en ninguna parte y no se puede recuperar."
        : "Sin ella no se puede escanear: es la que cifra los datos originales. Créala y guárdala en un lugar seguro.")),
    configurada ? null : el("button", {
      class: "btn btn-primary", type: "button",
      onclick: async () => { if (await asegurarClaveAuditor()) pintarClaveAuditor(); },
    }, icono("llave"), "Crear clave de auditor")].filter(Boolean));
}

// ¿Olvidaste tu contraseña? manda un código al correo. Aquí se ve si el envío está listo y se prueba.
function pintarCorreo() {
  const listo = estadoSesion.correo;
  const probar = el("button", { class: "btn", type: "button" }, icono("correo"), "Enviar correo de prueba");
  probar.addEventListener("click", async () => {
    probar.disabled = true;
    try {
      const r = await api("/usuarios/correo-prueba", { method: "POST" });
      aviso(r.configurado ? `Correo enviado a ${r.para}. Revisa también el spam.` : "Sin envío configurado: el correo se escribió en la terminal del servidor.");
    } catch (e) {
      aviso(e.message, "error");
    } finally {
      probar.disabled = false;
    }
  });
  $("envio-correo").replaceChildren(
    el("div", { class: `icon-badge ${listo ? "" : "peligro"}` }, icono("correo")),
    el("div", {},
      el("h3", {}, listo ? "Configurado" : "Sin configurar"),
      el("p", { class: "muted", style: "margin:0" }, listo
        ? `Quien olvide su contraseña recibe un código de 6 dígitos en el correo de su cuenta. La prueba llega a ${usuario.correo || "tu correo"}.`
        : "Los códigos para recuperar la contraseña se escriben en la terminal del servidor en vez de enviarse. Para enviarlos, define KSECURE_CORREO_URL y KSECURE_CORREO_SECRETO (ver el README).")),
    probar);
}

$("roles").append(...ROLES_INFO.map((r) =>
  el("div", { class: `card rol-card rol-${r.id}` },
    el("span", { class: `badge rol-${r.id}` }, r.titulo),
    el("p", { class: "muted", style: "margin:10px 0 8px" }, r.resumen),
    el("ul", { class: "lista-check" }, r.puede.map((p) => el("li", {}, icono("check"), p))))));

$("nuevo").append(icono("mas"), "Nueva cuenta");
$("nuevo").addEventListener("click", nuevaCuenta);
cargar();
pintarClaveAuditor();
pintarCorreo();
