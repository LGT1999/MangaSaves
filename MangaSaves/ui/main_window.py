"""Ventana principal: coordina componentes, estado de navegación y repositorio."""

from pathlib import Path
import sqlite3

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from MangaSaves.config import MINIMUM_WINDOW_SIZE, WINDOW_SIZE, WINDOW_TITLE
from MangaSaves.domain.models import ViewState
from MangaSaves.paths import resource_path
from MangaSaves.persistence.repository import ReadingRepository
from MangaSaves.ui.table_model import COLUMNS, ReadingTableModel
from MangaSaves.ui.themes import THEMES, apply_theme, saved_theme, user_settings
from MangaSaves.ui.widgets import (
    AddReadingForm, LibraryToolbar, PaginationBar, ReadingActions, ReadingTable, ThemeSelector,
)


class AppLectura(QMainWindow):
    def __init__(self, db_path: Path | str, settings: QSettings | None = None):
        super().__init__()
        self.settings = settings if settings is not None else user_settings()
        self.theme_key = saved_theme(self.settings)
        self.repository = ReadingRepository(db_path)
        self.state = ViewState()
        self.total_pages = 1
        try:
            self._configure_window()
            self.model = ReadingTableModel(self.repository, self)
            self.refresh_timer = QTimer(self)
            self.refresh_timer.setSingleShot(True)
            self._build_layout()
            self.table.set_theme(THEMES[self.theme_key])
            self._connect_signals()
            self.cargar_datos()
        except Exception:
            self.repository.close()
            raise
        if self.repository.backup_path:
            self.statusBar().showMessage("Copia de seguridad creada antes de actualizar la base.", 8000)

    def _configure_window(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*MINIMUM_WINDOW_SIZE)
        apply_theme(self, self.theme_key)
        icons = [resource_path("Img/mangasaves.ico"), resource_path("Img/mangasaves.png")]
        icon = next((path for path in icons if path.is_file()), None)
        if icon:
            self.setWindowIcon(QIcon(str(icon)))

    def _build_layout(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(22, 20, 22, 14)
        layout.setSpacing(14)
        title = QLabel("Tu biblioteca")
        title.setObjectName("title")
        heading = QHBoxLayout()
        heading.addWidget(title)
        heading.addStretch()
        self.theme_control = ThemeSelector(self.theme_key)
        heading.addWidget(self.theme_control)
        layout.addLayout(heading)
        subtitle = QLabel("Guarda tu progreso y retoma la próxima lectura.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        self.form = AddReadingForm()
        self.toolbar = LibraryToolbar()
        self.table = ReadingTable(self.model)
        self.empty_label = QLabel("No hay lecturas en esta vista.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pagination = PaginationBar()
        self.actions = ReadingActions()
        layout.addWidget(self.form)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.pagination)
        layout.addWidget(self.actions)
        db_label = QLabel(f"Base: {self.repository.path.name}")
        db_label.setToolTip(str(self.repository.path))
        self.statusBar().addPermanentWidget(db_label)

    def _connect_signals(self):
        self.theme_control.theme_changed.connect(self.cambiar_tema)
        self.refresh_timer.timeout.connect(self.cargar_datos)
        self.model.error.connect(self.mostrar_error)
        self.model.reading_changed.connect(self._reading_changed)
        self.form.submitted.connect(self.agregar_registro)
        self.toolbar.search_requested.connect(self.ejecutar_busqueda)
        self.toolbar.search_cleared.connect(self._search_cleared)
        self.toolbar.letter_changed.connect(self.seleccionar_letra)
        self.toolbar.view_requested.connect(self.alternar_modo_vista)
        self.table.horizontalHeader().sectionClicked.connect(self.procesar_orden_columna)
        self.table.clicked.connect(self._cell_clicked)
        self.table.selectionModel().selectionChanged.connect(self._selection_changed)
        self.pagination.previous_requested.connect(lambda: self.mostrar_pagina(self.state.page - 1))
        self.pagination.next_requested.connect(lambda: self.mostrar_pagina(self.state.page + 1))
        self.pagination.size_changed.connect(self._page_size_changed)
        self.actions.deletion_requested.connect(self.eliminar_registro)

    def cambiar_tema(self, key: str):
        if key not in THEMES or key == self.theme_key:
            return
        apply_theme(self, key)
        self.theme_key = key
        self.table.set_theme(THEMES[key])
        self.settings.setValue("appearance/theme", key)
        self.settings.sync()
        message = f"Tema {THEMES[key].name} aplicado."
        if self.settings.status() != QSettings.Status.NoError:
            message += " No se pudo guardar la preferencia para el próximo inicio."
        self.statusBar().showMessage(message, 4500)

    def mostrar_error(self, message: str):
        QMessageBox.warning(self, "No se pudo completar la operación", message)

    def selected_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        return self.model.rows[rows[0].row()].id if rows else None

    def cargar_datos(self):
        selected = self.selected_id()
        try:
            page = self.repository.load_page(self.state)
        except sqlite3.Error as exc:
            self.mostrar_error(str(exc))
            return
        self.state.page = page.page
        self.total_pages = page.pages
        self.model.replace_rows(page.rows)
        if selected is not None:
            for row, reading in enumerate(self.model.rows):
                if reading.id == selected:
                    self.table.selectRow(row)
                    break
        recent = self.state.mode == "ultimos" and not self.state.search
        self.toolbar.letter_selector.setVisible(self.state.mode == "todos" and not self.state.search)
        self.pagination.setVisible(not recent)
        self.pagination.page_label.setText(f"Página {page.page} de {page.pages}")
        self.pagination.previous_button.setEnabled(page.page > 1)
        self.pagination.next_button.setEnabled(page.page < page.pages)
        self.empty_label.setVisible(not page.rows)
        self.actions.result_label.setText(
            f"Últimas {len(page.rows)} lecturas modificadas" if recent
            else f"{page.total} lecturas · {len(page.rows)} en esta página"
        )
        column = COLUMNS.index("fecha") if recent else COLUMNS.index(self.state.sort_column)
        order = Qt.SortOrder.DescendingOrder if recent or self.state.descending else Qt.SortOrder.AscendingOrder
        self.table.horizontalHeader().setSortIndicator(column, order)
        self._selection_changed()

    def _reading_changed(self, reading_id: int, field: str):
        self.statusBar().showMessage("Progreso guardado.", 2500)
        sort_field = "estado" if field == "terminado" else field
        if (self.state.mode == "ultimos" or self.state.sort_column in (sort_field, "fecha")
                or (self.state.search and field == "pagina")):
            # Espera al cierre del editor antes de cambiar el orden de sus índices.
            self.refresh_timer.start(0)

    def _cell_clicked(self, index):
        if index.column() == 0:
            QApplication.clipboard().setText(self.model.rows[index.row()].nombre)
            self.statusBar().showMessage("Nombre completo copiado al portapapeles.", 2500)
        elif index.column() == 3:
            self.model.toggle_status(index)
        elif COLUMNS[index.column()] == "valoracion":
            self.table.edit(index)

    def _selection_changed(self, *args):
        self.actions.delete_button.setEnabled(self.selected_id() is not None)

    def ejecutar_busqueda(self):
        self.state.search = self.toolbar.search_input.text().strip()
        self.state.page = 1
        self.cargar_datos()

    def _search_cleared(self):
        if self.state.search:
            self.ejecutar_busqueda()

    def alternar_modo_vista(self):
        self.state.mode = "todos" if self.state.mode == "ultimos" else "ultimos"
        self.state.search = ""
        self.toolbar.search_input.clear()
        self.state.page = 1
        self.toolbar.view_button.setText("Ver últimos 5" if self.state.mode == "todos" else "Ver lista completa")
        self.cargar_datos()

    def seleccionar_letra(self, letter: str | None):
        self.state.letter = letter
        self.state.page = 1
        self.cargar_datos()

    def mostrar_pagina(self, page: int):
        self.state.page = max(1, min(page, self.total_pages))
        self.cargar_datos()

    def _page_size_changed(self, size: int):
        self.state.page_size = size
        self.state.page = 1
        self.cargar_datos()

    def procesar_orden_columna(self, column: int):
        if self.state.mode == "ultimos" and not self.state.search:
            self.statusBar().showMessage("Los últimos cinco se ordenan por fecha. Usa la lista completa para otro orden.", 4500)
            return
        key = COLUMNS[column]
        self.state.descending = not self.state.descending if self.state.sort_column == key else False
        self.state.sort_column = key
        self.state.page = 1
        self.cargar_datos()

    def agregar_registro(self):
        try:
            self.repository.add(*self.form.values())
        except (ValueError, sqlite3.Error) as exc:
            self.mostrar_error(str(exc))
            return
        self.form.clear()
        self.cargar_datos()
        self.form.name_input.setFocus()
        self.statusBar().showMessage("Lectura agregada.", 2500)

    def eliminar_registro(self):
        selected = self.selected_id()
        if selected is None:
            return
        answer = QMessageBox.question(
            self, "Eliminar lectura", "¿Eliminar la lectura seleccionada?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.repository.delete(selected)
        except sqlite3.Error as exc:
            self.mostrar_error(str(exc))
            return
        self.cargar_datos()
        self.statusBar().showMessage("Lectura eliminada.", 2500)

    def closeEvent(self, event):
        self.table.setFocus()
        self.refresh_timer.stop()
        self.repository.close()
        super().closeEvent(event)
