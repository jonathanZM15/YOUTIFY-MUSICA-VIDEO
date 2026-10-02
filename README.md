# Youtify

<div align="center">

**Descargador de música y videos de YouTube para Windows**

[![Build](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/actions/workflows/build-release.yml/badge.svg)](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/actions/workflows/build-release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[Descargar instalador](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases/latest/download/Youtify-Setup.exe)** ·
**[Ver versiones](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases)** ·
**[Código fuente](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO)**

</div>

## Sobre el proyecto

Youtify es una aplicación open source para Windows que permite descargar:

- Audio en MP3.
- Videos en MP4.
- Videos individuales o playlists completas.
- Varias calidades de video: máxima, 1080p, 720p, 480p y 360p.

La aplicación usa `yt-dlp` y FFmpeg. Descarga FFmpeg automáticamente cuando
se necesita y guarda los archivos en carpetas separadas junto a la aplicación.

## Descargar y usar sin instalar Python

La forma más sencilla es descargar el instalador:

1. Entra en **[Descargar instalador](https://github.com/jonathanZM15/YOUTIFY/releases/latest/download/Youtify-Setup.exe)**.
2. Ejecuta `Youtify-Setup.exe`.
3. Abre Youtify desde el menú Inicio o el acceso directo del escritorio.
4. Pega un enlace, selecciona MP3 o MP4 y pulsa **Descargar ahora**.

El instalador se genera automáticamente desde GitHub Actions y se publica en
la sección [Releases](https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO/releases).

> Windows Defender puede mostrar una advertencia para ejecutables sin firma
> digital. El instalador es generado desde este código fuente open source.

## Ejecutar desde el código fuente

Se necesita Python 3.12 o posterior. Node.js LTS es recomendable para ayudar a
resolver los desafíos actuales de YouTube.

```powershell
git clone https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO.git
cd YOUTIFY-MUSICA-VIDEO
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

## Compilar localmente

```powershell
python -m pip install pyinstaller
pyinstaller --noconsole --onefile --icon=icon.ico --name Youtify app.py
```

El ejecutable aparecerá en `dist\Youtify.exe`.

## Publicar una nueva versión

Los mantenedores pueden generar el instalador automáticamente creando una
etiqueta de versión:

```powershell
git add .
git commit -m "Prepare release v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

GitHub Actions compilará el programa y publicará `Youtify-Setup.exe` en una
Release nueva. El enlace de descarga del principio siempre apunta a la última
versión.

## Carpetas de salida

- `Musica_Descargada`: archivos MP3.
- `descargas_videos`: archivos MP4.
- `ffmpeg`: componentes descargados automáticamente para convertir y unir archivos.

Al terminar correctamente una descarga, el enlace se limpia automáticamente.
Si ocurre un error, el enlace se conserva para poder reintentarlo.

## Solución de problemas

### HTTP 403 o Forbidden

Actualiza las dependencias y comprueba que Node.js LTS esté instalado:

```powershell
python -m pip install --upgrade -r requirements.txt
node --version
```

YouTube puede limitar temporalmente una IP. En ese caso, espera antes de
realizar muchos intentos consecutivos.

## Contribuir

Las contribuciones son bienvenidas. Puedes abrir un issue para reportar un
problema o un pull request con una mejora. Antes de enviar cambios:

1. Comprueba que la aplicación inicia.
2. Verifica que MP3 y MP4 sigan funcionando.
3. Mantén los cambios enfocados y documentados.

## Licencia

Este proyecto se distribuye bajo la [Licencia MIT](LICENSE).

El usuario es responsable de respetar los derechos de autor, los términos de
servicio de cada plataforma y la legislación aplicable al contenido que
descargue.
