# 🌐 CnCNet Tunnel Server GUI - LatinBattle

Panel gráfico en **Python + Tkinter** para administrar y lanzar `cncnet-server.exe` usando argumentos configurables desde una interfaz moderna con pestañas tipo **TabPage**.

Este proyecto fue creado para facilitar la ejecución de un **CnCNet Tunnel Server** sin tener que escribir comandos manuales cada vez.

---

## 🔗 Proyecto / referencia original

Este GUI fue creado tomando como referencia la guía original compartida por Azzlaer:

**How to host a CnCNet Server**  
https://forums.cncnet.org/topic/6325-how-to-host-a-cncnet-server/

Argumentos usados por `cncnet-server.exe`:

```txt
--port          (Default: 50001) Port used for the tunnel server
--portv2        (Default: 50000) Port used for the V2 tunnel server
--name          (Default: Unnamed server) Name of the server
--maxclients    (Default: 200) Maximum clients allowed on the tunnel server
--nomaster      (Default: false) Don't register to master
--masterpw      (Default: ) Master password
--maintpw       (Default: ) Maintenance password
--master        (Default: http://cncnet.org/master-announce) Master server URL
--iplimit       (Default: 8) Maximum clients allowed per IP address
--iplimitv2     (Default: 4) Max game request allowed per IP address on V2 tunnel
--nop2p         (Default: false) Disable NAT traversal ports (8054, 3478 UDP)
--help          Display this help screen.
--version       Display version information.
```

---

## 📌 ¿Qué hace este proyecto?

Este panel permite configurar, iniciar, detener, detectar y monitorear un servidor `cncnet-server.exe` desde una interfaz gráfica.

El objetivo es evitar tener que ejecutar comandos largos manualmente por consola, permitiendo configurar todo desde campos visuales y guardar la configuración automáticamente en un archivo `.ini`.

---

## 📁 Archivos principales del proyecto

```txt
cncnet_server_gui_final_tray.py
ejecutar_cncnet_gui_admin.bat
cncnet_server_gui.ini
```

### `cncnet_server_gui_final_tray.py`

Archivo principal del panel gráfico.

Incluye:

- Interfaz con pestañas.
- Configuración de argumentos.
- Inicio y detención del servidor.
- Detección de proceso externo.
- Consola en vivo.
- Soporte para bandeja de Windows.
- Opción de ventana siempre encima.
- Herramientas para solucionar errores de `HttpListener`.
- Creación de URLACL para el puerto V2.

### `ejecutar_cncnet_gui_admin.bat`

Archivo BAT para ejecutar el panel como administrador.

Es útil porque algunas funciones requieren permisos elevados, especialmente:

- Crear URLACL.
- Eliminar URLACL.
- Cerrar procesos externos.
- Solucionar el error `Access is denied` de `HttpListener`.

### `cncnet_server_gui.ini`

Archivo generado automáticamente al guardar configuración.

Contiene los valores usados por el panel:

- Ruta del ejecutable.
- Nombre del servidor.
- Puertos.
- Contraseñas.
- Límites de clientes.
- Opciones de ventana.
- Opciones de bandeja.
- Auto-detección.

---

## 🧰 Requisitos

### Requisitos básicos

- Windows 10 / Windows 11.
- Python 3.10 o superior.
- `cncnet-server.exe`.
- Permisos de administrador recomendados.

### Librerías incluidas por Python

El panel usa principalmente librerías estándar:

```txt
tkinter
subprocess
configparser
threading
queue
socket
ctypes
pathlib
```

### Librerías opcionales para bandeja de Windows

Para usar la opción de minimizar a bandeja necesitas instalar:

```bash
pip install pystray pillow
```

Si no instalas estas librerías, el panel seguirá funcionando, pero la bandeja de Windows estará desactivada.

---

## 🚀 Cómo ejecutar el proyecto

### Opción 1: Ejecutar normal

```bash
python cncnet_server_gui_final_tray.py
```

### Opción 2: Ejecutar como administrador usando BAT

Ejecuta:

```bat
ejecutar_cncnet_gui_admin.bat
```

Este archivo pedirá permisos UAC de Windows y abrirá el panel con privilegios de administrador.

---

## 🖥️ Interfaz con pestañas

El proyecto está dividido en pestañas para evitar que el formulario sea demasiado grande.

---

# 🏠 INICIO

La pestaña **INICIO** contiene los controles principales del servidor.

Incluye:

- **Iniciar servidor**
- **Detener GUI**
- **Detectar proceso**
- **Detener detectado**
- Estado actual del servidor.
- PID del proceso.
- Nombre del proceso detectado.
- Comando generado.

Desde esta pestaña puedes operar el servidor rápidamente sin entrar a todas las opciones avanzadas.

---

# ⚙️ OPCIONES

La pestaña **OPCIONES** contiene los argumentos principales de `cncnet-server.exe`.

Campos disponibles:

| Campo | Argumento |
|---|---|
| Ejecutable | Ruta de `cncnet-server.exe` |
| Proceso a detectar | Nombre del proceso |
| Nombre servidor | `--name` |
| Puerto túnel | `--port` |
| Puerto V2 | `--portv2` |
| Máximo clientes | `--maxclients` |
| Límite por IP | `--iplimit` |
| Límite IP V2 | `--iplimitv2` |

También incluye checkboxes:

| Opción | Función |
|---|---|
| No registrar en master | Usa `--nomaster` |
| Desactivar NAT traversal | Usa `--nop2p` |
| Auto-detectar proceso abierto | Detecta si el servidor ya está corriendo |
| Minimizar a bandeja de Windows | Oculta el panel en la bandeja |
| Mantener ventana siempre encima | Mantiene el panel por encima de otras ventanas |

---

# 🔐 MASTER / SEGURIDAD

Esta pestaña contiene opciones relacionadas con el master server y contraseñas.

Campos disponibles:

| Campo | Argumento |
|---|---|
| Master URL | `--master` |
| Master password | `--masterpw` |
| Maintenance password | `--maintpw` |

Recomendaciones:

- No compartas capturas donde aparezcan las contraseñas.
- Usa contraseñas seguras.
- Si el servidor es privado, puedes activar `--nomaster`.
- Si usas un master personalizado, asegúrate de que la URL sea correcta.

---

# 🧰 HERRAMIENTAS

La pestaña **HERRAMIENTAS** incluye acciones útiles para diagnosticar y administrar el servidor.

Funciones:

- **Probar puertos**
- **Ver permisos Admin**
- **Crear URLACL V2**
- **Eliminar URLACL V2**
- **Reiniciar GUI como Admin**
- **Probar bandeja**
- **Aplicar siempre encima**
- **Ejecutar --help**
- **Ejecutar --version**
- **Copiar comando**
- **Abrir carpeta del panel**
- **Guardar configuración**
- **Restaurar defaults**

---

# 🖥️ CONSOLA

La pestaña **CONSOLA** muestra:

- Salida en vivo del servidor.
- Mensajes internos del panel.
- Errores detectados.
- Resultado de comandos.
- Resultado de `netsh`.
- Eventos de detección.
- Eventos de inicio y detención.

También incluye:

- Botón para limpiar consola.
- Checkbox de auto-scroll.

---

# ℹ️ ACERCA DE

Incluye:

- Resumen del proyecto.
- Características principales.
- Consejos de uso.
- Recordatorio de dependencias.
- Créditos del proyecto.

---

## 🧾 Argumentos soportados

El panel genera automáticamente un comando como este:

```bat
cncnet-server.exe --port 50001 --portv2 50000 --name "LatinBattle Tunnel Server" --maxclients 200 --master http://cncnet.org/master-announce --iplimit 8 --iplimitv2 4
```

Si activas opciones extra, puede agregar:

```bat
--nomaster
--nop2p
--masterpw TU_PASSWORD
--maintpw TU_PASSWORD
```

---

## 🌐 Puertos importantes

Por defecto:

| Puerto | Uso |
|---|---|
| 50001 | Tunnel server |
| 50000 | Tunnel V2 |
| 8054 UDP | NAT traversal |
| 3478 UDP | NAT traversal |

Si quieres que el servidor sea público, debes revisar:

- Firewall de Windows.
- Router / port forwarding.
- Reglas de VPS si usas servidor dedicado.
- Que los puertos no estén ocupados por otro programa.

---

## 🛡️ Solución al error: `HttpListenerException: Access is denied`

Si al iniciar el servidor ves este error:

```txt
Unhandled Exception: System.Net.HttpListenerException: Access is denied
   at System.Net.HttpListener.AddAllPrefixes()
   at System.Net.HttpListener.Start()
   at CnCNet.Net.Tunnel.TunnelV2.Start()
   at CnCNetServer.Program.Main(String[] args)
```

Significa que Windows bloqueó el listener HTTP del servidor V2.

Normalmente ocurre con el puerto:

```txt
--portv2 50000
```

### Solución desde el panel

1. Ejecuta el panel como administrador.
2. Ve a **HERRAMIENTAS**.
3. Presiona **Crear URLACL V2**.
4. Vuelve a **INICIO**.
5. Inicia el servidor otra vez.

### Comando equivalente manual

Si el puerto V2 es `50000`, el comando sería:

```bat
netsh http add urlacl url=http://+:50000/ user=TU_USUARIO_WINDOWS
```

Para eliminar la reserva:

```bat
netsh http delete urlacl url=http://+:50000/
```

El panel incluye botones para crear y eliminar esta URLACL automáticamente.

---

## 📥 Minimizar a bandeja de Windows

El panel incluye soporte para minimizarse a la bandeja de Windows.

Para activar esta función:

1. Instala dependencias:

```bash
pip install pystray pillow
```

2. Abre el panel.
3. Ve a **OPCIONES**.
4. Activa:

```txt
Minimizar a bandeja de Windows
```

Cuando esta opción está activa:

- Al minimizar el panel, se oculta en la bandeja.
- Al presionar la X, se oculta en la bandeja en vez de cerrarse.
- Desde el icono de bandeja puedes:
  - Mostrar panel.
  - Iniciar servidor.
  - Detener detectado.
  - Salir.

---

## 📌 Mantener ventana siempre encima

El panel también incluye una opción para mantener la ventana por encima de todas las demás.

Para usarla:

1. Ve a **OPCIONES**.
2. Activa:

```txt
Mantener ventana siempre encima
```

También puedes aplicarlo desde:

```txt
HERRAMIENTAS > Aplicar siempre encima
```

Esta opción no requiere librerías extra.

---

## 🔎 Detección de proceso

El panel puede detectar si `cncnet-server.exe` ya está abierto aunque haya sido iniciado fuera del GUI.

Detecta por defecto:

```txt
cncnet-server.exe
cncnet-server-core.exe
```

También puedes definir manualmente el proceso desde:

```txt
OPCIONES > Proceso a detectar
```

Funciones disponibles:

- Detectar proceso.
- Mostrar PID.
- Detectar procesos externos.
- Detener procesos externos con `taskkill`.

Para cerrar procesos externos, se recomienda ejecutar el panel como administrador.

---

## 💾 Configuración INI

El panel guarda configuración automáticamente en:

```txt
cncnet_server_gui.ini
```

Ejemplo:

```ini
[server]
exe_path = C:\CnCNet\cncnet-server.exe
process_name = cncnet-server.exe
port = 50001
portv2 = 50000
name = LatinBattle Tunnel Server
maxclients = 200
nomaster = false
masterpw =
maintpw =
master = http://cncnet.org/master-announce
iplimit = 8
iplimitv2 = 4
nop2p = false
auto_scroll = true
auto_detect = true
monitor_interval = 3000
minimize_to_tray = true
always_on_top = false
```

---

## 🧪 Probar puertos

Desde la pestaña **HERRAMIENTAS** puedes usar:

```txt
Probar puertos
```

Esta función revisa si los puertos TCP principales parecen libres localmente.

Importante:

- Esta prueba no confirma si el puerto está abierto públicamente desde Internet.
- Para validar acceso externo, debes revisar firewall, router o herramientas externas.
- Los puertos UDP 8054 y 3478 se mencionan como referencia para NAT traversal.

---

## 🧱 Estructura recomendada de carpeta

Ejemplo:

```txt
CnCNetServerPanel/
│
├── cncnet_server_gui_final_tray.py
├── ejecutar_cncnet_gui_admin.bat
├── cncnet_server_gui.ini
├── cncnet-server.exe
└── README.md
```

---

## 🧑‍💻 Compilar a EXE opcional

Puedes convertir el panel Python en `.exe` usando PyInstaller.

Instalar:

```bash
pip install pyinstaller
```

Compilar:

```bash
pyinstaller --onefile --noconsole cncnet_server_gui_final_tray.py
```

Si usas bandeja, instala también:

```bash
pip install pystray pillow
```

El EXE final quedará en:

```txt
dist/cncnet_server_gui_final_tray.exe
```

---

## 🧯 Problemas comunes

### El servidor se abre y se cierra rápido

Revisa la pestaña **CONSOLA**.

Posibles causas:

- Falta URLACL.
- Puerto ocupado.
- Falta permiso de administrador.
- Argumento mal escrito.
- `cncnet-server.exe` no está en la ruta correcta.

---

### Error `Access is denied`

Solución:

- Ejecutar como administrador.
- Crear URLACL V2 desde herramientas.

---

### No aparece en la lista pública

Revisa:

- Que `--nomaster` no esté activado.
- Que el master URL sea correcto.
- Que firewall/router permitan los puertos.
- Que el servidor no esté bloqueado por red o VPS.
- Que los puertos configurados estén abiertos.

---

### No funciona minimizar a bandeja

Instala:

```bash
pip install pystray pillow
```

Luego reinicia el panel.

---

### No puedo cerrar procesos externos

Ejecuta el panel como administrador usando:

```bat
ejecutar_cncnet_gui_admin.bat
```

---

## ✅ Recomendaciones finales

- Ejecuta el panel como administrador si usarás URLACL o cierre de procesos.
- Guarda configuración después de cambiar opciones.
- Mantén `cncnet-server.exe` junto al panel o selecciona su ruta.
- Revisa la consola si el servidor se cae.
- No publiques tus contraseñas `masterpw` o `maintpw`.
- Si cambias `--portv2`, vuelve a crear URLACL para el nuevo puerto.

---

## 🏷️ Créditos

Proyecto creado por:

```txt
ChatGPT OpenAI y Azzlaer para LatinBattle.com
```

Referencia original:

```txt
https://forums.cncnet.org/topic/6325-how-to-host-a-cncnet-server/
```

---

## 📜 Licencia / Uso

Este proyecto puede ser usado, modificado y adaptado para servidores personales o comunidades de CnCNet.

Se recomienda mantener los créditos del proyecto si se publica o redistribuye.
