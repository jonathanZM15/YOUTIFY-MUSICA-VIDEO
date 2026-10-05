import re
from urllib.parse import urlparse
from config.settings import VALID_YOUTUBE_HOSTS

_TRAVERSAL_RE = re.compile(r"\.{2,}")


class SecurityValidator:
    """Validador estricto de seguridad para mitigar SSRF, inyecciones y accesos no autorizados."""

    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        """Verifica que la URL sea un recurso legítimo de YouTube y mitiga ataques SSRF/Phishing."""
        if not url or not isinstance(url, str):
            return False

        clean_url = url.strip()
        try:
            parsed = urlparse(clean_url)
            # Solo permitir protocolos cifrados y web seguros
            if parsed.scheme not in ("http", "https"):
                return False

            host = (parsed.hostname or "").lower()
            if not host:
                return False

            # Comprobar pertenencia estricta en dominios oficiales
            return host in VALID_YOUTUBE_HOSTS or host.endswith(".youtube.com")
        except Exception:
            return False

    @staticmethod
    def sanitize_title(title: str) -> str:
        """Sanitiza títulos para evitar vulnerabilidades de Path Traversal e inyección de rutas en Windows."""
        invalid_chars = '<>:"/\\|?*\x00'
        for char in invalid_chars:
            title = title.replace(char, "_")
        # Eliminar secuencias de escape de directorio '../' o '..'
        title = _TRAVERSAL_RE.sub("_", title)
        return title[:200].strip().strip("._")
