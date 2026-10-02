"""Genera el ejecutable de Windows sin depender de la política de PowerShell."""

import argparse
from pathlib import Path
import sys

import PyInstaller.__main__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--onefile", action="store_true",
        help="Genera un único .exe portátil; extrae sus dependencias al arrancar.",
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Genera el ejecutable de Windows desde Windows.")
    root = Path(__file__).resolve().parent.parent
    app_dir = root / "MangaSaves"
    icon = app_dir / "Img" / "mangasaves.ico"
    resources = [app_dir / "Img", app_dir / "ui" / "styles.qss"]
    for path in [icon, *resources]:
        if not path.exists():
            raise SystemExit(f"No se encontró el recurso: {path}")
    mode = "onefile" if args.onefile else "onedir"
    build_dir = app_dir / "build" / mode
    executable = app_dir / "dist" / "MangaSaves.exe"
    if not args.onefile:
        executable = app_dir / "dist" / "MangaSaves" / "MangaSaves.exe"
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--windowed", f"--{mode}", "--name", "MangaSaves",
        "--paths", str(root),
        "--distpath", str(app_dir / "dist"),
        "--workpath", str(build_dir),
        "--specpath", str(build_dir),
        "--icon", str(icon),
        "--add-data", f"{app_dir / 'Img'};MangaSaves/Img",
        "--add-data", f"{app_dir / 'ui' / 'styles.qss'};MangaSaves/ui",
        str(app_dir / "app.py"),
    ])
    print(f"Ejecutable: {executable}")


if __name__ == "__main__":
    main()
