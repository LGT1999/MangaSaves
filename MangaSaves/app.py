"""Punto de entrada compatible con python MangaSaves/app.py y -m MangaSaves.app."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from MangaSaves.bootstrap import main


if __name__ == "__main__":
    raise SystemExit(main())
