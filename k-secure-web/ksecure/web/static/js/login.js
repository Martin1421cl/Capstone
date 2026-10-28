// Ingreso a K-Secure. La misma página sirve para tres momentos:
// 1) configurar: K-Secure recién instalado, se crea la cuenta de administrador;
// 2) ingresar: usuario y contraseña;
// 3) cambiar: la cuenta tiene una contraseña temporal y debe crear la suya.
import { api } from "./api.js";
import { campoClave, campoTexto, el, estadoSesion, icono, salir } from "./ui.js";

const contenido = document.getElementById("contenido");
const params = new URLSearchParams(location.search);
const minimo = estadoSesion.largo_minimo;

// A dónde volver después de ingresar: solo rutas de esta misma web.
const volver = (() => {
  const v = params.get("volver") || "/";
  return v.startsWith("/") && !v.startsWith("//") && !v.startsWith("/login.html") ? v : "/";
})();

function formulario({ titulo, texto, campos, boton, alEnviar, extra = null, nota = null }) {
  const error = el("p", { class: "error-form", role: "alert" });
  const enviar = el("button", { class: "btn btn-primary btn-ancho", type: "submit" }, boton);
  const form = el("form", { novalidate: false },
    el("h1", {}, titulo),
    texto ? el("p", { class: "muted" }, texto) : null,
    nota,
    campos, error, enviar, extra);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    error.textContent = "";
    enviar.disabled = true;
    try {
      await alEnviar(Object.fromEntries(new FormData(form)));
    } catch (e) {
      error.textContent = e.message;
      enviar.disabled = false;
    }
  });
  contenido.replaceChildren(form);
  form.querySelector("input:not([readonly])")?.focus();
}

const ayudaClave = `Mínimo ${minimo} caracteres. Mejor una frase que una palabra.`;

function claveNueva(datos) {
  if (datos.clave !== datos.repetir) throw new Error("Las contraseñas no coinciden");
  if (datos.clave.length < minimo) throw new Error(`La contraseña debe tener al menos ${minimo} caracteres`);
}

function configurar() {
  formulario({
    titulo: "Configura K-Secure",
    texto: "Crea la cuenta de administrador. Desde la página Usuarios crearás después las cuentas del equipo: no hay registro público.",
    campos: [
      campoTexto("nombre", "Tu nombre", { autocomplete: "name" }),
      campoTexto("usuario", "Usuario", { autocomplete: "username", ayuda: "Con él ingresas. Letras, números, punto o guion." }),
      campoTexto("correo", "Correo", { type: "email", autocomplete: "email", ayuda: "Para recuperar la contraseña." }),
      campoClave("clave", "Contraseña", "new-password"),
      campoClave("repetir", "Repite la contraseña", "new-password"),
      el("p", { class: "ayuda-campo", style: "margin-top:-8px" }, ayudaClave),
    ],
    boton: "Crear cuenta de administrador",
    alEnviar: async (datos) => {
      claveNueva(datos);
      await api("/sesion/configurar", { method: "POST", json: datos });
      location.replace("/");
    },
  });
}

function ingresar() {
  const avisoSesion = params.get("motivo") === "sesion"
    ? el("div", { class: "forma" }, icono("info"), el("span", {}, "Tu sesión se cerró. Vuelve a ingresar para continuar."))
    : null;
  formulario({
    titulo: "Ingresar",
    texto: null,
    nota: avisoSesion,
    campos: [
      campoTexto("usuario", "Usuario", { autocomplete: "username" }),
      campoClave("clave", "Contraseña", "current-password"),
    ],
    boton: "Ingresar",
    alEnviar: async (datos) => {
      const { usuario } = await api("/sesion/ingresar", { method: "POST", json: datos });
      if (usuario.debe_cambiar_clave) cambiar(usuario);
      else location.replace(volver);
    },
    extra: el("p", { class: "muted login-ayuda" },
      "¿Olvidaste tu contraseña? Pide a un administrador que la restablezca."),
  });
}

function cambiar(cuenta) {
  formulario({
    titulo: "Crea tu contraseña",
    texto: `Hola, ${cuenta.nombre.split(" ")[0]}. Estás usando una contraseña temporal: crea una propia para continuar.`,
    campos: [
      cuenta.correo ? null : campoTexto("correo", "Tu correo", {
        type: "email", autocomplete: "email", ayuda: "Lo usarás para recuperar la contraseña." }),
      campoClave("clave", "Contraseña nueva", "new-password"),
      campoClave("repetir", "Repite la contraseña", "new-password"),
      el("p", { class: "ayuda-campo", style: "margin-top:-8px" }, ayudaClave),
    ],
    boton: "Guardar y continuar",
    alEnviar: async (datos) => {
      claveNueva(datos);
      await api("/sesion/cambiar-clave", { method: "POST", json: { nueva: datos.clave, correo: datos.correo } });
      location.replace(volver);
    },
    extra: el("p", { class: "muted login-ayuda" },
      `Conectado como @${cuenta.usuario}. `,
      el("button", { type: "button", class: "enlace", onclick: salir }, "Usar otra cuenta")),
  });
}

if (!estadoSesion.configurado) configurar();
else if (estadoSesion.usuario?.debe_cambiar_clave) cambiar(estadoSesion.usuario);
else if (estadoSesion.usuario) location.replace(volver);
else ingresar();
