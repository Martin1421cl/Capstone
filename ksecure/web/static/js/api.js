// Llamadas a la API de K-Secure y datos compartidos entre páginas.

export async function api(ruta, { method = "GET", json, form } = {}) {
  const opciones = { method };
  if (json !== undefined) {
    opciones.headers = { "Content-Type": "application/json" };
    opciones.body = JSON.stringify(json);
  } else if (form) {
    opciones.body = form;
  }
  const res = await fetch(`/api${ruta}`, opciones);
  if (res.status === 204) return null;
  const datos = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detalle = Array.isArray(datos.detail) ? "Datos inválidos" : datos.detail;
    throw Object.assign(new Error(detalle || `Error ${res.status}`), { status: res.status });
  }
  return datos;
}

export const RIESGOS = [
  { id: "Restringido", descripcion: "Identifica a una persona o permite un fraude: RUT, tarjetas, cuentas, claves." },
  { id: "Confidencial", descripcion: "Datos personales de contacto: celulares, correos personales, patentes." },
  { id: "Interno", descripcion: "Datos dudosos o de empresas: RUT de empresa, teléfonos fijos, datos de prueba." },
  { id: "Público", descripcion: "Datos pensados para publicarse, como contacto@empresa.cl." },
];

export const TIPOS = {
  RUT: "RUT",
  TELEFONO: "Teléfono",
  TARJETA_PAGO: "Tarjeta de pago",
  EMAIL: "Correo",
  CUENTA_BANCARIA: "Cuenta bancaria",
  PATENTE: "Patente",
  SECRETO: "Clave o token",
};

export const nombreTipo = (tipo) => TIPOS[tipo] || tipo;
