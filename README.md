# Youtify v1.3.4

Aplicación de escritorio para Windows que guarda audio MP3 y video MP4 de YouTube.
Descarga únicamente contenido que tengas derecho a guardar.

## Uso

1. Ejecuta `Youtify-Setup.exe`. El instalador incluye Python, FFmpeg, FFprobe,
   Node.js y los scripts EJS: el usuario no necesita instalarlos aparte.
2. Pega un enlace de video, Shorts o playlist y elige formato y calidad.
3. **Descargar ahora** añade el enlace e inicia la cola. **Añadir a la cola**
   prepara las descargas; si la cola está en pausa, espera a **Iniciar cola**.
4. Puedes cancelar elementos, reintentar errores y abrir los archivos guardados.
   **Pausar cola** permite terminar el archivo actual y detiene el siguiente.

La cola se guarda entre sesiones. Al reiniciar, los pendientes esperan a que pulses
**Iniciar cola**; los archivos `.part` permiten a yt-dlp continuar transferencias
cuando el servidor lo admite. Cancelar durante una conversión conserva el estado
como cancelado. Cerrar durante una descarga guarda el trabajo como pendiente.

## Cambios de 1.3.4

* La compilación en GitHub reutiliza Inno Setup cuando ya está instalado en el
  ejecutor y solo lo instala cuando falta, evitando conflictos de versiones.

## Cambios de 1.3.3

* Pruebas de conversión con un servidor HTTP local y cierre explícito de sus
  recursos para que la limpieza de archivos temporales sea fiable en Windows CI.

## Cambios de 1.3.2

* Selectores de formato, calidad y tema con flechas dibujadas sin glifos de fuente,
  bordes completos y listas redondeadas que siguen los colores de la aplicación.
* Apertura desde todo el campo, opción seleccionada visible y navegación con
  flechas, Enter, Escape y Tab. Las listas se cierran al hacer clic fuera, mover
  la ventana o cambiar de aplicación y se colocan dentro del área visible.

## Cambios de 1.3.1

* Un video individual muestra una sola barra: el avance de su archivo.
* Al descargar una playlist aparece una segunda barra con el avance total y
  el contador de canciones guardadas. Incluye el avance parcial del archivo
  actual; cada canción tiene el mismo peso en el total.
* Cada playlist conserva su contador, sin sumar el historial u otras listas.
  Los errores y las cancelaciones se indican por separado: el 100 % total
  significa que la lista terminó de procesarse, no que todos sus archivos
  necesariamente se guardaron. Al reintentar un elemento, vuelve a estar pendiente.
* El contador se conserva al pausar, reiniciar o limpiar el historial terminado.

## Cambios de 1.3.0

* Actualizaciones completas en segundo plano, sin volver a ejecutar un instalador.
  Se consulta GitHub como máximo cada seis horas y solo se aceptan versiones
  estables superiores con el paquete `Youtify-Update-x64.zip` y su SHA-256
  publicado por la API de GitHub.
* El paquete se valida, se comprueban sus componentes y se activa de forma
  atómica en `%LOCALAPPDATA%\Youtify\versions`. La versión en uso y las descargas
  continúan funcionando; la actualización se aplica al volver a abrir.
* Un aviso discreto aparece una sola vez por versión cuando el paquete está
  listo. Sin conexión o si falla la verificación, se conserva la versión actual
  y se reintenta en una consulta posterior. El modo de desarrollo no se actualiza.
* Los accesos directos conservan su destino: el ejecutable instalado inicia la
  versión verificada más reciente. Esto también funciona con instalaciones en
  `Program Files`, sin sobrescribir archivos en uso ni pedir elevación adicional.

## Cambios de 1.2.1

* Una sola ventana por sesión de Windows, tanto desde el ejecutable como desde
  el código fuente. El bloqueo se adquiere antes de cargar la interfaz.
* Los clics repetidos recuperan la ventana existente, incluso minimizada, sin
  crear ventanas de aviso ni depender de la carpeta de datos.
* Distribución en dos columnas: ajustes a la izquierda, cola y actividad a la
  derecha, y progreso fijo debajo. Los controles principales caben en ventanas
  bajas y el desplazamiento se limita a los paneles de opciones y archivos.
* Un error al aplicar una respuesta en segundo plano no detiene las siguientes
  actualizaciones de la interfaz.

## Cambios de 1.2.0

* Interfaz redimensionable con temas oscuro/claro/sistema, cola visible, progreso
  por archivo, velocidad, tiempo restante y actividad en una pestaña separada.
* La consulta de playlists y la previsualización se ejecutan fuera del hilo de Tk.
  Respuestas antiguas no sustituyen la previsualización actual.
* Cancelación de descargas y procesos auxiliares propios. Los fallos se muestran
  como fallos y no se convierten en un mensaje de éxito al terminar la cola.
* Nombres con título, identificador y calidad para evitar colisiones.
* MP4 final incluso cuando el formato disponible necesita remultiplexado.
* Portadas JPEG de hasta 600 px y etiquetas ID3; sin consultas duplicadas de
  metadatos para calcular el tamaño de cada video.
* Playlists sin el anterior recorte silencioso de 100 videos. Capacidad máxima
  explícita: 2000 trabajos pendientes, con error visible si se supera.
* Preferencias y cola escritas de forma atómica; registro rotativo de diagnóstico.
* Motor JavaScript y scripts EJS locales. No se ejecuta pip ni se descarga código
  JavaScript al abrir la aplicación. Clientes de YouTube seleccionados por yt-dlp.
* Paquetes fijados, componentes verificados mediante SHA-256 y comprobación del
  ejecutable empaquetado en la compilación.

YouTube puede exigir verificaciones o limitar solicitudes (por ejemplo HTTP 429).
La aplicación muestra el error y permite reintentar más tarde; un runtime
JavaScript no garantiza acceso a todos los videos.

## Ejecutar desde el código

Windows 10/11 de 64 bits y Python 3.12.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\python scripts/prepare_components.py
.venv\Scripts\python main.py
```

`requirements.txt` fija las dependencias directas de ejecución;
`requirements-build.txt` añade el compilador. `requirements-lock.txt` reproduce
el entorno completo verificado de Windows, incluidas las dependencias transitivas.
Actualiza esas versiones de forma deliberada y vuelve a ejecutar las pruebas.

## Pruebas y compilación

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python scripts/build.py
iscc installer.iss
.venv\Scripts\python scripts/package_release.py
```

`scripts/build.py` ejecuta las pruebas, genera `build/version.iss` desde
`config.settings.APP_VERSION`, compila `Youtify.spec` y comprueba el paquete.
Necesitas Inno Setup 6.5.4 o posterior para generar el instalador.

El ejecutable y sus archivos auxiliares se generan en `dist\Youtify\`.
Se usa una carpeta de aplicación para evitar extraer Python en cada arranque.
El usuario recibe un único `installer\Youtify-Setup.exe`; no debe copiar solamente
el ejecutable de `dist` sin sus archivos auxiliares. El compilador conserva los
antiguos `dist\Youtify.exe` y `dist\app.exe` en `build\legacy-executables` para
evitar abrir por error una versión obsoleta.

Para migrar una instalación antigua, ejecuta el instalador 1.3.0 una vez. Conserva
el identificador de la aplicación y reutiliza el modo de instalación y la carpeta
anteriores, incluyendo instalaciones en `Program Files`; así actualiza el destino
de los accesos directos existentes. Las instalaciones nuevas pueden elegir modo
por usuario o para todos los usuarios. Una actualización de una instalación para
todos los usuarios puede requerir la confirmación de Windows.

Después de esa migración, las versiones futuras se descargan y activan sin
instalador. El instalador sigue disponible para la primera instalación o una
reparación. Los paquetes preparados conservan la versión anterior; una descarga
incompleta nunca reemplaza la aplicación instalada.

Las pruebas de integración generan medios sintéticos y verifican MP3, etiquetas,
portada y MP4 con FFmpeg/FFprobe, sin depender de YouTube. Las pruebas de interfaz
crean widgets reales y usan datos temporales aislados.

## GitHub Actions y versiones

El workflow compila en cada push a `main` y permite ejecución manual. Valida las
pruebas antes de compilar, incluye los componentes y publica el instalador solo
al recibir una etiqueta que coincida con `APP_VERSION` (por ejemplo `v1.3.4`).
Los artefactos incluyen el instalador, `Youtify-Update-x64.zip`, SHA-256 y el
informe de componentes. Cada release debe conservar ese nombre exacto para el ZIP;
GitHub proporciona su campo `digest` SHA-256 para la comprobación automática.
La compilación local no crea commits ni publica releases automáticamente.

## Datos locales

* Descargas por defecto: `Downloads\Youtify\Musica_Descargada` y
  `Downloads\Youtify\descargas_videos`. La carpeta se puede cambiar y restablecer.
* `%LOCALAPPDATA%\Youtify\preferences.json`: formato, calidad, carpeta y tema.
* `%LOCALAPPDATA%\Youtify\queue.json`: trabajos pendientes y hasta 100 resultados.
* `%LOCALAPPDATA%\Youtify\update_state.json`: última consulta y versión ya avisada.
* `%LOCALAPPDATA%\Youtify\active_version.json` y `versions`: versión verificada activa.
* `%LOCALAPPDATA%\Youtify\logs\youtify.log`: diagnóstico, hasta cuatro archivos
  de 2 MB. Puede contener enlaces, títulos y rutas; no se envía automáticamente.
* `YOUTIFY_DATA_DIR`: ruta alternativa para aislar pruebas y previsualizaciones.

Atajos: **Ctrl+L** enfoca el enlace; **Ctrl+Enter** inicia la descarga.

## Licencias

Código de la aplicación: [MIT](LICENSE). Los componentes incluidos conservan
sus propias licencias: [avisos de terceros](THIRD_PARTY_NOTICES.md).
