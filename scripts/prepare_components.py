"""Fetch pinned, SHA-256 verified components for the Windows installer."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import FFMPEG_OFFICIAL_URL, FFMPEG_EXPECTED_SHA256

NODE_URL = "https://nodejs.org/dist/v24.5.0/node-v24.5.0-win-x64.zip"
NODE_SHA256 = "c6a5714108caa81bc71e3859c18f449a8f456e275946c0d429e2d7120b03d20e"


def fetch(url, expected, destination):
    if destination.exists():
        with destination.open("rb") as existing:
            if hashlib.file_digest(existing, "sha256").hexdigest() == expected:
                return
    temporary = destination.with_suffix(".download")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Youtify-Build/1.2"})
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as stream:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                stream.write(chunk)
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise RuntimeError(f"SHA-256 mismatch: {url}")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def extract(archive, target, filenames):
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp, zipfile.ZipFile(archive) as zf:
        staged = {}
        for filename in filenames:
            member = next((m for m in zf.infolist() if Path(m.filename).name == filename and not m.is_dir()), None)
            if not member:
                raise RuntimeError(f"Missing {filename} in {archive.name}")
            path = Path(tmp) / filename
            with zf.open(member) as source, path.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            staged[filename] = path
        for filename, path in staged.items():
            shutil.copy2(path, target / filename)


def main():
    cache = ROOT / "build" / "components"
    cache.mkdir(parents=True, exist_ok=True)
    ffmpeg_zip, node_zip = cache / "ffmpeg.zip", cache / "node.zip"
    print("Verifying pinned FFmpeg package...", flush=True)
    fetch(FFMPEG_OFFICIAL_URL, FFMPEG_EXPECTED_SHA256, ffmpeg_zip)
    extract(ffmpeg_zip, ROOT / "ffmpeg", ["ffmpeg.exe", "ffprobe.exe", "LICENSE.txt"])
    print("Verifying pinned Node.js package...", flush=True)
    fetch(NODE_URL, NODE_SHA256, node_zip)
    extract(node_zip, ROOT / "runtime", ["node.exe", "LICENSE"])
    manifest = {"ffmpeg": {"url": FFMPEG_OFFICIAL_URL, "sha256": FFMPEG_EXPECTED_SHA256},
                "node": {"url": NODE_URL, "sha256": NODE_SHA256}}
    (cache / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Components ready.")


if __name__ == "__main__":
    main()
