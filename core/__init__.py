"""Public exports are lazy so the single-instance guard can run before yt-dlp."""
from importlib import import_module

__all__ = ["SecurityValidator", "FFmpegManager", "DownloadEngine"]
_MODULES = {"SecurityValidator": "validator", "FFmpegManager": "ffmpeg_manager", "DownloadEngine": "downloader"}


def __getattr__(name):
    if name not in _MODULES:
        raise AttributeError(name)
    value = getattr(import_module(f".{_MODULES[name]}", __name__), name)
    globals()[name] = value
    return value
