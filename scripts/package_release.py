"""Generate the installer/update release assets from the tested onedir build."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import APP_VERSION, UPDATE_ASSET_NAME


def main():
    package = ROOT / "dist/Youtify"
    manifest = json.loads((package / "update-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("version") != APP_VERSION:
        raise RuntimeError("Build/version mismatch")
    installer = ROOT / "installer/Youtify-Setup.exe"
    if not installer.is_file():
        raise RuntimeError("Compile installer.iss first")
    archive = installer.parent / UPDATE_ASSET_NAME
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                zipped.write(path, path.relative_to(package.parent).as_posix())
    lines = []
    for path in (installer, archive):
        with path.open("rb") as stream:
            lines.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {path.name}")
    (installer.parent / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"Release {APP_VERSION}: installer, verified update ZIP and SHA256SUMS.txt ready")


if __name__ == "__main__":
    main()
