"""Use installed challenge scripts and a local runtime, without downloading code at startup."""
import shutil
from config.settings import BASE_DIR


def javascript_options() -> dict:
    for name in ("node", "deno", "quickjs"):
        bundled = BASE_DIR / "runtime" / f"{name}.exe"
        path = str(bundled) if bundled.is_file() else shutil.which(name)
        if path:
            return {"js_runtimes": {name: {"path": path}}}
    return {"js_runtimes": {}}
