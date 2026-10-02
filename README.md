# 🎵 Youtify - YouTube MP3 & MP4 Downloader 🚀

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-brightgreen)
![yt-dlp](https://img.shields.io/badge/Powered_by-yt--dlp-red)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

Una aplicación de escritorio moderna, ligera y open source para descargar
música y videos de YouTube. Permite elegir entre audio MP3 y video MP4,
descargar videos individuales o playlists completas y seleccionar la calidad
del video desde una interfaz gráfica sencilla construida con Python y
CustomTkinter.

> ⚠️ Descarga únicamente contenido que tengas derecho a guardar. El usuario es
> responsable de respetar los derechos de autor, los términos de servicio de
> cada plataforma y la legislación aplicable.

---

## ✨ Características principales

### 🎵 Descargas de música

* Convierte videos y playlists a audio MP3.
* Usa la mejor calidad de audio disponible.
* Guarda automáticamente los archivos en `Descargas\Youtify\Musica_Descargada`.

### 🎬 Descargas de video

* Descarga videos y playlists en formato MP4.
* Calidad máxima, 1080p, 720p, 480p o 360p.
* Si un video de una playlist no tiene la calidad seleccionada, utiliza la
  mejor calidad disponible sin detener toda la playlist.
* Guarda automáticamente los archivos en `Descargas\Youtify\descargas_videos`.

### 🖥️ Interfaz y funcionamiento

* Interfaz moderna adaptable al tema claro u oscuro del sistema.
* Barra de progreso y mensajes de estado legibles.
* El enlace se limpia automáticamente después de una descarga exitosa.
* Si ocurre un error, el enlace se conserva para poder reintentarlo.
* Rutas compatibles con ejecución como código fuente o como `.exe`.
* Icono personalizado incluido para la ventana y el ejecutable.

### ⚙️ FFmpeg automático

La aplicación descarga y configura automáticamente FFmpeg y FFprobe cuando se
necesitan para convertir audio o unir video y audio. Los componentes se guardan
en la carpeta local `ffmpeg`, sin requerir una instalación manual.

### 🛡️ Compatibilidad con los desafíos actuales de YouTube

La aplicación está preparada para utilizar Node.js junto con `yt-dlp` para
resolver algunos desafíos JavaScript de YouTube y reducir errores HTTP 403.
Esto no garantiza que YouTube no aplique límites temporales a una conexión o
dirección IP.

---

## 📥 Descargar el instalador

Si solo quieres utilizar la aplicación, no necesitas instalar Python.

### [⬇️ Descargar Youtify para Windows](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases/latest/download/Youtify-Setup.exe)

También puedes consultar todas las versiones en
[GitHub Releases](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases).

1. Descarga `Youtify-Setup.exe`.
2. Ejecuta el instalador.
3. Abre Youtify desde el menú Inicio o el acceso directo del escritorio.
4. Pega un enlace de YouTube.
5. Elige `MP3 (audio)` o `MP4 (video)`.
6. Selecciona la calidad y pulsa **Descargar ahora**.

> Windows Defender puede mostrar una advertencia para ejecutables sin firma
> digital. El instalador se genera automáticamente mediante GitHub Actions a
> partir del código fuente público de este repositorio.

---

## 🛠️ Requisitos para ejecutar desde el código fuente

* Windows 10 u 11.
* Python 3.12 o posterior.
* Node.js LTS recomendado para los desafíos JavaScript actuales de YouTube.
* Conexión a Internet.

### 1. Instalar Node.js

Descarga la versión LTS desde [nodejs.org](https://nodejs.org/). Durante la
instalación, asegúrate de agregar Node.js al `PATH` y reinicia la terminal.

Puedes comprobar la instalación con:

```powershell
node --version
```

### 2. Clonar el repositorio

```powershell
git clone https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO.git
cd YOUTIFY-MUSICA-VIDEO
```

### 3. Crear un entorno virtual e instalar dependencias

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```powershell
python app.py
```

---

## 📦 Compilar el ejecutable manualmente

Si quieres crear tu propio `.exe`, instala PyInstaller:

```powershell
python -m pip install pyinstaller
```

Después ejecuta:

```powershell
pyinstaller --noconsole --onefile --clean --icon=icon.ico --name Youtify app.py
```

El ejecutable se generará en:

```text
dist\Youtify.exe
```

El parámetro `--onefile` crea un único ejecutable y `--noconsole` evita que
aparezca una ventana negra de terminal junto a la aplicación.

### Crear un instalador local

El archivo `installer.iss` contiene la configuración para Inno Setup. Si tienes
[Inno Setup](https://jrsoftware.org/isinfo.php) instalado:

```powershell
iscc installer.iss
```

El instalador aparecerá en la carpeta `installer`.

---

## 🚀 Publicar una nueva versión

El workflow de GitHub Actions ubicado en
`.github/workflows/build-release.yml` compila automáticamente el ejecutable y
el instalador en Windows.

Para publicar una nueva versión:

```powershell
git add .
git commit -m "Prepare release v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

Al subir una etiqueta con el formato `vX.Y.Z`, GitHub Actions:

1. Instala Python y las dependencias.
2. Compila `Youtify.exe`.
3. Crea `Youtify-Setup.exe`.
4. Publica el instalador en GitHub Releases.

---

## 📂 Carpetas generadas

| Carpeta | Contenido |
| --- | --- |
| `Descargas\Youtify\Musica_Descargada` | Archivos MP3 |
| `Descargas\Youtify\descargas_videos` | Archivos MP4 |
| `%LOCALAPPDATA%\Youtify\ffmpeg` | FFmpeg y FFprobe descargados automáticamente |

---

## ⚠️ Solución de problemas

### Error HTTP 403 / Forbidden

Actualiza `yt-dlp` y comprueba Node.js:

```powershell
python -m pip install --upgrade -r requirements.txt
node --version
```

YouTube puede limitar temporalmente una dirección IP después de muchos
intentos. Espera un tiempo antes de volver a descargar o prueba con una
conexión permitida.

### FFmpeg no se pudo descargar

Comprueba que tienes conexión a Internet y permisos de escritura en la carpeta
del programa. La aplicación necesita descargar `ffmpeg.exe` y `ffprobe.exe`
para convertir MP3 o unir video y audio.

### El antivirus detecta el ejecutable

Los ejecutables creados con PyInstaller pueden producir falsos positivos porque
no tienen una firma digital comercial. Puedes revisar el código fuente y
compilar el programa localmente antes de añadir una excepción.

---

## 🤝 Contribuir

Youtify es un proyecto open source y las contribuciones son bienvenidas.

1. Haz un fork del repositorio.
2. Crea una rama para tu cambio.
3. Prueba la aplicación en MP3 y MP4.
4. Envía un pull request con una descripción clara.

También puedes abrir un issue para reportar errores o proponer mejoras.

---

## 📄 Licencia

Este proyecto se distribuye bajo la [Licencia MIT](LICENSE).

Desarrollado con ☕ y Python.
