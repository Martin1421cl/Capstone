import { api } from "./api.js";
import { asegurarClaveAuditor, aviso, el, icono, mostrarEscaneando } from "./ui.js";

const dropzone = document.getElementById("dropzone");
const selector = document.getElementById("selector");
const lista = document.getElementById("lista");
const resumen = document.getElementById("resumen");
const botonEscanear = document.getElementById("escanear");
document.getElementById("icono-subir").append(icono("subir"));

let archivos = [];

const tamano = (b) => (b < 1024 * 1024 ? `${Math.max(1, Math.round(b / 1024))} KB` : `${(b / 1024 / 1024).toFixed(1)} MB`);
const extension = (nombre) => (nombre.includes(".") ? nombre.split(".").pop() : "?");

function agregar(nuevos) {
  for (const f of nuevos) {
    // El mismo archivo dos veces no aporta nada.
    if (!archivos.some((a) => a.name === f.name && a.size === f.size)) archivos.push(f);
  }
  pintar();
}

function pintar() {
  lista.replaceChildren(...archivos.map((f, i) => el("li", {},
    el("span", { class: "ext" }, extension(f.name)),
    el("span", { class: "nombre", title: f.name }, f.name),
    el("span", { class: "muted" }, tamano(f.size)),
    el("button", {
      class: "btn btn-icon btn-sm", type: "button", "aria-label": `Quitar ${f.name}`,
      onclick: () => { archivos.splice(i, 1); pintar(); },
    }, icono("x")))));
  const total = archivos.reduce((s, f) => s + f.size, 0);
  resumen.textContent = archivos.length
    ? `${archivos.length} archivo${archivos.length > 1 ? "s" : ""} · ${tamano(total)}`
    : "Ningún archivo elegido";
  botonEscanear.disabled = !archivos.length;
}

selector.addEventListener("change", () => { agregar(selector.files); selector.value = ""; });
for (const evento of ["dragenter", "dragover"]) {
  dropzone.addEventListener(evento, (e) => { e.preventDefault(); dropzone.classList.add("encima"); });
}
for (const evento of ["dragleave", "drop"]) {
  dropzone.addEventListener(evento, () => dropzone.classList.remove("encima"));
}
dropzone.addEventListener("drop", (e) => { e.preventDefault(); agregar(e.dataTransfer.files); });

botonEscanear.addEventListener("click", async () => {
  if (!(await asegurarClaveAuditor())) return;
  const form = new FormData();
  archivos.forEach((f) => form.append("archivos", f));
  const cerrar = mostrarEscaneando(`Revisando ${resumen.textContent}`);
  try {
    const { escaneo_id } = await api("/archivos", { method: "POST", form });
    location.href = `/resultados.html?id=${escaneo_id}`;
  } catch (e) {
    cerrar();
    aviso(e.message, "error");
  }
});
