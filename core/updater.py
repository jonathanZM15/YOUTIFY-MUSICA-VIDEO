from dataclasses import dataclass
import json
import logging
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional
from packaging.version import Version, InvalidVersion
from core.storage import JsonStore

from config.settings import (
    APP_NAME,
    APP_VERSION,
    GITHUB_API_LATEST_RELEASE,
    GITHUB_RELEASES_URL,
    UPDATE_STATE_FILE,
    UPDATE_CHECK_INTERVAL_SEC,
    UPDATE_ASSET_NAME,
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
    sha256: str = ""
    size: int = 0


class Updater:
    """Gestor de ciclo de vida y actualizaciones: GitHub Releases y motor yt-dlp."""

    # Lock para proteger acceso concurrente a update_state.json
    _state_lock = threading.Lock()

    @staticmethod
    def parse_version(v_str: str) -> tuple[int, ...]:
        """Extrae tupla numérica de versión semántica (ej. 'v1.0.7' -> (1, 0, 7))."""
        numbers = re.findall(r"\d+", v_str)
        return tuple(map(int, numbers)) if numbers else (0,)

    @classmethod
    def is_newer_version(cls, remote_tag: str, current_version: str) -> bool:
        """Determina si la versión remota es estrictamente superior a la local."""
        try:
            return Version(remote_tag.lstrip("vV")) > Version(current_version.lstrip("vV"))
        except InvalidVersion:
            return False

    @classmethod
    def _load_state(cls) -> dict:
        try:
            if UPDATE_STATE_FILE.exists():
                with open(UPDATE_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    @classmethod
    def _save_state(cls, data: dict) -> None:
        try:
            JsonStore(UPDATE_STATE_FILE).write(data)
        except Exception:
            pass

    @classmethod
    def _read_update_state(cls) -> dict:
        with cls._state_lock:
            return cls._load_state()

    @classmethod
    def _write_update_state(cls, data: dict) -> None:
        with cls._state_lock:
            cls._save_state(data)

    @classmethod
    def _update_state(cls, **updates) -> dict:
        """Adquiere el lock, lee el estado en disco, aplica updates, guarda y retorna el estado."""
        with cls._state_lock:
            state = cls._load_state()
            state.update(updates)
            cls._save_state(state)
            return state

    @classmethod
    def should_notify(cls, remote_tag: str) -> bool:
        """Comprueba si el usuario pospuso la notificación de esta versión."""
        state = cls._read_update_state()
        if state.get("last_notified_tag") == remote_tag:
            return False
        postponed_until = state.get("postponed_until", 0)
        postponed_tag = state.get("postponed_tag", "")

        # Si pospuso esta misma versión y aún no expira el tiempo, silenciar
        if postponed_tag == remote_tag and isinstance(postponed_until, (int, float)) and time.time() < postponed_until:
            return False
        return True

    @classmethod
    def postpone_update(cls, remote_tag: str, hours: int = 24) -> None:
        """Pospone el aviso para recordar al usuario más tarde (por defecto 24 horas)."""
        cls._update_state(
            postponed_until=time.time() + (hours * 3600),
            postponed_tag=remote_tag,
        )

    @classmethod
    def check_github_release(cls) -> Optional[ReleaseInfo]:
        """Consulta GitHub Releases API de forma segura y devuelve info si hay actualización."""
        try:
            with cls._state_lock:
                state = cls._load_state()
                last = state.get("last_check", 0)
                now = time.time()
                if isinstance(last, (int, float)) and 0 <= now - last < UPDATE_CHECK_INTERVAL_SEC:
                    return None
                state["last_check"] = now
                cls._save_state(state)
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
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    return None
                data = json.loads(raw.decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            if not re.fullmatch(r"v?\d+\.\d+\.\d+", tag_name) or data.get("draft") or data.get("prerelease"):
                return None

            if not cls.is_newer_version(tag_name, APP_VERSION):
                return None

            asset = next((a for a in data.get("assets", []) if a.get("name") == UPDATE_ASSET_NAME), None)
            if not asset:
                return None
            download_url = asset.get("browser_download_url", "")
            from core.managed_updates import valid_package_url, MAX_ARCHIVE_BYTES
            digest = asset.get("digest", "") or ""
            size = asset.get("size", 0)
            if not valid_package_url(download_url, tag_name) or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest) or not isinstance(size, int) or not 0 < size <= MAX_ARCHIVE_BYTES:
                return None

            html_url = data.get("html_url", GITHUB_RELEASES_URL)
            if not cls._valid_release_url(html_url):
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
                sha256=digest[7:],
                size=size,
            )
        except Exception:
            return None

    @classmethod
    def check_app_update_async(cls, callback: Callable[[ReleaseInfo], None]) -> None:
        """Prepara el paquete completo fuera de Tk; el aviso llega solo al estar listo."""
        def _task():
            if not getattr(sys, "frozen", False):
                return  # Development never activates a packaged release.
            try:
                release = cls.check_github_release()
                if release:
                    from core.managed_updates import ManagedUpdates
                    ManagedUpdates().prepare(release)
                    if cls.should_notify(release.tag_name):
                        callback(release)
            except Exception:
                logging.getLogger(__name__).exception("No se pudo preparar la actualización; se reintentará más tarde")

        threading.Thread(target=_task, daemon=True).start()

    @classmethod
    def check_and_update_async(cls, log_callback: Optional[Callable[[str], None]] = None) -> None:
        """Report the bundled engine version. Never mutate an environment at application startup."""
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

        threading.Thread(target=_task, daemon=True).start()

    @staticmethod
    def _valid_release_url(url):
        from urllib.parse import urlparse
        from config.settings import GITHUB_REPO
        if not isinstance(url, str):
            return False
        parsed = urlparse(url)
        return (parsed.scheme == "https" and parsed.netloc == "github.com"
                and parsed.path.startswith(f"/{GITHUB_REPO}/releases"))
