"""Ubicaciones de datos y recursos para c?digo fuente y ejecutables."""

from pathlib import Path
import sys

from MangaSaves.config import DB_NAME


def application_directory() -> Path:
    """Carpeta persistente de la app; nunca la carpeta temporal del empaquetador."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_path(relative: str) -> Path:
    """Recursos dentro del paquete, incluidos por PyInstaller bajo MangaSaves."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "MangaSaves" / relative
    return Path(__file__).resolve().parent / relative


def resolve_database_path(app_dir: Path, cwd: Path, explicit: str | None = None) -> Path:
    """Evita crear una base vacía cuando ya existe una en la ubicación anterior."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    candidates = [app_dir / DB_NAME, cwd / DB_NAME, app_dir / "dist" / DB_NAME,
                  app_dir.parent / DB_NAME]
    existing = list(dict.fromkeys(p.resolve() for p in candidates if p.is_file()))
    if len(existing) > 1:
        paths = "\n".join(str(p) for p in existing)
        raise ValueError(
            f"Hay varias bases de lecturas:\n{paths}\n\n"
            "Indica cuál usar con --db RUTA."
        )
    return existing[0] if existing else (app_dir / DB_NAME).resolve()
