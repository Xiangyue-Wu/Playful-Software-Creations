"""Build an allowlisted source archive; never include device or user data."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import hashlib
import sys

ROOT = Path(__file__).resolve().parent
DEST = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1
        else ROOT.parent / "RMPP-ScreenBridge-Source-20261113.zip")
FILES = (
    ".gitignore", "LICENSE", "README.md", "README.zh-CN.md",
    "THIRD_PARTY.md", "PUBLICATION_REVIEW.md", "requirements.txt",
    "setup.ps1", "启动安装器.cmd", "卸载RMPP-ScreenBridge.cmd", "make_source_zip.py", "docs/RECOVERY.md",
    "deploy/qmd-vnsee-layout/vnsee-asivery-clip-v7-landscape.qmd",
    "apps/VNSee-Launcher/portable_manager.py",
    "apps/VNSee-Launcher/portable_gui.py",
    "apps/VNSee-Launcher/uninstaller_gui.py",
    "apps/VNSee-Launcher/test_proxy.py",
    "apps/VNSee-Launcher/test_portable_manager.py",
)

with ZipFile(DEST, "w", ZIP_DEFLATED) as archive:
    for name in FILES:
        path = ROOT / name
        if not path.is_file():
            raise RuntimeError(f"Source file missing: {name}")
        archive.write(path, name)
with ZipFile(DEST) as archive:
    if archive.testzip() is not None or set(archive.namelist()) != set(FILES):
        raise RuntimeError("Archive verification failed")
print(f"{DEST} | {DEST.stat().st_size} bytes | SHA256 {hashlib.sha256(DEST.read_bytes()).hexdigest()}")
