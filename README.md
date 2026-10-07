# 🎵 Youtify - YouTube MP3 & MP4 Downloader 🚀

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-brightgreen)
![yt-dlp](https://img.shields.io/badge/Powered_by-yt--dlp-red)
![Version](https://img.shields.io/badge/Version-v1.0.7-blue)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

Una aplicación de escritorio moderna, ligera, elegante y open source para descargar
música y videos de YouTube. Permite elegir entre audio MP3 de alta fidelidad y video MP4 en múltiples resoluciones,
descargar videos individuales o playlists completas, y gestionar descargas mediante una cola asíncrona desde una interfaz gráfica construida con Python y CustomTkinter.

> ⚠️ Descarga únicamente contenido que tengas derecho a guardar. El usuario es
> responsable de respetar los derechos de autor, los términos de servicio de
> cada plataforma y la legislación aplicable.

---

## ✨ Características principales

### 🎵 Descargas de música (Audio MP3)

* **Calidad seleccionable en kbps:** Elige entre **Máxima** (VBR sin pérdida perceptible), **320 kbps**, **256 kbps**, **192 kbps** o **128 kbps**.
* **Incrustación de carátulas oficial:** Descarga la miniatura en alta resolución y la inserta directamente en las etiquetas del archivo MP3.
* **Metadatos ID3 automáticos:** Inyecta artista, álbum, título y fecha para compatibilidad total con reproductores de música (Spotify, Apple Music, VLC, Windows Media).
* Guarda automáticamente los archivos en `Descargas\Youtify\Musica_Descargada`.

### 🎬 Descargas de video (MP4)

* **Resoluciones disponibles:** **Máxima**, **1080p**, **720p**, **480p** o **360p**.
* **Fusión inteligente:** Une automáticamente las pistas de video y audio de mejor calidad con FFmpeg en un único contenedor `.mp4`.
* Si un video de una playlist no tiene la resolución seleccionada, utiliza la mejor disponible sin detener la descarga.
* Guarda automáticamente los archivos en `Descargas\Youtify\descargas_videos`.

### 🖥️ Interfaz dinámica y moderna (Obsidian Palette)

* **Selector inteligente reactivo:** El menú de calidad cambia dinámicamente según el formato: si seleccionas MP3 muestra opciones en `kbps`; si seleccionas MP4 muestra resoluciones en `p`.
* **Previsualización automática:** Al pegar un enlace, detecta el video y carga miniatura, título, canal y duración en tiempo real.
* **Cola de descargas asíncrona:** Añade múltiples videos o playlists a la cola para descargarlos secuencialmente sin congelar la interfaz.
* **Consola de registro en vivo:** Barra de progreso ultra-fina, porcentaje exacto, velocidad de transferencia y tiempo estimado (ETA).

### 🔔 Notificaciones de actualización integradas

* Comprobación en segundo plano conectada directamente con **GitHub Releases**.
* Si se publica una nueva versión, muestra un diálogo modal para:
  * **Actualizar ahora:** Descarga la nueva versión directamente en tu navegador.
  * **Recordar más tarde:** Pospone el recordatorio durante 24 horas.
  * **No por ahora:** Cierra el aviso para la sesión actual.

### ⚙️ FFmpeg automático

La aplicación detecta, descarga y configura automáticamente FFmpeg y FFprobe cuando se
requieren para convertir audio o empaquetar video. No requiere instalación manual.

---

## 📥 Descargar el instalador para Windows

No necesitas instalar Python ni herramientas adicionales para usar Youtify.

### [⬇️ Descargar Youtify para Windows (Última versión)](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases/latest/download/Youtify-Setup.exe)

También puedes consultar el historial de versiones en
[GitHub Releases](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases).

1. Descarga `Youtify-Setup.exe`.
2. Ejecuta el instalador e inicia Youtify.
3. Pega un enlace de YouTube o playlist.
4. Elige `MP3 (audio)` o `MP4 (video)`.
5. Selecciona la calidad deseada y pulsa **Descargar ahora** o **Añadir a la cola**.

> Windows Defender puede mostrar una advertencia para ejecutables sin firma digital comercial. El instalador se compila de forma transparente mediante GitHub Actions desde este código fuente público.

---

## 🛠️ Requisitos para ejecutar desde el código fuente

* Windows 10 u 11.
* Python 3.12 o posterior.
* Node.js LTS recomendado para los desafíos JavaScript de YouTube.
* Conexión a Internet.

### 1. Clonar el repositorio

```powershell
git clone https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO.git
cd YOUTIFY-MUSICA-VIDEO
```

### 2. Crear entorno virtual e instalar dependencias

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Ejecutar la aplicación

```powershell
python main.py
```

---

## 📦 Compilar el ejecutable e instalador localmente

Si quieres generar tu propio binario compilado:

```powershell
python -m pip install pyinstaller
pyinstaller --noconsole --onefile --clean --icon=icon.ico --name Youtify main.py
```

El ejecutable se generará en `dist\Youtify.exe`.

### Generar el instalador con Inno Setup

```powershell
iscc installer.iss
```

El instalador quedará listo en la carpeta `installer\Youtify-Setup.exe`.

---

## 🚀 Publicar una nueva versión con CI/CD

El workflow de GitHub Actions en `.github/workflows/build-release.yml` compila y publica automáticamente la nueva versión al subir una etiqueta de versión:

```powershell
git add .
git commit -m "feat: preparar release v1.0.7"
git tag v1.0.7
git push origin main
git push origin v1.0.7
```

---

## 📂 Carpetas generadas

| Carpeta | Contenido |
| --- | --- |
| `Descargas\Youtify\Musica_Descargada` | Archivos MP3 con portada incrustada |
| `Descargas\Youtify\descargas_videos` | Archivos MP4 en alta resolución |
| `%LOCALAPPDATA%\Youtify\ffmpeg` | Binarios de FFmpeg y FFprobe |
| `%LOCALAPPDATA%\Youtify\update_state.json` | Registro de preferencias de actualización |

---

## 📄 Licencia

Este proyecto se distribuye bajo la [Licencia MIT](LICENSE).

Desarrollado con ☕ y Python por [jonathanZM15](https://github.com/jonathanZM15).
