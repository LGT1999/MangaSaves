"""Modelo Qt: datos y editores temporales, sin widgets permanentes por celda."""

import sqlite3

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor, QFont

from MangaSaves.domain.models import Reading
from MangaSaves.persistence.repository import ReadingRepository
from MangaSaves.ui.themes import DEFAULT_THEME, THEMES


COLUMNS = ("nombre", "capitulo", "pagina", "estado", "valoracion", "fecha")
HEADERS = ("Nombre", "Capítulo", "Página / Plataforma", "Estado de lectura", "Valoración", "Última modificación")


class ReadingTableModel(QAbstractTableModel):
    error = Signal(str)
    reading_changed = Signal(int, str)

    def __init__(self, repository: ReadingRepository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.rows: list[Reading] = []
        self.theme = THEMES[DEFAULT_THEME]

    def set_theme(self, theme):
        self.theme = theme
        if self.rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.rows) - 1, len(COLUMNS) - 1),
                                  [Qt.ItemDataRole.ForegroundRole])

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.TextAlignmentRole and orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return HEADERS[section] if 0 <= section < len(HEADERS) else None
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.rows):
            return None
        reading = self.rows[index.row()]
        column = COLUMNS[index.column()]
        if role == Qt.ItemDataRole.EditRole and column == "valoracion":
            return reading.valoracion
        values = (reading.nombre, reading.capitulo, reading.pagina.upper(),
                  "Terminado" if reading.completed else "Leyendo", reading.valoracion or "Sin valorar",
                  reading.fecha_mod or "Sin datos")
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, Qt.ItemDataRole.ToolTipRole):
            if role == Qt.ItemDataRole.ToolTipRole and index.column() == 3:
                return "Haz clic para cambiar entre Leyendo y Terminado."
            if role == Qt.ItemDataRole.ToolTipRole and column == "valoracion":
                return "Haz clic para elegir una valoración."
            return values[index.column()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column in ("capitulo", "estado", "valoracion", "fecha"):
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        if role == Qt.ItemDataRole.ForegroundRole:
            color = "muted" if reading.completed or column == "fecha" else "text"
            return QColor(self.theme.colors[color])
        if role == Qt.ItemDataRole.FontRole and reading.completed and index.column() == 0:
            font = QFont()
            font.setItalic(True)
            return font
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if COLUMNS[index.column()] in ("capitulo", "pagina", "valoracion"):
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if (role != Qt.ItemDataRole.EditRole or not index.isValid()
                or COLUMNS[index.column()] not in ("capitulo", "pagina", "valoracion")):
            return False
        field = COLUMNS[index.column()]
        return self._update(index.row(), field, str(value))

    def _update(self, row: int, field: str, value: str) -> bool:
        try:
            reading, changed = self.repository.update(self.rows[row].id, field, value)
        except (ValueError, sqlite3.Error) as exc:
            self.error.emit(str(exc))
            return False
        if changed:
            self.rows[row] = reading
            self.dataChanged.emit(self.index(row, 0), self.index(row, len(COLUMNS) - 1))
            self.reading_changed.emit(reading.id, field)
        return True

    def toggle_status(self, index):
        if index.isValid():
            reading = self.rows[index.row()]
            self._update(index.row(), "terminado", "No" if reading.completed else "Sí")

    def replace_rows(self, rows: list[Reading]):
        # Si la consulta conserva las mismas filas y orden, actualiza solo las diferencias.
        if [r.id for r in rows] == [r.id for r in self.rows]:
            for row, reading in enumerate(rows):
                if reading != self.rows[row]:
                    self.rows[row] = reading
                    self.dataChanged.emit(self.index(row, 0), self.index(row, len(COLUMNS) - 1))
            return
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()
