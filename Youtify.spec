# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH)
datas = [(str(root / 'icon.ico'), '.'), (str(root / 'THIRD_PARTY_NOTICES.md'), '.')]
datas += collect_data_files('customtkinter') + collect_data_files('yt_dlp_ejs')
for package in ['yt-dlp', 'yt-dlp-ejs', 'customtkinter', 'Pillow', 'mutagen', 'psutil',
                'packaging', 'darkdetect', 'requests', 'urllib3', 'idna', 'charset-normalizer',
                'certifi', 'brotli', 'pycryptodomex', 'websockets']:
    datas += copy_metadata(package)
hidden = collect_submodules('yt_dlp') + collect_submodules('yt_dlp_ejs')
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=[], datas=datas,
    hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
# A folder bundle starts without unpacking Python on every launch. The user receives one installer.
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Youtify', debug=False,
    strip=False, upx=False, console=False, icon=str(root / 'icon.ico'),
    version=str(root / 'build/windows_version.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Youtify')
