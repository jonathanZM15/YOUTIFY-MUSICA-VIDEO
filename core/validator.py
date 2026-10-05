from urllib.parse import urlparse
from config.settings import VALID_YOUTUBE_HOSTS


class SecurityValidator:
    """Validador estricto de seguridad para mitigar inyecciones y accesos a dominios no autorizados."""

    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        """Verifica que la URL sea un recurso válido y legítimo de YouTube."""
        if not url or not isinstance(url, str):
            return False

        clean_url = url.strip()
        try:
            parsed = urlparse(clean_url)
            if parsed.scheme not in ("http", "https"):
                return False

            host = (parsed.hostname or "").lower()
            if not host:
                return False

            return host in VALID_YOUTUBE_HOSTS or host.endswith(".youtube.com")
        except Exception:
            return False

    @staticmethod
    def sanitize_title(title: str) -> str:
        """Sanitiza títulos para evitar vulnerabilidades de path traversal en Windows."""
        invalid_chars = '<>:"/\\|?*\x00'
        for char in invalid_chars:
            title = title.replace(char, "_")
        return title[:200].strip()
