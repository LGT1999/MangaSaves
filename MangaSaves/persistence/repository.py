"""Persistencia SQLite compatible con las bases de la versión Tkinter."""

from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3

from MangaSaves.domain.models import Reading, ReadingPage, ViewState
from MangaSaves.domain.validation import validate_chapter, validate_rating
from MangaSaves.persistence.queries import DATE_SQL, FIELDS, RATING_VALUES_SQL, SORT_SQL, filter_clause


class ReadingRepository:
    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()
        self.backup_path: Path | None = None
        self.conn = sqlite3.connect(self.path, timeout=2)
        self.conn.row_factory = sqlite3.Row
        try:
            self._initialize()
        except Exception:
            self.conn.close()
            raise

    def _initialize(self):
        table_exists = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lecturas'"
        ).fetchone()
        index_exists = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_lecturas_fecha_v2'"
        ).fetchone()
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(lecturas)")}
        needs_rating = table_exists and "valoracion" not in columns
        if table_exists and (not index_exists or needs_rating):
            # Respalda también bases Qt que ya tienen índices pero aún no valoración.
            backup_dir = self.path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            self.backup_path = backup_dir / f"{self.path.stem}-antes-actualizar-{stamp}.db"
            with closing(sqlite3.connect(self.backup_path)) as destination:
                self.conn.backup(destination)
        with self.conn:
            # La migración y los índices se confirman juntos o se revierten juntos.
            self.conn.execute("BEGIN")
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS lecturas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    capitulo TEXT NOT NULL,
                    pagina TEXT NOT NULL,
                    terminado TEXT DEFAULT 'No',
                    fecha_mod TEXT,
                    valoracion TEXT NOT NULL DEFAULT '' CHECK (valoracion IN ({RATING_VALUES_SQL}))
                )
            """)
            if needs_rating:
                self.conn.execute(
                    "ALTER TABLE lecturas ADD COLUMN valoracion TEXT NOT NULL DEFAULT '' "
                    f"CHECK (valoracion IN ({RATING_VALUES_SQL}))"
                )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lecturas_nombre_v2 "
                "ON lecturas(nombre COLLATE NOCASE, id)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lecturas_capitulo_v2 "
                "ON lecturas(CAST(capitulo AS REAL), id)"
            )
            self.conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_lecturas_fecha_v2 "
                f"ON lecturas({DATE_SQL} DESC, id DESC)"
            )

    def load_page(self, state: ViewState) -> ReadingPage:
        if state.mode == "ultimos" and not state.search:
            rows = self.conn.execute(
                f"SELECT {FIELDS} FROM lecturas ORDER BY {DATE_SQL} DESC, id DESC LIMIT 5"
            ).fetchall()
            return ReadingPage([Reading(**dict(r)) for r in rows], len(rows), 1, 1)
        where, params = filter_clause(state)
        total = self.conn.execute(f"SELECT COUNT(*) FROM lecturas {where}", params).fetchone()[0]
        size = max(1, min(state.page_size, 100))
        pages = max(1, (total + size - 1) // size)
        page = max(1, min(state.page, pages))
        order = SORT_SQL.get(state.sort_column, SORT_SQL["nombre"])
        direction = "DESC" if state.descending else "ASC"
        rows = self.conn.execute(
            f"SELECT {FIELDS} FROM lecturas {where} "
            f"ORDER BY {order} {direction}, id {direction} LIMIT ? OFFSET ?",
            (*params, size, (page - 1) * size),
        ).fetchall()
        return ReadingPage([Reading(**dict(r)) for r in rows], total, page, pages)

    def get(self, reading_id: int) -> Reading:
        row = self.conn.execute(
            f"SELECT {FIELDS} FROM lecturas WHERE id = ?", (reading_id,)
        ).fetchone()
        if row is None:
            raise ValueError("La lectura ya no existe. Actualiza la lista.")
        return Reading(**dict(row))

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def add(self, name: str, chapter: str, platform: str, rating: str = "") -> Reading:
        name, platform = name.strip(), platform.strip().upper()
        if not name or not platform:
            raise ValueError("Completa el nombre, el capítulo y la plataforma.")
        chapter = validate_chapter(chapter)
        rating = validate_rating(rating)
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO lecturas (nombre, capitulo, pagina, terminado, fecha_mod, valoracion) "
                "VALUES (?, ?, ?, 'No', ?, ?)", (name, chapter, platform, self._now(), rating),
            )
        return self.get(cursor.lastrowid)

    def update(self, reading_id: int, field: str, value: str) -> tuple[Reading, bool]:
        if field not in ("capitulo", "pagina", "terminado", "valoracion"):
            raise ValueError("Campo no editable.")
        if field == "capitulo":
            value = validate_chapter(value)
        elif field == "pagina":
            value = value.strip().upper()
            if not value:
                raise ValueError("La plataforma no puede quedar vacía.")
        elif field == "valoracion":
            value = validate_rating(value)
        elif value not in ("Sí", "No"):
            raise ValueError("Estado de lectura no válido.")
        old = self.get(reading_id)
        previous = getattr(old, field)
        if field == "pagina":
            previous = previous.upper()
        if previous == value:
            return old, False
        with self.conn:
            self.conn.execute(
                f"UPDATE lecturas SET {field} = ?, fecha_mod = ? WHERE id = ?",
                (value, self._now(), reading_id),
            )
        return self.get(reading_id), True

    def delete(self, reading_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM lecturas WHERE id = ?", (reading_id,))

    def close(self):
        self.conn.close()
