from dataclasses import dataclass
import json
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from config.settings import (
    APP_NAME,
    APP_VERSION,
    GITHUB_API_LATEST_RELEASE,
    GITHUB_RELEASES_URL,
    UPDATE_STATE_FILE,
)


@dataclass
class ReleaseInfo:
    """Información estructurada de una versión disponible en GitHub Releases."""
    tag_name: str
    version: str
    title: str
    release_notes: str
    html_url: str
    download_url: str


class Updater:
    """Gestor de ciclo de vida y actualizaciones: GitHub Releases y motor yt-dlp."""

    @staticmethod
    def parse_version(v_str: str) -> tuple[int, ...]:
        """Extrae tupla numérica de versión semántica (ej. 'v1.0.7' -> (1, 0, 7))."""
        numbers = re.findall(r"\d+", v_str)
        return tuple(map(int, numbers)) if numbers else (0,)

    @classmethod
    def is_newer_version(cls, remote_tag: str, current_version: str) -> bool:
        """Determina si la versión remota es estrictamente superior a la local."""
        return cls.parse_version(remote_tag) > cls.parse_version(current_version)

    @classmethod
    def _read_update_state(cls) -> dict:
        try:
            if UPDATE_STATE_FILE.exists():
                with open(UPDATE_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    @classmethod
    def _write_update_state(cls, data: dict) -> None:
        try:
            UPDATE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(UPDATE_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def should_notify(cls, remote_tag: str) -> bool:
        """Comprueba si el usuario pospuso la notificación de esta versión."""
        state = cls._read_update_state()
        postponed_until = state.get("postponed_until", 0)
        postponed_tag = state.get("postponed_tag", "")

        # Si pospuso esta misma versión y aún no expira el tiempo, silenciar
        if postponed_tag == remote_tag and time.time() < postponed_until:
            return False
        return True

    @classmethod
    def postpone_update(cls, remote_tag: str, hours: int = 24) -> None:
        """Pospone el aviso para recordar al usuario más tarde (por defecto 24 horas)."""
        state = cls._read_update_state()
        state["postponed_until"] = time.time() + (hours * 3600)
        state["postponed_tag"] = remote_tag
        cls._write_update_state(state)

    @classmethod
    def check_github_release(cls) -> Optional[ReleaseInfo]:
        """Consulta GitHub Releases API de forma segura y devuelve info si hay actualización."""
        try:
            request = urllib.request.Request(
                GITHUB_API_LATEST_RELEASE,
                headers={
                    "User-Agent": f"{APP_NAME}-Desktop/{APP_VERSION}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status != 200:
                    return None
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            if not tag_name:
                return None

            if not cls.is_newer_version(tag_name, APP_VERSION):
                return None

            if not cls.should_notify(tag_name):
                return None

            # Buscar asset instalador ejecutable .exe en la release
            download_url = data.get("html_url", GITHUB_RELEASES_URL)
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url", download_url)
                    if "setup" in name.lower():
                        break

            # Ciberseguridad: Solo admitir URLs HTTPS legítimas para mitigar inyecciones de esquemas arbitrarios
            if not isinstance(download_url, str) or not download_url.startswith("https://"):
                download_url = GITHUB_RELEASES_URL

            html_url = data.get("html_url", GITHUB_RELEASES_URL)
            if not isinstance(html_url, str) or not html_url.startswith("https://"):
                html_url = GITHUB_RELEASES_URL

            clean_ver = tag_name.lstrip("vV")
            raw_body = data.get("body", "") or "Nueva versión con mejoras y correcciones."
            # Limitar notas de versión a 400 caracteres para legibilidad limpia en GUI
            body_summary = raw_body[:400] + ("..." if len(raw_body) > 400 else "")

            return ReleaseInfo(
                tag_name=tag_name,
                version=clean_ver,
                title=data.get("name", f"Youtify v{clean_ver}"),
                release_notes=body_summary.strip(),
                html_url=html_url,
                download_url=download_url,
            )
        except Exception:
            return None

    @classmethod
    def check_app_update_async(cls, callback: Callable[[ReleaseInfo], None]) -> None:
        """Verifica en segundo plano sin bloquear interfaz gráfica ni el hilo principal."""
        def _task():
            release = cls.check_github_release()
            if release:
                callback(release)

        threading.Thread(target=_task, daemon=True).start()

    @classmethod
    def check_and_update_async(cls, log_callback: Optional[Callable[[str], None]] = None) -> None:
        """Comprueba de forma segura actualizaciones de dependencias en modo desarrollo y reporta versión."""
        def _task():
            current_ver = "desconocida"
            try:
                import yt_dlp.version
                current_ver = getattr(yt_dlp.version, "__version__", "desconocida")
                if log_callback:
                    log_callback(f"[*] Motor yt-dlp: versión instalada {current_ver}")
            except Exception:
                pass

            state = cls._read_update_state()
            last_updated = state.get("yt_dlp_last_updated")
            if last_updated and log_callback:
                log_callback(f"[*] yt-dlp: última actualización registrada el {last_updated}")

            if getattr(sys, "frozen", False):
                return

            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "--no-warn-script-location"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    if "Requirement already satisfied" not in result.stdout:
                        try:
                            import importlib
                            import yt_dlp.version
                            importlib.reload(yt_dlp.version)
                            current_ver = getattr(yt_dlp.version, "__version__", current_ver)
                        except Exception:
                            pass
                        state["yt_dlp_last_updated"] = now_str
                        cls._write_update_state(state)
                        if log_callback:
                            log_callback(f"[*] yt-dlp actualizado a la versión más reciente ({current_ver}) el {now_str}.")
                    else:
                        if not last_updated:
                            state["yt_dlp_last_updated"] = now_str
                            cls._write_update_state(state)
                        if log_callback:
                            log_callback(f"[*] yt-dlp verificado: ya se encuentra en la versión más reciente ({current_ver}).")
            except Exception:
                pass

        threading.Thread(target=_task, daemon=True).start()
