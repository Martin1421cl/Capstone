// Ingreso a K-Secure. La misma página sirve para tres momentos:
// 1) configurar: K-Secure recién instalado, se crea la cuenta de administrador;
// 2) ingresar: usuario y contraseña;
// 3) cambiar: la cuenta tiene una contraseña temporal y debe crear la suya;
// 4) recuperar: ¿olvidaste tu contraseña? Llega un código de 6 dígitos al correo (RF-14).
import { api } from "./api.js";
import { aviso, campoClave, campoTexto, el, estadoSesion, icono, salir } from "./ui.js";

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
      el("button", { type: "button", class: "enlace", onclick: () => pedirCodigo() }, "¿Olvidaste tu contraseña?")),
  });
}

// --- ¿Olvidaste tu contraseña? ------------------------------------------------------------------

const ESPERA_REENVIO = 60;  // segundos, igual que en el servidor

const enlaceIngresar = () => el("button", { type: "button", class: "enlace", onclick: () => ingresar() }, "Volver a ingresar");

function pedirCodigo(cuenta = "") {
  formulario({
    titulo: "Recupera tu contraseña",
    texto: "Escribe tu usuario o tu correo. Te enviaremos un código de 6 dígitos al correo de tu cuenta.",
    campos: [campoTexto("cuenta", "Usuario o correo", { autocomplete: "username", value: cuenta })],
    boton: "Enviar código",
    alEnviar: async (datos) => {
      const { minutos } = await api("/sesion/recuperar", { method: "POST", json: { cuenta: datos.cuenta } });
      usarCodigo(datos.cuenta.trim(), minutos);
    },
    extra: el("p", { class: "muted login-ayuda" }, enlaceIngresar()),
  });
}

// "Enviar otro código", que se habilita pasado un minuto.
function botonReenviar(cuenta) {
  const boton = el("button", { type: "button", class: "enlace" });
  let quedan = ESPERA_REENVIO;
  let reloj;
  const pintar = () => {
    boton.disabled = quedan > 0;
    boton.textContent = quedan > 0 ? `Enviar otro código (${quedan} s)` : "Enviar otro código";
  };
  const contar = () => {
    quedan = ESPERA_REENVIO;
    pintar();
    clearInterval(reloj);
    reloj = setInterval(() => {
      quedan -= 1;
      pintar();
      if (quedan <= 0 || !boton.isConnected) clearInterval(reloj);
    }, 1000);
  };
  boton.addEventListener("click", async () => {
    boton.disabled = true;
    try {
      await api("/sesion/recuperar", { method: "POST", json: { cuenta } });
      aviso("Te enviamos un código nuevo. El anterior ya no sirve.");
      contar();
    } catch (e) {
      aviso(e.message, "error");
      boton.disabled = false;
    }
  });
  contar();
  return boton;
}

function campoCodigo() {
  const entrada = el("input", {
    id: "codigo", name: "codigo", class: "entrada-codigo", required: true, inputmode: "numeric",
    autocomplete: "one-time-code", pattern: "[0-9]{6}", title: "Los 6 números que llegaron al correo",
    spellcheck: "false", placeholder: "000000",
  });
  // Acepta "123 456" o "123-456" pegados desde el correo: deja solo los números.
  entrada.addEventListener("input", () => { entrada.value = entrada.value.replace(/\D/g, "").slice(0, 6); });
  return el("div", { class: "campo" }, el("label", { for: "codigo" }, "Código de 6 dígitos"), entrada);
}

function usarCodigo(cuenta, minutos = 10) {
  const dondeMirar = estadoSesion.correo
    ? el("span", {}, `Si la cuenta tiene un correo registrado, te llegó un código. Vence en ${minutos} minutos. `,
        "¿No lo ves? Revisa la carpeta de spam.")
    : el("span", {}, "Este K-Secure no tiene el envío de correos configurado: el código aparece en la terminal donde corre el servidor.");
  formulario({
    titulo: "Revisa tu correo",
    texto: null,
    nota: el("div", { class: "forma" }, icono("correo"), dondeMirar),
    campos: [
      campoCodigo(),
      campoClave("clave", "Contraseña nueva", "new-password"),
      campoClave("repetir", "Repite la contraseña", "new-password"),
      el("p", { class: "ayuda-campo", style: "margin-top:-8px" }, ayudaClave),
    ],
    boton: "Guardar contraseña y entrar",
    alEnviar: async (datos) => {
      claveNueva(datos);
      await api("/sesion/recuperar/confirmar", {
        method: "POST", json: { cuenta, codigo: datos.codigo, clave: datos.clave } });
      location.replace(volver);
    },
    extra: el("p", { class: "muted login-ayuda" }, botonReenviar(cuenta), el("br"), enlaceIngresar()),
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
