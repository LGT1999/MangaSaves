"""Verificación reproducible con copia de la base y capturas fuera de pantalla."""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import platform
from statistics import median
import sys
import tempfile
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import PySide6
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from MangaSaves.ui.main_window import AppLectura
from MangaSaves.persistence.repository import ReadingRepository
from MangaSaves.domain.models import ViewState


def measure(repository, state, repetitions=100):
    times = []
    for _ in range(repetitions):
        started = perf_counter()
        page = repository.load_page(state)
        times.append((perf_counter() - started) * 1000)
    return {"median_ms": round(median(times), 3), "rows_loaded": len(page.rows), "total": page.total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("verification"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.db.resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    application = QApplication([])
    application.setStyle("Fusion")
    # El plugin offscreen de Windows no descubre las fuentes del sistema.
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
    if font_path.is_file():
        QFontDatabase.addApplicationFont(str(font_path))
    report = {"python": platform.python_version(), "qt": PySide6.__version__, "render": "offscreen"}
    with tempfile.TemporaryDirectory() as temp:
        copied = Path(temp) / "copy.db"
        # No abre el repositorio de producción: SQLite solo lee la base original.
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            original_columns = [row[1] for row in original.execute("PRAGMA table_info(lecturas)")]
            fields = ", ".join('"' + name.replace('"', '""') + '"' for name in original_columns)
            before = original.execute(f"SELECT {fields} FROM lecturas ORDER BY id").fetchall()
            with closing(sqlite3.connect(copied)) as destination:
                original.backup(destination)
        settings = QSettings(str(Path(temp) / "settings.ini"), QSettings.Format.IniFormat)
        window = AppLectura(copied, settings)
        after = window.repository.conn.execute(f"SELECT {fields} FROM lecturas ORDER BY id").fetchall()
        assert before == [tuple(row) for row in after], "La inicialización modificó registros"
        report["existing_rows"] = len(before)
        report["existing_records_preserved"] = True
        report["rating_column_available"] = "valoracion" in {
            row["name"] for row in window.repository.conn.execute("PRAGMA table_info(lecturas)")
        }
        report["existing_recent"] = measure(window.repository, ViewState())
        report["existing_all"] = measure(window.repository, ViewState(mode="todos"))
        window.show()
        application.processEvents()
        for size, filename in (((1150, 720), "app-wide.png"), ((850, 530), "app-narrow.png")):
            window.resize(*size)
            application.processEvents()
            assert window.grab().save(str(args.output / filename))
        window.close()
        application.processEvents()

        repository = ReadingRepository(Path(temp) / "synthetic.db")
        try:
            with repository.conn:
                repository.conn.executemany(
                    "INSERT INTO lecturas(nombre,capitulo,pagina,terminado,fecha_mod) VALUES(?,?,?,?,?)",
                    ((f"Lectura de prueba {i:05}", str(i % 150), "MH", "No", "02/10/2026 02:33:00")
                     for i in range(10000)),
                )
            report["synthetic_rows"] = 10000
            report["synthetic_recent"] = measure(repository, ViewState())
            report["synthetic_all"] = measure(repository, ViewState(mode="todos"))
            report["synthetic_search"] = measure(repository, ViewState(search="MH"))
        finally:
            repository.close()
    report["original_file_unchanged"] = digest == hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["original_file_unchanged"], "Se modificó el archivo original"
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
