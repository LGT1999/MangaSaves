from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest

from MangaSaves.persistence.queries import DATE_SQL, LEGACY_FIELDS
from MangaSaves.persistence.repository import ReadingRepository
from MangaSaves.domain.models import RATING_OPTIONS, ViewState
from MangaSaves.paths import resolve_database_path


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "progreso_lectura.db"
        self.repo = ReadingRepository(self.path)

    def tearDown(self):
        self.repo.close()
        self.temp.cleanup()

    def test_validation_and_unchanged_edit_do_not_write(self):
        reading = self.repo.add("  Un título  ", "2.3", "mh")
        self.assertEqual((reading.nombre, reading.pagina), ("Un título", "MH"))
        before = self.repo.conn.total_changes
        same, changed = self.repo.update(reading.id, "capitulo", "2.3")
        self.assertFalse(changed)
        self.assertEqual(same.fecha_mod, reading.fecha_mod)
        self.assertEqual(self.repo.conn.total_changes, before)
        for value in ("-1", "", "2..3", "dos", "2,3"):
            with self.assertRaises(ValueError):
                self.repo.update(reading.id, "capitulo", value)
        with self.assertRaises(ValueError):
            self.repo.update(reading.id, "pagina", "  ")
        self.assertEqual(self.repo.get(reading.id), reading)

    def test_numeric_sort_applies_before_pagination(self):
        for chapter in ("10", "2.3", "2", "0.5", "42"):
            self.repo.add(f"Lectura {chapter}", chapter, "MH")
        state = ViewState(mode="todos", sort_column="capitulo", page_size=2)
        first = self.repo.load_page(state)
        self.assertEqual([r.capitulo for r in first.rows], ["0.5", "2"])
        self.assertEqual((first.total, first.pages), (5, 3))
        state.page = 2
        self.assertEqual([r.capitulo for r in self.repo.load_page(state).rows], ["2.3", "10"])
        state.page, state.descending = 1, True
        self.assertEqual([r.capitulo for r in self.repo.load_page(state).rows], ["42", "10"])

    def test_recent_dates_are_chronological_and_indexed(self):
        dates = ("31/12/2025 20:00", "01/01/2026 00:00", "02/10/2026 02:33",
                 "01/10/2026 06:50", None, "2026-10-03 12:00:00")
        for number, date in enumerate(dates):
            reading = self.repo.add(str(number), "0", "MH")
            self.repo.conn.execute("UPDATE lecturas SET fecha_mod=? WHERE id=?", (date, reading.id))
        self.repo.conn.commit()
        self.assertEqual([r.nombre for r in self.repo.load_page(ViewState()).rows], ["5", "2", "3", "1", "0"])
        plan = self.repo.conn.execute(
            f"EXPLAIN QUERY PLAN SELECT id FROM lecturas ORDER BY {DATE_SQL} DESC, id DESC LIMIT 5"
        ).fetchall()
        self.assertTrue(any("idx_lecturas_fecha_v2" in row[3] for row in plan))

    def test_search_is_paginated_literal_and_independent_of_letter(self):
        for i in range(31):
            self.repo.add(f"Lectura {i:02}", "1", "MH")
        special = self.repo.add("100%_\\ especial", "1", "SCAN")
        state = ViewState(search="MH", letter="Z", page_size=10)
        result = self.repo.load_page(state)
        self.assertEqual((result.total, len(result.rows), result.pages), (31, 10, 4))
        state.search = "%_\\"
        self.assertEqual([r.id for r in self.repo.load_page(state).rows], [special.id])
        state.search = "' OR 1=1 --"
        self.assertEqual(self.repo.load_page(state).total, 0)

    def test_delete_last_page_clamps_to_valid_page(self):
        records = [self.repo.add(f"A {i:02}", "1", "MH") for i in range(11)]
        state = ViewState(mode="todos", letter="A", page=2, page_size=10)
        self.assertEqual(len(self.repo.load_page(state).rows), 1)
        self.repo.delete(records[-1].id)
        result = self.repo.load_page(state)
        self.assertEqual((result.page, result.pages, len(result.rows)), (1, 1, 10))

    def test_legacy_status_and_letter_filters(self):
        reading = self.repo.add("Alpha", "1", "MH")
        self.repo.add("beta", "2", "MH")
        other = self.repo.add("3 mundos", "3", "MH")
        self.repo.conn.execute("UPDATE lecturas SET terminado='✅ Terminado' WHERE id=?", (reading.id,))
        self.repo.conn.commit()
        self.assertTrue(self.repo.get(reading.id).completed)
        self.assertEqual(self.repo.load_page(ViewState(mode="todos", letter="B")).total, 1)
        self.assertEqual([r.id for r in self.repo.load_page(ViewState(mode="todos", letter="#")).rows], [other.id])

    def test_legacy_database_is_backed_up_once_without_changing_records(self):
        self.repo.close()
        legacy = Path(self.temp.name) / "legacy.db"
        with closing(sqlite3.connect(legacy)) as conn:
            conn.execute("CREATE TABLE lecturas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, "
                         "capitulo TEXT NOT NULL, pagina TEXT NOT NULL, terminado TEXT DEFAULT 'No', fecha_mod TEXT)")
            conn.execute("INSERT INTO lecturas VALUES (7, 'Mi lectura', '2.3', 'mh', 'Sí', '23/07/2026 08:13')")
            conn.commit()
        self.repo = ReadingRepository(legacy)
        backup = self.repo.backup_path
        self.assertTrue(backup.is_file())
        with closing(sqlite3.connect(backup)) as conn:
            self.assertEqual(conn.execute("SELECT * FROM lecturas").fetchall(),
                             [tuple(self.repo.conn.execute(f"SELECT {LEGACY_FIELDS} FROM lecturas").fetchone())])
        self.assertEqual(self.repo.get(7).pagina, "mh")
        self.assertEqual(self.repo.get(7).valoracion, "")
        self.repo.close()
        self.repo = ReadingRepository(legacy)
        self.assertIsNone(self.repo.backup_path)

    def test_default_path_finds_dist_and_refuses_ambiguous_databases(self):
        app_dir = Path(self.temp.name) / "nested" / "app"
        cwd = Path(self.temp.name) / "cwd"
        (app_dir / "dist").mkdir(parents=True)
        cwd.mkdir()
        db = app_dir / "dist" / "progreso_lectura.db"
        db.touch()
        self.assertEqual(resolve_database_path(app_dir, cwd), db.resolve())
        duplicate = cwd / "progreso_lectura.db"
        duplicate.touch()
        with self.assertRaises(ValueError):
            resolve_database_path(app_dir, cwd)
        self.assertEqual(resolve_database_path(app_dir, cwd, str(duplicate)), duplicate.resolve())

    def test_ratings_save_validate_and_sort_by_quality_before_pagination(self):
        ungraded = self.repo.add("Sin nota", "1", "MH")
        for rating in reversed(RATING_OPTIONS):
            self.repo.add(rating, "1", "MH", rating)
        state = ViewState(mode="todos", sort_column="valoracion", page_size=100)
        self.assertEqual([r.valoracion for r in self.repo.load_page(state).rows], ["", *RATING_OPTIONS])
        state.descending, state.page_size = True, 2
        self.assertEqual([r.valoracion for r in self.repo.load_page(state).rows], ["GOAT", "Increíble"])
        updated, changed = self.repo.update(ungraded.id, "valoracion", "Muy bueno")
        self.assertTrue(changed)
        self.assertEqual(updated.valoracion, "Muy bueno")
        before = self.repo.conn.total_changes
        self.assertFalse(self.repo.update(ungraded.id, "valoracion", "Muy bueno")[1])
        self.assertEqual(self.repo.conn.total_changes, before)
        with self.assertRaises(ValueError):
            self.repo.update(ungraded.id, "valoracion", "Excelente")
        with self.assertRaises(ValueError):
            self.repo.add("Nota inválida", "1", "MH", "Otro")
        with self.assertRaises(sqlite3.IntegrityError):
            with self.repo.conn:
                self.repo.conn.execute("UPDATE lecturas SET valoracion='Otro' WHERE id=?", (ungraded.id,))
        self.assertEqual(self.repo.update(ungraded.id, "valoracion", "")[0].valoracion, "")
        self.repo.close()
        self.repo = ReadingRepository(self.path)
        self.assertEqual(self.repo.get(ungraded.id).valoracion, "")
        self.assertEqual(self.repo.load_page(state).rows[0].valoracion, "GOAT")

    def test_qt_database_with_existing_indices_is_backed_up_before_rating_migration(self):
        self.repo.close()
        legacy = Path(self.temp.name) / "qt-before-rating.db"
        # Simula la versión Qt anterior, cuyo índice de fecha ya estaba creado.
        with closing(sqlite3.connect(legacy)) as conn:
            conn.execute("CREATE TABLE lecturas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, "
                         "capitulo TEXT NOT NULL, pagina TEXT NOT NULL, terminado TEXT DEFAULT 'No', fecha_mod TEXT)")
            conn.execute("INSERT INTO lecturas VALUES (9, 'Conservar', '42', 'MH', 'Sí', '02/10/2026 02:33')")
            conn.execute(f"CREATE INDEX idx_lecturas_fecha_v2 ON lecturas({DATE_SQL} DESC, id DESC)")
            conn.commit()
        self.repo = ReadingRepository(legacy)
        backup = self.repo.backup_path
        self.assertTrue(backup.is_file())
        self.assertEqual(self.repo.get(9).valoracion, "")
        self.assertEqual(tuple(self.repo.conn.execute(f"SELECT {LEGACY_FIELDS} FROM lecturas").fetchone()),
                         (9, "Conservar", "42", "MH", "Sí", "02/10/2026 02:33"))
        with closing(sqlite3.connect(backup)) as conn:
            self.assertNotIn("valoracion", [row[1] for row in conn.execute("PRAGMA table_info(lecturas)")])
        self.repo.close()
        self.repo = ReadingRepository(legacy)
        self.assertIsNone(self.repo.backup_path)


if __name__ == "__main__":
    unittest.main()
