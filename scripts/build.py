"""Build the same tested app locally and in GitHub Actions."""
import argparse
from pathlib import Path
import subprocess
import sys
import shutil
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import APP_VERSION


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def archive_legacy_executables():
    """Keep obsolete generated binaries recoverable, away from the launch path."""
    root = ROOT.resolve()
    for filename in ("app.exe", "Youtify.exe"):
        source = root / "dist" / filename
        if not source.is_file():
            continue
        archive = root / "build" / "legacy-executables"
        target = archive / f"{source.stem}-{source.stat().st_mtime_ns}.exe"
        if not source.resolve().is_relative_to(root) or not target.resolve().is_relative_to(root):
            raise RuntimeError("Legacy binary is outside the project")
        archive.mkdir(parents=True, exist_ok=True)
        source.rename(target)
    (root / "dist" / "LEEME.txt").write_text(
        "Ejecuta Youtify\\Youtify.exe y conserva su carpeta completa.\n"
        "Para actualizar la aplicación instalada y sus accesos directos, usa installer\\Youtify-Setup.exe.\n"
        "Los ejecutables antiguos se conservaron en build\\legacy-executables.\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true", help="CI only: tests already ran")
    args = parser.parse_args()
    for filename in ["ffmpeg/ffmpeg.exe", "ffmpeg/ffprobe.exe", "runtime/node.exe"]:
        if not (ROOT / filename).is_file():
            parser.error("Missing components. Run python scripts/prepare_components.py first.")
    if not args.skip_tests:
        run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    (build / "version.iss").write_text(f'#define MyAppVersion "{APP_VERSION}"\n', encoding="utf-8")
    from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo,
        StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct)
    numbers = tuple(map(int, APP_VERSION.split("."))) + (0,)
    version = VSVersionInfo(ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, fileType=1), kids=[
        StringFileInfo([StringTable("040904b0", [StringStruct("ProductName", "Youtify"),
            StringStruct("FileDescription", "Youtify - Audio y video"), StringStruct("FileVersion", APP_VERSION),
            StringStruct("ProductVersion", APP_VERSION), StringStruct("OriginalFilename", "Youtify.exe")])]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])])])
    (build / "windows_version.txt").write_text(str(version), encoding="utf-8")
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "Youtify.spec")
    for folder in ("ffmpeg", "runtime"):
        shutil.copytree(ROOT / folder, ROOT / "dist" / "Youtify" / folder, dirs_exist_ok=True)
    import json
    (ROOT / "dist/Youtify/update-manifest.json").write_text(json.dumps({"schema": 1,
        "app": "Youtify", "version": APP_VERSION, "platform": "win-x64", "entrypoint": "Youtify.exe"}), encoding="utf-8")
    run(str(ROOT / "dist/Youtify/Youtify.exe"), "--self-check", str(build / "packaged-check.json"))
    check = json.loads((build / "packaged-check.json").read_text(encoding="utf-8"))
    if not all(check.get(key) for key in ["frozen", "ffmpeg", "ffprobe", "javascript", "ejs", "icon"]):
        raise RuntimeError(f"Packaged component check failed: {check}")
    archive_legacy_executables()
    print(f"Youtify {APP_VERSION} ready in dist/Youtify. Compile installer.iss with Inno Setup.")


if __name__ == "__main__":
    main()
