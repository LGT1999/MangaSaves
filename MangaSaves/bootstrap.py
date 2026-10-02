"""Argumentos de inicio, preparaci?n de Qt y apertura de la ventana."""

import argparse
import ctypes
from pathlib import Path
import sqlite3
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from MangaSaves.config import APP_NAME, WINDOWS_APP_ID
from MangaSaves.paths import application_directory, resolve_database_path
from MangaSaves.ui.main_window import AppLectura


def main() -> int:
    parser = argparse.ArgumentParser(description="Control de progreso de lectura MangaSaves")
    parser.add_argument("--db", help="Ruta de la base SQLite que quieres usar")
    args = parser.parse_args()
    if sys.platform.startswith("win"):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    application = QApplication(sys.argv[:1])
    application.setApplicationName(APP_NAME)
    application.setStyle("Fusion")
    app_dir = application_directory()
    try:
        db_path = resolve_database_path(app_dir, Path.cwd(), args.db)
        window = AppLectura(db_path)
    except (OSError, ValueError, sqlite3.Error) as exc:
        QMessageBox.critical(None, "No se pudo abrir MangaSaves", str(exc))
        return 1
    window.show()
    return application.exec()
