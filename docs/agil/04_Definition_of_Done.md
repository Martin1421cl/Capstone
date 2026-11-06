# Definition of Done — K-Secure

Una historia de usuario está **terminada** solo cuando cumple **todos** los puntos de esta lista.
Si falta uno, la historia vuelve al Product Backlog o sigue en el sprint siguiente.

---

## 1. Código

- [ ] Cumple todos los criterios de aceptación de la historia en el [Product Backlog](02_Product_Backlog.md).
- [ ] Sigue la estructura del proyecto: validadores en `validators/`, lectura de archivos en `preprocessors/`,
      escaneo en `escaneo/`, persistencia en `almacenamiento/` y web en `web/`.
- [ ] Nombres y comentarios en español, claros, sin código comentado ni `print` de depuración.
- [ ] No deja contraseñas, llaves ni cadenas de conexión en el código (van en variables de entorno).

## 2. Seguridad (no negociable)

- [ ] Ningún dato original se muestra, se exporta ni se guarda en claro: solo enmascarado o cifrado.
- [ ] Las bases del cliente se abren en solo lectura.
- [ ] Cada endpoint nuevo revisa la sesión y el rol mínimo (Visor, Auditor o Admin).
- [ ] Las acciones sensibles (ver un original, cambiar cuentas o reglas, escanear, exportar) quedan en la bitácora.

## 3. Pruebas

- [ ] Tiene pruebas automáticas con pytest (unitarias y, si toca la API, de integración).
- [ ] **Toda** la suite pasa: `pytest` en `k-secure-web/` termina sin fallos.
- [ ] Se probó a mano en el navegador el flujo completo de la historia.

## 4. Revisión e integración

- [ ] Los cambios están en el repositorio con commits descriptivos, hechos con el usuario de quien los programó.
- [ ] Otro integrante revisó el cambio (pull request o revisión en la reunión semanal).
- [ ] Está integrado en la rama `main` sin conflictos.

## 5. Documentación y despliegue

- [ ] El README o el manual técnico se actualizaron si cambia la forma de instalar o usar K-Secure.
- [ ] Si agrega un requisito, se actualizó la ERS o los casos de uso.
- [ ] Funciona en la versión publicada (Render + Neon) y con `docker compose up`.

## 6. Aceptación

- [ ] Se mostró al equipo en la revisión del sprint y se marcó como ✅ en el Product Backlog.
