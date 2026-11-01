"""yt-dlp thumbnail support, imported only when a download needs it."""
from pathlib import Path
from yt_dlp.postprocessor import PostProcessor
from config.settings import THUMBNAIL_MAX_DIMENSION, THUMBNAIL_JPEG_QUALITY
from core.downloader import optimize_thumbnail


class ThumbnailOptimizerPP(PostProcessor):
    def __init__(self, downloader=None, max_dimension=THUMBNAIL_MAX_DIMENSION,
                 quality=THUMBNAIL_JPEG_QUALITY):
        super().__init__(downloader)
        self.max_dimension, self.quality = max_dimension, quality
        self.created_thumbnails: set[Path] = set()

    def run(self, info):
        for thumb in info.get("thumbnails") or []:
            filepath = thumb.get("filepath")
            if filepath and Path(filepath).exists():
                self.created_thumbnails.add(Path(filepath))
                optimized = optimize_thumbnail(Path(filepath), self.max_dimension, self.quality)
                self.created_thumbnails.add(optimized)
                thumb["filepath"] = str(optimized)
                if "__files_to_move" in info and filepath in info["__files_to_move"]:
                    info["__files_to_move"][str(optimized)] = info["__files_to_move"].pop(filepath)
        return [], info
