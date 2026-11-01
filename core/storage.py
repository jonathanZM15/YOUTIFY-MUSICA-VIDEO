"""Small, atomic JSON stores. Never leave half a preferences/queue file on disk."""
import json
import logging
import os
import tempfile
import threading
from pathlib import Path

log = logging.getLogger(__name__)


class JsonStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()

    def read(self, default=None):
        with self._lock:
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                return default
            except (ValueError, OSError):
                log.warning("No se pudo leer %s", self.path, exc_info=True)
                return default

    def write(self, data):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix=self.path.name, suffix=".tmp", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(data, stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, self.path)
            finally:
                Path(name).unlink(missing_ok=True)

    def update(self, **changes):
        with self._lock:
            data = self.read({})
            if not isinstance(data, dict):
                data = {}
            data.update(changes)
            self.write(data)
            return data
