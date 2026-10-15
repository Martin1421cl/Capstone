import { api } from "./api.js";
import { tarjetaEscaneo } from "./tarjetas.js";
import { el, icono } from "./ui.js";

const ACCIONES = [
  { href: "/archivos.html", icono: "archivo", titulo: "Escanear archivos",
    texto: "Arrastra documentos Word, Excel, PowerPoint, PDF, CSV o bases SQLite (.db). Revisamos también encabezados, notas y metadata." },
  { href: "/base-datos.html", icono: "bd", titulo: "Conectar una base de datos",
    texto: "PostgreSQL, MySQL, SQL Server u Oracle en modo solo lectura. Te decimos qué columnas guardan datos sensibles." },
];

const PASOS = [
  { icono: "lupa", titulo: "Detecta", texto: "Cada texto pasa por 7 validadores chilenos: Módulo 11 para el RUT, Luhn para tarjetas y el contexto alrededor del dato." },
  { icono: "escudo", titulo: "Clasifica", texto: "Cada hallazgo queda como Restringido, Confidencial, Interno o Público según qué tan grave sería que se filtre." },
  { icono: "candado", titulo: "Protege", texto: "Ves los datos enmascarados. El original queda cifrado y solo se muestra con la clave de auditor." },
];

const DETECTA = [
  ["RUT", "**.***.198-5"], ["Celular y fijo", "+56 9 **** 4870"], ["Tarjeta de pago", "****-****-****-0366"],
  ["Correo", "an****@gmail.com"], ["Cuenta bancaria", "*******6789"], ["Patente", "**·**·12"], ["Claves y tokens", "AKIA********"],
];

document.getElementById("acciones").append(...ACCIONES.map((a) =>
  el("a", { href: a.href, class: "card card-hover action-card entrar" },
    el("div", { class: "icon-badge" }, icono(a.icono)),
    el("h3", {}, a.titulo), el("p", { class: "muted" }, a.texto),
    el("span", { class: "arrow" }, "Comenzar", icono("flecha")))));

document.getElementById("pasos").append(...PASOS.map((p) =>
  el("div", { class: "card card-hover step entrar" },
    el("div", { class: "icon-badge" }, icono(p.icono)),
    el("h3", {}, p.titulo), el("p", { class: "muted", style: "margin:0" }, p.texto))));

document.getElementById("detecta").append(...DETECTA.map(([nombre, ejemplo]) =>
  el("div", { class: "chip" }, el("strong", {}, nombre), el("code", {}, ejemplo))));

const escaneos = await api("/escaneos").catch(() => []);
if (escaneos.length) {
  document.getElementById("lista-recientes").append(...escaneos.slice(0, 3).map((e) => tarjetaEscaneo(e)));
  document.getElementById("recientes").hidden = false;
}
