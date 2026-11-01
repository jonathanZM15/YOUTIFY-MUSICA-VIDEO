# Bundled components

Youtify application sources are MIT licensed (see LICENSE). Third-party components
keep their respective licenses, independently of the application license.

* FFmpeg / FFprobe: BtbN Windows GPL v3 build, dated 2026-10-28, FFmpeg commit
  28fda48e0b. License: ffmpeg/LICENSE.txt. Source and build configuration:
  https://github.com/FFmpeg/FFmpeg/tree/28fda48e0b and
  https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-10-28-19-47.
  These are separate executables invoked by the application.
* Node.js 24.5.0: Node.js and included component licenses are in runtime/LICENSE.
  Source: https://github.com/nodejs/node/tree/v24.5.0.
* yt-dlp: https://github.com/yt-dlp/yt-dlp (Unlicense).
* yt-dlp-ejs: https://github.com/yt-dlp/ejs (Unlicense).
* CustomTkinter: https://github.com/TomSchimansky/CustomTkinter. License metadata
  from the bundled distribution is included in _internal.
* Pillow: https://python-pillow.github.io (HPND).
* Mutagen: https://mutagen.readthedocs.io (GPL v2 or later).
* psutil: https://github.com/giampaolo/psutil (BSD 3 clause).

Python package license metadata is retained in the packaged application.
Pinned download URLs and SHA-256 values are in scripts/prepare_components.py
and config/settings.py. No JavaScript is downloaded at application startup.
