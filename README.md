<div align="center">

# 🎵 Youtify — YouTube MP3 & MP4 Downloader 🚀

**Tu música y tus videos, en un solo lugar.**

Una aplicación de escritorio para Windows que convierte tus enlaces de YouTube en
archivos MP3 o MP4, con playlists, carátulas y una cola que tú controlas.

[![Versión](https://img.shields.io/github/v/release/jonathanZM15/YOUTIFY-MUSICA-VIDEO?label=Versi%C3%B3n&color=3b82f6)](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases/latest)
![Python](https://img.shields.io/badge/Python-3.12-3776ab)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-22c55e)
![yt-dlp](https://img.shields.io/badge/Powered_by-yt--dlp-ef4444)
[![Build](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/actions/workflows/build-release.yml/badge.svg?branch=main)](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/actions/workflows/build-release.yml)
[![Licencia MIT](https://img.shields.io/badge/Licencia-MIT-eab308)](LICENSE)

### [⬇️ Descargar Youtify para Windows](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases/latest/download/Youtify-Setup.exe)

[📦 Versiones publicadas](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases) · [📝 Novedades](CHANGELOG.md) · [🐛 Reportar un problema](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/issues)

**Versión actual: v1.3.4 · Windows 10/11 de 64 bits**

</div>

---

## ✨ Características principales

### 🎵 Tu música en MP3

- **Calidad a tu elección:** Máxima (VBR), 320, 256, 192 o 128 kbps.
- **Carátula opcional:** miniatura incrustada en el archivo, optimizada como JPEG de hasta 600 px.
- **Metadatos automáticos:** etiquetas como título, artista y fecha, según la información disponible.
- **Carpeta personalizable:** elige dónde guardar tu música y abre el resultado desde la cola.

### 🎬 Tus videos en MP4

- **Resoluciones disponibles:** Máxima, 1080p, 720p, 480p o 360p.
- **Audio y video juntos:** FFmpeg une las pistas y prepara el archivo MP4 final.
- **Enlaces individuales o playlists:** utiliza el mismo flujo para guardar uno o varios videos.

La calidad final depende de los formatos disponibles en el video original.

### 📚 Playlists y una cola bajo tu control

- Añade videos, Shorts o playlists para descargarlos de forma secuencial.
- Usa **Descargar ahora** para empezar o **Añadir a la cola** para preparar el trabajo.
- **Pausa, cancela y reintenta** desde la misma ventana. La pausa deja terminar el archivo actual.
- La cola se guarda entre sesiones; los pendientes esperan a que pulses **Iniciar cola** al volver.
- Los errores se muestran por elemento y permiten continuar con los siguientes.
- Capacidad de hasta **2000 trabajos pendientes**, con un aviso si una lista supera el espacio disponible.

### 📊 El progreso de tu archivo y de tu playlist

| Lo que descargas | Lo que ves |
| --- | --- |
| Una canción o un video individual | Una barra del archivo actual, de 0 a 100 %. |
| Una playlist | La barra del archivo actual y otra con el avance total y el contador de canciones guardadas. |

El total incluye el avance parcial de la canción en curso, con el mismo peso para cada
archivo. Cada playlist conserva su propio contador, incluso al pausar o limpiar el historial.
Los errores y las cancelaciones aparecen por separado: **100 % total significa que terminó
de procesarse la lista**; el contador indica cuántos archivos se guardaron correctamente.

### 🖥️ Una interfaz que acompaña la descarga

- **Temas oscuro, claro y del sistema.**
- **Dos columnas:** opciones a la izquierda; cola y actividad a la derecha.
- **Selectores redondeados** de formato, calidad y tema, con navegación por teclado.
- **Calidad reactiva:** opciones en kbps para MP3 y resoluciones para MP4.
- **Vista previa automática:** título, canal, duración y miniatura cuando están disponibles.
- **Progreso en vivo:** velocidad y tiempo restante, con un registro de actividad en su propia pestaña.
- **Una sola instancia:** abrir Youtify de nuevo recupera la ventana existente, incluso minimizada.

---

## 📥 Instalar y empezar

**El instalador incluye Python, FFmpeg, FFprobe, Node.js y los scripts EJS necesarios.**

1. Descarga [`Youtify-Setup.exe`](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases/latest/download/Youtify-Setup.exe) y ejecuta el instalador.
2. Abre Youtify y pega un enlace de YouTube, Shorts o playlist.
3. Elige **MP3 (audio)** o **MP4 (video)** y selecciona la calidad.
4. Activa **Incluir carátula** si quieres incrustar la miniatura.
5. Pulsa **Descargar ahora** o prepara varios enlaces con **Añadir a la cola**.

> Descarga únicamente contenido que tengas derecho a guardar.

### ⌨️ Atajos que te ahorran clics

| Atajo | Acción |
| --- | --- |
| `Ctrl + L` | Enfocar el campo del enlace. |
| `Ctrl + Enter` | Añadir el enlace e iniciar la descarga. |
| `↑` / `↓` y `Enter` | Recorrer y elegir opciones en un selector abierto. |
| `Esc` | Cerrar el selector sin cambiar la opción. |
| `Tab` | Pasar al siguiente control. |

---

## 🔄 Actualizaciones automáticas

Youtify consulta **GitHub Releases en segundo plano**, como máximo cada seis horas.
Cuando hay una versión estable más reciente:

1. Descarga el paquete de actualización.
2. Verifica su SHA-256 y comprueba que el nuevo ejecutable incluya los componentes necesarios.
3. Muestra **un aviso discreto por versión**, cuando está lista.
4. Aplica la actualización **al volver a abrir Youtify**, sin interrumpir las descargas.

Si la conexión o la verificación fallan, conserva la versión actual y reintenta en una
consulta posterior. Tus accesos directos siguen abriendo la aplicación actualizada.

> **¿Vienes de una versión anterior a la 1.3.0?** Instala la última versión una vez
> para incorporar el nuevo actualizador. Las siguientes actualizaciones se aplican
> desde la aplicación, sin volver a ejecutar un instalador.

---

## 📂 ¿Dónde quedan tus archivos?

| Ubicación predeterminada | Contenido |
| --- | --- |
| `%USERPROFILE%\Downloads\Youtify\Musica_Descargada` | Archivos MP3. |
| `%USERPROFILE%\Downloads\Youtify\descargas_videos` | Archivos MP4. |
| `%LOCALAPPDATA%\Youtify` | Preferencias, cola, diagnóstico y versiones preparadas. |

Puedes cambiar la carpeta de descarga desde **Guardar en → Cambiar** y recuperar la
ubicación predeterminada con **Restablecer**.

<details>
<summary><strong>🔎 Preferencias y diagnóstico</strong></summary>

Dentro de `%LOCALAPPDATA%\Youtify`:

| Archivo o carpeta | Función |
| --- | --- |
| `preferences.json` | Formato, calidad, carpeta y tema elegidos. |
| `queue.json` | Pendientes, contadores de playlists y hasta 100 resultados recientes. |
| `update_state.json` | Última consulta y versión ya avisada. |
| `active_version.json` y `versions` | Versión verificada que abrirá la aplicación. |
| `logs\youtify.log` | Diagnóstico rotativo: hasta cuatro archivos de 2 MB. |

El registro puede contener enlaces, títulos y rutas; no se envía automáticamente.
`YOUTIFY_DATA_DIR` permite usar una carpeta de datos distinta para desarrollo o pruebas.

</details>

---

## 🛠️ Para desarrolladores

<details>
<summary><strong>Ejecutar desde el código fuente</strong></summary>

Entorno verificado: **Windows 10/11 de 64 bits y Python 3.12**.

```powershell
git clone https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO.git
cd YOUTIFY-MUSICA-VIDEO

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/prepare_components.py
.\.venv\Scripts\python.exe main.py
```

`prepare_components.py` descarga versiones fijadas de FFmpeg, FFprobe y Node.js,
verifica sus hashes y prepara los componentes locales. El actualizador automático
de la aplicación empaquetada permanece desactivado en modo de desarrollo.

`requirements-lock.txt` reproduce el entorno completo; `requirements.txt` contiene
las dependencias directas y `requirements-build.txt` añade el compilador.

</details>

<details>
<summary><strong>Pruebas y compilación local</strong></summary>

Con el entorno y los componentes preparados:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/build.py
iscc installer.iss
.\.venv\Scripts\python.exe scripts/package_release.py
```

La compilación del instalador requiere **Inno Setup 6.5.4 o posterior**.
`build.py` ejecuta las pruebas, genera la información de versión desde `APP_VERSION`,
compila `Youtify.spec` y comprueba el ejecutable empaquetado.

El programa completo queda en `dist\Youtify\` y el instalador en
`installer\Youtify-Setup.exe`. Conserva la carpeta completa de `dist\Youtify` al
usar esa distribución: el ejecutable necesita sus archivos auxiliares.

Las pruebas de integración usan medios sintéticos servidos por HTTP local para
verificar conversión, etiquetas, portada y MP4. Las de interfaz crean widgets reales
con datos temporales aislados.

</details>

### 🚀 Publicar una versión desde GitHub

El workflow valida y compila con cada push a `main`. Cuando recibe una etiqueta
`vX.Y.Z` que coincide con `APP_VERSION`, también publica la release.

1. Actualiza `APP_VERSION` en `config/settings.py` y documenta las novedades.
2. Ejecuta las pruebas con los componentes preparados.
3. Crea el commit y la etiqueta de la nueva versión:

```powershell
$releaseVersion = .\.venv\Scripts\python.exe -c "from config.settings import APP_VERSION; print(APP_VERSION)"
git add .
git commit -m "release: v$releaseVersion"
git tag -a "v$releaseVersion" -m "Youtify v$releaseVersion"
git push --atomic origin main "v$releaseVersion"
```

GitHub Actions genera los archivos y los publica en
[Releases](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases):

| Archivo | Uso |
| --- | --- |
| `Youtify-Setup.exe` | Primera instalación, migración o reparación. |
| `Youtify-Update-x64.zip` | Paquete que gestiona el actualizador de la aplicación. |
| `SHA256SUMS.txt` | Sumas de comprobación de ambos archivos. |

Los binarios y temporales de compilación están excluidos del repositorio mediante `.gitignore`.
El historial detallado de mejoras está en [CHANGELOG.md](CHANGELOG.md).

---

## 💬 ¿Encontraste un problema?

Revisa el detalle del elemento en la cola y la pestaña **Actividad**. YouTube puede
restringir videos o limitar solicitudes; en esos casos, la aplicación muestra el error
y permite reintentar más tarde.

Puedes [abrir un issue](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/issues)
con los pasos para reproducirlo y el mensaje de error. Revisa el registro antes de
compartirlo si contiene enlaces o rutas personales.

## 📄 Licencia y créditos

Youtify se distribuye bajo la [Licencia MIT](LICENSE). Los componentes incluidos
conservan sus propias licencias: [avisos de terceros](THIRD_PARTY_NOTICES.md).

Desarrollado con ☕ y Python por [jonathanZM15](https://github.com/jonathanZM15).
