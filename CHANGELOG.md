# 📝 Historial de cambios

Novedades de Youtify. Los instaladores publicados están en [GitHub Releases](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases).

## 1.3.4

* La compilación en GitHub reutiliza Inno Setup cuando ya está instalado en el
  ejecutor y solo lo instala cuando falta, evitando conflictos de versiones.

## 1.3.3

* Pruebas de conversión con un servidor HTTP local y cierre explícito de sus
  recursos para que la limpieza de archivos temporales sea fiable en Windows CI.

## 1.3.2

* Selectores de formato, calidad y tema con flechas dibujadas sin glifos de fuente,
  bordes completos y listas redondeadas que siguen los colores de la aplicación.
* Apertura desde todo el campo, opción seleccionada visible y navegación con
  flechas, Enter, Escape y Tab. Las listas se cierran al hacer clic fuera, mover
  la ventana o cambiar de aplicación y se colocan dentro del área visible.

## 1.3.1

* Un video individual muestra una sola barra: el avance de su archivo.
* Al descargar una playlist aparece una segunda barra con el avance total y
  el contador de canciones guardadas. Incluye el avance parcial del archivo
  actual; cada canción tiene el mismo peso en el total.
* Cada playlist conserva su contador, sin sumar el historial u otras listas.
  Los errores y las cancelaciones se indican por separado: el 100 % total
  significa que la lista terminó de procesarse, no que todos sus archivos
  necesariamente se guardaron. Al reintentar un elemento, vuelve a estar pendiente.
* El contador se conserva al pausar, reiniciar o limpiar el historial terminado.

## 1.3.0

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

## 1.2.1

* Una sola ventana por sesión de Windows, tanto desde el ejecutable como desde
  el código fuente. El bloqueo se adquiere antes de cargar la interfaz.
* Los clics repetidos recuperan la ventana existente, incluso minimizada, sin
  crear ventanas de aviso ni depender de la carpeta de datos.
* Distribución en dos columnas: ajustes a la izquierda, cola y actividad a la
  derecha, y progreso fijo debajo. Los controles principales caben en ventanas
  bajas y el desplazamiento se limita a los paneles de opciones y archivos.
* Un error al aplicar una respuesta en segundo plano no detiene las siguientes
  actualizaciones de la interfaz.

## 1.2.0

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
