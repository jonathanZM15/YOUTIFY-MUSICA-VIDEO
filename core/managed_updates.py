"""Verified per-user update packages. Installed shortcuts remain stable launchers.

Packages are staged in a new version directory and activated atomically; running
executables are never overwritten, including installations under Program Files.
"""
import hashlib
import json
import logging
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

from packaging.version import Version
from config.settings import (ACTIVE_VERSION_FILE, APP_VERSION, GITHUB_REPO,
    UPDATE_ASSET_NAME, UPDATE_VERSIONS_DIR)
from core.storage import JsonStore

VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
MAX_ARCHIVE_BYTES = 600 * 1024 * 1024
MAX_EXTRACTED_BYTES = 2 * 1024 * 1024 * 1024
log = logging.getLogger(__name__)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def valid_package_url(url, tag):
    parsed = urllib.parse.urlparse(url)
    return (parsed.scheme == "https" and parsed.netloc == "github.com"
        and parsed.path == f"/{GITHUB_REPO}/releases/download/{tag}/{UPDATE_ASSET_NAME}")


class ManagedUpdates:
    def __init__(self, root=None, pointer=None, current_version=APP_VERSION, opener=None, probe=None):
        self.root = Path(root) if root is not None else UPDATE_VERSIONS_DIR
        self.pointer = pointer or JsonStore(ACTIVE_VERSION_FILE)
        self.current_version = current_version
        self.opener = opener or urllib.request.urlopen
        self.probe = probe or self._probe

    @staticmethod
    def _probe(executable, report):
        result = subprocess.run([str(executable), "--self-check", str(report)],
            capture_output=True, timeout=45, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode != 0:
            raise RuntimeError("El paquete de actualización no pudo iniciarse.")
        return json.loads(report.read_text(encoding="utf-8"))

    def prepare(self, release):
        version = release.version
        if not VERSION_RE.fullmatch(version) or Version(version) <= Version(self.current_version):
            raise ValueError("Versión de actualización inválida.")
        if not valid_package_url(release.download_url, release.tag_name):
            raise ValueError("Origen de actualización no autorizado.")
        if not re.fullmatch(r"[a-f0-9]{64}", release.sha256):
            raise ValueError("La actualización no tiene un SHA-256 verificable.")
        if not isinstance(release.size, int) or not 0 < release.size <= MAX_ARCHIVE_BYTES:
            raise ValueError("Tamaño de actualización inválido.")
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / version
        marker = target / ".verified-update.json"
        if target.exists():
            cached = JsonStore(marker).read({})
            if isinstance(cached, dict) and cached.get("archive_sha256") == release.sha256 and \
                    (target / "Youtify.exe").is_file() and sha256(target / "Youtify.exe") == cached.get("exe_sha256"):
                return self._activate(version, cached)
            raise RuntimeError("Ya existe un paquete diferente con esa versión.")
        with tempfile.TemporaryDirectory(prefix="staging-", dir=self.root) as temporary:
            staging = Path(temporary)
            archive = staging / "update.zip"
            digest, total = hashlib.sha256(), 0
            request = urllib.request.Request(release.download_url, headers={"User-Agent": "Youtify-Updater"})
            with self.opener(request, timeout=30) as response, archive.open("wb") as destination:
                final = urllib.parse.urlparse(response.geturl())
                if final.scheme != "https" or not (final.hostname == "github.com" or
                        (final.hostname or "").endswith(".githubusercontent.com")):
                    raise ValueError("Redirección de actualización no autorizada.")
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    total += len(chunk)
                    if total > release.size or total > MAX_ARCHIVE_BYTES:
                        raise ValueError("La actualización excede su tamaño declarado.")
                    destination.write(chunk)
                    digest.update(chunk)
            if total != release.size or digest.hexdigest() != release.sha256:
                raise ValueError("La actualización no supera la verificación SHA-256.")
            import zipfile
            with zipfile.ZipFile(archive) as zipped:
                entries = zipped.infolist()
                if len(entries) > 15000 or sum(e.file_size for e in entries) > MAX_EXTRACTED_BYTES:
                    raise ValueError("El paquete de actualización es demasiado grande.")
                names = set()
                for entry in entries:
                    path = PurePosixPath(entry.filename.replace("\\", "/"))
                    if path.is_absolute() or ".." in path.parts or ":" in entry.filename or \
                            not path.parts or path.parts[0] != "Youtify" or stat.S_ISLNK(entry.external_attr >> 16) or \
                            any(p.endswith((".", " ")) or PureWindowsPath(p).is_reserved() for p in path.parts):
                        raise ValueError("El paquete contiene una ruta no permitida.")
                    normalized = str(path).casefold()
                    if normalized in names:
                        raise ValueError("El paquete contiene rutas duplicadas.")
                    names.add(normalized)
                manifest_entry = zipped.getinfo("Youtify/update-manifest.json")
                if manifest_entry.file_size > 8192:
                    raise ValueError("Manifiesto de actualización inválido.")
                manifest = json.loads(zipped.read(manifest_entry))
                if manifest != {"schema": 1, "app": "Youtify", "version": version, "platform": "win-x64", "entrypoint": "Youtify.exe"}:
                    raise ValueError("El paquete no corresponde a esta aplicación o versión.")
                zipped.extractall(staging)
            package = staging / "Youtify"
            for name in ("Youtify.exe", "ffmpeg/ffmpeg.exe", "ffmpeg/ffprobe.exe", "runtime/node.exe"):
                if not (package / name).is_file():
                    raise ValueError("Faltan componentes en la actualización.")
            report = self.probe(package / "Youtify.exe", staging / "probe.json")
            if report.get("version") != version or not all(report.get(k) for k in
                    ("frozen", "ffmpeg", "ffprobe", "javascript", "ejs", "icon")):
                raise ValueError("La comprobación del nuevo ejecutable falló.")
            verified = {"archive_sha256": release.sha256, "exe_sha256": sha256(package / "Youtify.exe")}
            JsonStore(package / ".verified-update.json").write(verified)
            os.replace(package, target)
            return self._activate(version, verified)

    def _activate(self, version, verified):
        old = self.pointer.read({})
        if isinstance(old, dict) and old.get("version") == version:
            previous = old.get("previous", {})
        else:
            previous = {k: v for k, v in old.items() if k != "previous"} if isinstance(old, dict) else {}
        state = {"version": version, "source": GITHUB_REPO, **verified, "previous": previous}
        self.pointer.write(state)
        return self.root / version / "Youtify.exe"

    def ready_executable(self):
        state = self.pointer.read({})
        if not isinstance(state, dict) or state.get("source") != GITHUB_REPO:
            return None
        version = state.get("version", "")
        if not isinstance(version, str) or not VERSION_RE.fullmatch(version) or Version(version) <= Version(self.current_version):
            return None
        directory = self.root / version
        executable = directory / "Youtify.exe"
        if not directory.resolve().is_relative_to(self.root.resolve()) or not executable.is_file():
            return None
        if sha256(executable) != state.get("exe_sha256"):
            log.error("La actualización activa fue modificada; se conserva la versión instalada.")
            return None
        return executable

    def redirect(self, release_lock=None, frozen=None, launcher=None):
        if not (getattr(sys, "frozen", False) if frozen is None else frozen):
            return False
        try:
            executable = self.ready_executable()
        except (OSError, ValueError):
            log.exception("No se pudo leer la actualización; se conserva la versión instalada.")
            return False
        if executable is None:
            return False
        if executable.resolve() == Path(sys.executable).resolve():
            return False
        if release_lock:
            release_lock()
        try:
            (launcher or subprocess.Popen)([str(executable)], cwd=str(executable.parent), close_fds=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True
        except OSError:
            state = self.pointer.read({})
            try:
                self.pointer.write(state.get("previous", {}) if isinstance(state, dict) else {})
            except OSError:
                log.exception("No se pudo restaurar el registro de actualización.")
            log.exception("No se pudo iniciar la actualización; se conserva la versión anterior.")
            return False
