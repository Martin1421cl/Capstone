// K-Secure: envío de correos desde la cuenta Gmail del equipo (Google Apps Script).
//
// Render (plan gratis) bloquea el SMTP, así que K-Secure le pide a este script, por HTTPS, que mande
// el correo. Se publica como aplicación web: ejecutar como "Yo", acceso "Cualquier usuario".
// El secreto compartido evita que otros lo usen para mandar correos desde nuestra cuenta.
//
// Configuración (ver README → "Correo para recuperar contraseñas"):
//   1. Configuración del proyecto → Propiedades del script → SECRETO = una clave larga al azar.
//   2. Ejecutar "probar" una vez: pide permisos y manda un correo a esta misma cuenta.
//   3. Implementar → Nueva implementación → Aplicación web. En Render:
//        KSECURE_CORREO_URL     = la URL que termina en /exec
//        KSECURE_CORREO_SECRETO = el mismo valor de SECRETO
//   Al editar el script: Administrar implementaciones → lápiz → Versión: Nueva versión.
//
// Este archivo es solo una copia de referencia: el que corre está en script.google.com.

// Prueba manual desde el editor (elegir "probar" en el selector de funciones y Ejecutar).
function probar() {
  var yo = Session.getActiveUser().getEmail();
  MailApp.sendEmail(yo, "K-Secure: prueba", "Si te llegó este correo, el envío funciona.");
  Logger.log("Correo enviado a " + yo + ". Quedan " + MailApp.getRemainingDailyQuota() + " correos hoy.");
}

// Lo que llama K-Secure: POST con {secreto, para, asunto, texto, html}.
function doPost(e) {
  if (!e || !e.postData) throw new Error("doPost no se ejecuta desde el editor: elige la función probar.");
  var datos;
  try {
    datos = JSON.parse(e.postData.contents);
  } catch (err) {
    return respuesta({ ok: false, error: "Datos inválidos" });
  }
  var secreto = PropertiesService.getScriptProperties().getProperty("SECRETO");
  if (!secreto || datos.secreto !== secreto) return respuesta({ ok: false, error: "Clave incorrecta" });
  if (!datos.para || !datos.asunto || !datos.texto) return respuesta({ ok: false, error: "Faltan datos" });

  var opciones = { to: datos.para, subject: datos.asunto, body: datos.texto, name: "K-Secure" };
  if (datos.html) opciones.htmlBody = datos.html;
  MailApp.sendEmail(opciones);
  return respuesta({ ok: true, quedan: MailApp.getRemainingDailyQuota() });
}

function respuesta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
