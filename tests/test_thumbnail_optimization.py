import unittest
from unittest.mock import MagicMock, patch
import tempfile
from pathlib import Path
from PIL import Image

from config.settings import (
    THUMBNAIL_MAX_DIMENSION,
    THUMBNAIL_JPEG_QUALITY,
    DEFAULT_EMBED_THUMBNAIL,
)
from core.downloader import (
    optimize_thumbnail,
    ThumbnailOptimizerPP,
    DownloadEngine,
)


class TestThumbnailOptimization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_oversized_image_is_resized_and_compressed_to_jpeg(self):
        """Una imagen de alta resolución (ej. 1920x1080) se redimensiona a <= 600px y se convierte a JPEG."""
        src_path = self.temp_path / "highres_thumb.webp"
        img = Image.new("RGB", (1920, 1080), color=(120, 50, 200))
        img.save(src_path, format="WEBP")
        original_size = src_path.stat().st_size

        optimized_path = optimize_thumbnail(
            src_path,
            max_dimension=THUMBNAIL_MAX_DIMENSION,
            quality=THUMBNAIL_JPEG_QUALITY,
        )

        self.assertEqual(optimized_path.suffix.lower(), ".jpg")
        self.assertTrue(optimized_path.exists())

        with Image.open(optimized_path) as opt_img:
            w, h = opt_img.size
            self.assertLessEqual(w, THUMBNAIL_MAX_DIMENSION)
            self.assertLessEqual(h, THUMBNAIL_MAX_DIMENSION)
            self.assertEqual(opt_img.format, "JPEG")

    def test_transparent_rgba_and_p_mode_converted_to_rgb(self):
        """Imágenes RGBA o en paleta P con transparencia se convierten a RGB sin errores."""
        rgba_path = self.temp_path / "alpha.png"
        img_rgba = Image.new("RGBA", (800, 800), color=(255, 0, 0, 128))
        img_rgba.save(rgba_path, format="PNG")

        opt_rgba = optimize_thumbnail(rgba_path, max_dimension=600, quality=85)
        with Image.open(opt_rgba) as opt_img:
            self.assertEqual(opt_img.mode, "RGB")
            self.assertEqual(opt_img.format, "JPEG")

        p_path = self.temp_path / "palette.png"
        img_p = Image.new("P", (700, 700))
        img_p.save(p_path, format="PNG")

        opt_p = optimize_thumbnail(p_path, max_dimension=600, quality=85)
        with Image.open(opt_p) as opt_img:
            self.assertEqual(opt_img.mode, "RGB")
            self.assertEqual(opt_img.format, "JPEG")

    def test_small_jpeg_is_not_reprocessed(self):
        """Un JPEG que ya cumple con <= 600x600 no se reprocesa innecesariamente."""
        small_path = self.temp_path / "already_small.jpg"
        img = Image.new("RGB", (400, 400), color=(50, 100, 150))
        img.save(small_path, format="JPEG", quality=85)
        mtime_before = small_path.stat().st_mtime_ns

        result_path = optimize_thumbnail(small_path, max_dimension=600, quality=85)
        self.assertEqual(result_path, small_path)
        self.assertEqual(result_path.stat().st_mtime_ns, mtime_before)

    def test_thumbnail_optimizer_postprocessor_updates_info_dict(self):
        """ThumbnailOptimizerPP actualiza el filepath en info['thumbnails'] a la versión .jpg optimizada."""
        src_path = self.temp_path / "video_thumb.webp"
        img = Image.new("RGB", (1280, 720), color=(30, 60, 90))
        img.save(src_path, format="WEBP")

        info = {
            "thumbnails": [
                {"filepath": str(src_path), "id": "0"}
            ]
        }

        pp = ThumbnailOptimizerPP(
            max_dimension=THUMBNAIL_MAX_DIMENSION,
            quality=THUMBNAIL_JPEG_QUALITY,
        )
        _, returned_info = pp.run(info)

        new_filepath = Path(returned_info["thumbnails"][0]["filepath"])
        self.assertEqual(new_filepath.suffix.lower(), ".jpg")
        self.assertTrue(new_filepath.exists())
        with Image.open(new_filepath) as opt_img:
            w, h = opt_img.size
            self.assertLessEqual(w, THUMBNAIL_MAX_DIMENSION)
            self.assertLessEqual(h, THUMBNAIL_MAX_DIMENSION)

    def test_build_yt_dlp_options_reflects_embed_thumbnail_flag(self):
        """_build_yt_dlp_options configura writethumbnail y postprocessors según embed_thumbnail."""
        engine = DownloadEngine()
        dest = Path("C:/Downloads")

        # Audio con carátula activada
        opts_audio_embed = engine._build_yt_dlp_options(
            is_audio=True,
            destination=dest,
            ffmpeg_dir=dest,
            embed_thumbnail=True,
        )
        self.assertTrue(opts_audio_embed["writethumbnail"])
        pps_audio_embed = [p.get("key") for p in opts_audio_embed["postprocessors"]]
        self.assertIn("EmbedThumbnail", pps_audio_embed)

        # Audio con carátula desactivada
        opts_audio_no_embed = engine._build_yt_dlp_options(
            is_audio=True,
            destination=dest,
            ffmpeg_dir=dest,
            embed_thumbnail=False,
        )
        self.assertFalse(opts_audio_no_embed["writethumbnail"])
        pps_audio_no_embed = [p.get("key") for p in opts_audio_no_embed["postprocessors"]]
        self.assertNotIn("EmbedThumbnail", pps_audio_no_embed)

        # Video con carátula desactivada
        opts_video_no_embed = engine._build_yt_dlp_options(
            is_audio=False,
            destination=dest,
            ffmpeg_dir=dest,
            embed_thumbnail=False,
        )
        self.assertFalse(opts_video_no_embed["writethumbnail"])
        pps_video_no_embed = [p.get("key") for p in opts_video_no_embed["postprocessors"]]
        self.assertNotIn("EmbedThumbnail", pps_video_no_embed)


if __name__ == "__main__":
    unittest.main()
