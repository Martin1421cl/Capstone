"""Envío de correos de K-Secure (por ahora, el código para recuperar la contraseña).

Render en su plan gratis bloquea el SMTP, así que el correo sale por un Apps Script de la cuenta
Gmail del equipo, publicado como aplicación web (código en docs/apps-script-correo.gs). K-Secure
le manda por HTTPS el destinatario, el asunto y el texto, junto con un secreto compartido para
que nadie más pueda usarlo para mandar correos.

Variables de entorno:
  KSECURE_CORREO_URL      URL de la aplicación web (https://script.google.com/macros/s/.../exec)
  KSECURE_CORREO_SECRETO  el mismo valor de la propiedad SECRETO del script

Sin ellas (por ejemplo, en un PC para probar) el correo no se envía: se escribe en la terminal.
"""

import html
import json
import os
import urllib.request
from dataclasses import dataclass


class ErrorCorreo(RuntimeError):
    """El correo no salió. El mensaje explica por qué (nunca incluye el secreto)."""


@dataclass
class Correo:
    url: str | None = None
    secreto: str | None = None
    espera: float = 20  # segundos; Apps Script a veces tarda en "despertar"

    @classmethod
    def desde_entorno(cls) -> "Correo":
        return cls(os.environ.get("KSECURE_CORREO_URL", "").strip() or None,
                   os.environ.get("KSECURE_CORREO_SECRETO", "").strip() or None)

    @property
    def configurado(self) -> bool:
        return bool(self.url and self.secreto)

    def enviar(self, para: str, asunto: str, texto: str, html_: str | None = None) -> None:
        if not self.configurado:
            print(f"\n[K-Secure] Correo sin configurar: en vez de enviarlo se muestra aquí.\n"
                  f"  Para: {para}\n  Asunto: {asunto}\n\n{texto}\n", flush=True)
            return
        cuerpo = json.dumps({"secreto": self.secreto, "para": para, "asunto": asunto,
                             "texto": texto, "html": html_}).encode()
        pedido = urllib.request.Request(self.url, data=cuerpo, method="POST",
                                        headers={"Content-Type": "application/json"})
        # Apps Script responde con una redirección a script.googleusercontent.com, donde queda
        # la respuesta; urllib la sigue sola (como GET, que es lo que Google espera).
        try:
            with urllib.request.urlopen(pedido, timeout=self.espera) as r:
                bruto = r.read()
        except OSError as e:  # sin red, DNS, tiempo agotado, HTTP 4xx/5xx
            raise ErrorCorreo(f"No se pudo contactar al servicio de correo ({e})") from None
        try:
            respuesta = json.loads(bruto)
        except ValueError:
            raise ErrorCorreo("El servicio de correo respondió algo inesperado. Revisa que la "
                              "implementación del Apps Script tenga acceso «Cualquier usuario».") from None
        if not respuesta.get("ok"):
            raise ErrorCorreo(f"El servicio de correo rechazó el envío: {respuesta.get('error', 'sin detalle')}")


# --- Mensajes ---------------------------------------------------------------------------------

def mensaje_codigo(nombre: str, usuario: str, codigo: str, minutos: int) -> tuple[str, str, str]:
    """Asunto, texto y HTML del correo con el código para crear una contraseña nueva."""
    hola = nombre.split()[0] if nombre.split() else usuario
    asunto = "K-Secure: código para recuperar tu contraseña"  # sin el código: se vería en la pantalla bloqueada
    texto = (
        f"Hola, {hola}:\n\n"
        f"Tu código para crear una contraseña nueva en K-Secure es:\n\n"
        f"    {codigo}\n\n"
        f"Vence en {minutos} minutos y sirve una sola vez (cuenta @{usuario}).\n\n"
        "Si no lo pediste, ignora este correo: tu contraseña no cambia.\n"
        "Nadie de K-Secure te va a pedir este código.\n"
    )
    e = html.escape
    html_ = f"""\
<div style="background:#eef6f8;padding:28px 12px;font-family:Arial,Helvetica,sans-serif;color:#10242c">
  <div style="max-width:440px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #d5e6ea">
    <div style="background:#04080b;padding:18px 24px">
      <span style="color:#00e0f0;font-size:20px;font-weight:bold;letter-spacing:.5px">K-Secure</span>
    </div>
    <div style="padding:26px 24px">
      <p style="margin:0 0 14px;font-size:16px">Hola, {e(hola)}:</p>
      <p style="margin:0 0 18px;font-size:15px;line-height:1.5">Tu código para crear una contraseña nueva es:</p>
      <p style="margin:0 0 18px;text-align:center">
        <span style="display:inline-block;padding:12px 20px;border-radius:10px;background:#e6fbfd;border:1px solid #9ee9f0;
          font-family:Consolas,'Courier New',monospace;font-size:32px;font-weight:bold;letter-spacing:8px;color:#04080b">{e(codigo)}</span>
      </p>
      <p style="margin:0 0 6px;font-size:14px;color:#3d5a64">Vence en {minutos} minutos y sirve una sola vez (cuenta @{e(usuario)}).</p>
      <p style="margin:18px 0 0;font-size:13px;color:#6b8790;line-height:1.5">Si no lo pediste, ignora este correo: tu contraseña no cambia.
        Nadie de K-Secure te va a pedir este código.</p>
    </div>
  </div>
</div>"""
    return asunto, texto, html_


def mensaje_prueba(nombre: str) -> tuple[str, str, str]:
    hola = nombre.split()[0] if nombre.split() else ""
    texto = (f"Hola, {hola}:\n\nEste es un correo de prueba de K-Secure. Si te llegó, los códigos para "
             "recuperar la contraseña también van a llegar.\n")
    html_ = (f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#10242c;line-height:1.5">'
             f'<p>Hola, {html.escape(hola)}:</p><p>Este es un correo de prueba de <b>K-Secure</b>. Si te llegó, '
             f'los códigos para recuperar la contraseña también van a llegar.</p></div>')
    return "K-Secure: correo de prueba", texto, html_
