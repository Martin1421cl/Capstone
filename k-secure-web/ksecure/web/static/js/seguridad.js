// Página Seguridad: cómo protege K-Secure los datos (enmascarar, cifrar y hashear). Para todos los roles.
import { api, nombreTipo } from "./api.js";
import { el, icono } from "./ui.js";

const $ = (id) => document.getElementById(id);

// --- El recorrido de un dato ------------------------------------------------------------------
const RECORRIDO = [
  ["lupa", "Se encuentra", "Un RUT en clientes.csv, columna rut."],
  ["mascara", "Se enmascara", "En pantalla solo se ve **.***.198-5, también para el Visor."],
  ["candado", "Se cifra", "El original se guarda cifrado en la bóveda, nunca en claro."],
  ["llave", "Se revela con clave", "Un Auditor lo ve 20 segundos con la clave de auditor."],
  ["historial", "Queda anotado", "La bitácora registra quién lo vio y cuándo, sin guardar el dato."],
];
$("recorrido").append(...RECORRIDO.map(([ic, titulo, texto], i) =>
  el("li", { class: "card entrar", style: `animation-delay:${i * 70}ms` },
    el("span", { class: "numero" }, String(i + 1)),
    el("div", { class: "icon-badge" }, icono(ic)),
    el("h3", {}, titulo), el("p", { class: "muted" }, texto))));

// --- Las tres técnicas -------------------------------------------------------------------------
const TECNICAS = [
  { ic: "mascara", titulo: "Enmascarar", clase: "tec-mascara", resumen: "Oculta parte del dato para poder mostrarlo.",
    ejemplo: "**.***.198-5", reversible: "No guarda el resto: lo oculto no se recupera desde aquí.",
    uso: "Lo que ves en Resultados y en la bitácora." },
  { ic: "candado", titulo: "Cifrar", clase: "tec-cifrado", resumen: "Lo vuelve ilegible, pero se puede recuperar con la llave.",
    ejemplo: "gAAAAABn3x…Q9vR", reversible: "Reversible, solo con la llave correcta.",
    uso: "Guardar el original para que un Auditor lo vea con la clave de auditor." },
  { ic: "escudo", titulo: "Hashear", clase: "tec-hash", resumen: "Crea una huella del dato que no se puede revertir.",
    ejemplo: "9f2c4a…e71b", reversible: "Irreversible: solo sirve para comparar.",
    uso: "Contraseñas (bcrypt), sesiones y códigos del correo: se comparan, nunca se leen." },
];
$("tecnicas").append(...TECNICAS.map((t) =>
  el("div", { class: `card tecnica ${t.clase}` },
    el("div", { class: "icon-badge" }, icono(t.ic)),
    el("h3", {}, t.titulo),
    el("p", { class: "muted" }, t.resumen),
    el("code", { class: "muestra" }, t.ejemplo),
    el("dl", {},
      el("dt", {}, "¿Se puede volver al original?"), el("dd", {}, t.reversible),
      el("dt", {}, "En K-Secure"), el("dd", {}, t.uso)))));

// --- Pruébalo ----------------------------------------------------------------------------------
const EJEMPLOS = [["RUT", "15.432.198-5"], ["Correo", "ana.perez@gmail.com"], ["Celular", "+56 9 8765 4321"],
  ["Tarjeta", "4111 1111 1111 1111"]];
$("ejemplos").append(...EJEMPLOS.map(([nombre, valor]) =>
  el("button", { type: "button", onclick: () => { $("dato").value = valor; probar(); } }, nombre)));

let anterior = null;  // para mostrar que el cifrado cambia y el hash no

function salida(titulo, valor, nota, clase) {
  return el("div", { class: `salida ${clase}` },
    el("div", { class: "salida-titulo" }, titulo),
    el("code", {}, valor ?? "—"),
    el("p", { class: "muted" }, nota));
}

async function probar() {
  const texto = $("dato").value.trim();
  if (!texto) return;
  let r;
  try {
    r = await api("/seguridad/ejemplo", { method: "POST", json: { texto } });
  } catch (e) {
    $("demo-aviso").hidden = false;
    $("demo-aviso").textContent = e.message;
    return;
  }
  const mismo = anterior && anterior.dato === r.dato;
  $("demo-aviso").hidden = Boolean(r.tipo);
  $("demo-aviso").textContent = r.tipo ? "" : "K-Secure no reconoce un dato sensible en ese texto, así que no lo enmascara. Igual puedes ver cómo se cifra y se hashea.";
  $("salidas").replaceChildren(
    salida(r.tipo ? `Enmascarado · ${nombreTipo(r.tipo)}` : "Enmascarado", r.enmascarado,
      "Lo que muestra K-Secure en pantalla.", "tec-mascara"),
    salida("Cifrado", r.cifrado,
      mismo ? "Cambió aunque el dato es el mismo: cada cifrado usa datos al azar."
        : "Vuelve a apretar Probar: con el mismo dato sale distinto cada vez.", "tec-cifrado"),
    salida("Hash SHA-256", r.hash,
      mismo ? "Igual que antes: el mismo dato siempre da el mismo hash, y no se puede revertir."
        : "Siempre el mismo para el mismo dato, y no se puede revertir.", "tec-hash"));
  anterior = r;
}

$("demo").addEventListener("submit", (ev) => { ev.preventDefault(); probar(); });
probar();

// --- ¿Por qué cifrar y no hashear? ----------------------------------------------------------------
$("por-que").append(
  el("div", { class: "card por-que no" },
    el("h3", {}, icono("x"), "Si el original se hasheara"),
    el("ul", {},
      el("li", {}, "Nadie podría volver a verlo, ni siquiera un Auditor con la clave: un hash no se revierte."),
      el("li", {}, "Y se podría adivinar: hay menos de 100 millones de RUT posibles (el dígito verificador se calcula solo). Un computador saca el hash de todos en minutos y busca cuál coincide."))),
  el("div", { class: "card por-que si" },
    el("h3", {}, icono("check"), "Por eso se cifra con la clave de auditor"),
    el("ul", {},
      el("li", {}, "El original se puede recuperar cuando hace falta, pero solo con la clave."),
      el("li", {}, "La clave de auditor no se guarda en ninguna parte: si alguien roba la base, los originales no le sirven."),
      el("li", {}, "Cada vez que alguien la usa queda en la bitácora."))));

// --- La bóveda ---------------------------------------------------------------------------------------
const BOVEDA = [
  ["Al crear la clave de auditor", "Se generan dos llaves RSA de 2048 bits. La pública se guarda tal cual; la privada se guarda cifrada con la clave de auditor."],
  ["En cada escaneo", "Se crea una llave AES nueva (Fernet) que cifra los originales de ese escaneo. Esa llave se guarda cifrada con la llave pública, así se puede escanear sin pedir la clave."],
  ["Para ver un original", "La clave de auditor abre la llave privada, que abre la llave del escaneo, que abre el dato. Se muestra 20 segundos y queda en la bitácora."],
];
$("boveda").append(...BOVEDA.map(([titulo, texto], i) =>
  el("li", {}, el("span", { class: "numero" }, String(i + 1)), el("div", {}, el("strong", {}, titulo), el("p", { class: "muted" }, texto)))));

// --- Otras protecciones --------------------------------------------------------------------------------
const PROTECCIONES = [
  "Contraseñas con hash bcrypt; 5 intentos fallidos bloquean la cuenta 5 minutos.",
  "La sesión vence a los 30 minutos sin uso o a las 12 horas, y su cookie no la puede leer JavaScript.",
  "Tres roles: el Visor solo ve datos enmascarados; solo el Auditor y el Admin pueden ver originales.",
  "5 claves de auditor incorrectas seguidas bloquean el desenmascarado 1 minuto.",
  "Recuperar la contraseña con un código de un solo uso que vence a los 10 minutos.",
  "Las bases de los clientes se leen en modo solo lectura y su contraseña no se guarda.",
  "Sin registro público: las cuentas las crea un Admin.",
  "Bitácora de solo lectura con quién hizo qué y cuándo.",
];
$("protecciones").append(...PROTECCIONES.map((p) => el("li", {}, icono("check"), p)));
