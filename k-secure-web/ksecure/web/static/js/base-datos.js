import { api } from "./api.js";
import { asegurarClaveAuditor, aviso, el, icono, mostrarEscaneando } from "./ui.js";

const $ = (id) => document.getElementById(id);
const DESCRIPCIONES = {
  sqlite: "Un archivo .db. Se sube desde Escanear archivos.",
  postgresql: "También Neon, Supabase, Amazon RDS y otros servicios en la nube.",
  mysql: "Incluye MariaDB.",
  sqlserver: "Microsoft SQL Server y Azure SQL.",
  oracle: "Se conecta con el service name.",
};

let motor = null;
let conexion = null;

function irAPaso(n) {
  [1, 2, 3].forEach((i) => { $(`paso-${i}`).hidden = i !== n; });
  [...$("stepper").children].forEach((li, i) => {
    li.classList.toggle("actual", i + 1 === n);
    li.classList.toggle("hecho", i + 1 < n);
  });
}

// --- Paso 1: elegir el motor ---------------------------------------------------
function elegirMotor(m) {
  if (m.id === "sqlite") {
    location.href = "/archivos.html";
    return;
  }
  motor = m;
  $("titulo-conexion").textContent = `Conexión a ${m.nombre}`;
  $("puerto").value = m.puerto;
  $("label-base").textContent = m.id === "oracle" ? "Service name" : "Base de datos";
  irAPaso(2);
  $("host").focus();
}

const motores = await api("/bd/motores");
$("motores").append(...motores.map((m) => el("button", {
  type: "button", class: "card card-hover motor entrar", onclick: () => elegirMotor(m),
},
  el("div", { class: "icon-badge" }, icono(m.id === "sqlite" ? "archivo" : "bd")),
  el("h3", {}, m.nombre),
  el("p", { class: "muted", style: "margin:0" }, DESCRIPCIONES[m.id] || ""))));

$("aviso-lectura").append(icono("escudo"), el("span", {},
  "K-Secure se conecta en ", el("strong", {}, "solo lectura"),
  " y nunca modifica tu base. La contraseña se usa solo para este escaneo: no se guarda."));

// --- Paso 2: probar la conexión ------------------------------------------------
$("form-conexion").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const datos = Object.fromEntries(new FormData(ev.target));
  conexion = { ...datos, motor: motor.id, puerto: Number(datos.puerto) || null };
  $("probar").disabled = true;
  $("probar").textContent = "Conectando…";
  try {
    const { tablas } = await api("/bd/probar", { method: "POST", json: conexion });
    mostrarTablas(tablas);
    irAPaso(3);
  } catch (e) {
    aviso(e.message, "error");
  } finally {
    $("probar").disabled = false;
    $("probar").textContent = "Probar conexión";
  }
});

// --- Paso 3: elegir tablas y escanear -------------------------------------------
function mostrarTablas(tablas) {
  $("titulo-tablas").textContent = `${tablas.length} tabla${tablas.length === 1 ? "" : "s"} encontrada${tablas.length === 1 ? "" : "s"}`;
  $("tablas").replaceChildren(...tablas.map((t) =>
    el("label", {}, el("input", { type: "checkbox", value: t, checked: true }), t)));
  $("todas").checked = true;
}

const casillas = () => [...$("tablas").querySelectorAll("input")];
$("todas").addEventListener("change", (e) => casillas().forEach((c) => { c.checked = e.target.checked; }));
$("tablas").addEventListener("change", () => { $("todas").checked = casillas().every((c) => c.checked); });

$("escanear").addEventListener("click", async () => {
  const tablas = casillas().filter((c) => c.checked).map((c) => c.value);
  if (!tablas.length) return aviso("Elige al menos una tabla", "error");
  if (!(await asegurarClaveAuditor())) return;
  const cerrar = mostrarEscaneando(`Revisando ${tablas.length} tabla${tablas.length === 1 ? "" : "s"} de ${conexion.base}`);
  try {
    const { escaneo_id } = await api("/bd/escanear", {
      method: "POST", json: { conexion, tablas, max_filas: Number($("max-filas").value) },
    });
    location.href = `/resultados.html?id=${escaneo_id}`;
  } catch (e) {
    cerrar();
    aviso(e.message, "error");
  }
});

$("volver-1").addEventListener("click", () => irAPaso(1));
$("volver-2").addEventListener("click", () => irAPaso(2));
irAPaso(1);
