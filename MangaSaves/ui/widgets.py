"""Componentes de interfaz reutilizables; emiten eventos sin acceder a SQLite."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFrame, QHeaderView, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableView, QVBoxLayout, QWidget,
)

from MangaSaves.config import DEFAULT_PAGE_SIZE, PAGE_SIZES
from MangaSaves.ui.delegates import RatingDelegate, StatusDelegate, populate_ratings
from MangaSaves.ui.table_model import COLUMNS
from MangaSaves.ui.themes import THEMES


class ThemeSelector(QWidget):
    theme_changed = Signal(str)

    def __init__(self, current_theme: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Tema")
        self.selector = QComboBox()
        self.selector.setAccessibleName("Tema de la interfaz")
        self.selector.setToolTip("Cambia los colores y recuerda tu elección")
        for key, theme in THEMES.items():
            self.selector.addItem(theme.name, key)
        self.selector.setCurrentIndex(self.selector.findData(current_theme))
        label.setBuddy(self.selector)
        layout.addWidget(label)
        layout.addWidget(self.selector)
        self.selector.currentIndexChanged.connect(
            lambda: self.theme_changed.emit(self.selector.currentData())
        )


class AddReadingForm(QFrame):
    submitted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("addPanel")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre de lectura")
        self.name_input.setAccessibleName("Nombre de lectura")
        self.chapter_input = QLineEdit()
        self.chapter_input.setPlaceholderText("Capítulo")
        self.chapter_input.setAccessibleName("Capítulo")
        self.chapter_input.setToolTip("Ejemplos: 2, 2.3 o 0.5")
        self.chapter_input.setFixedWidth(100)
        self.platform_input = QLineEdit()
        self.platform_input.setPlaceholderText("Página / Plataforma")
        self.platform_input.setAccessibleName("Página o plataforma")
        self.platform_input.textEdited.connect(self._uppercase_platform)
        self.rating_selector = QComboBox()
        self.rating_selector.setAccessibleName("Valoración inicial de la lectura")
        self.rating_selector.setToolTip("Valoración opcional de la lectura")
        populate_ratings(self.rating_selector)
        self.add_button = QPushButton("+ Agregar")
        self.add_button.clicked.connect(self.submitted.emit)
        layout.addWidget(self.name_input, 3)
        layout.addWidget(self.chapter_input)
        layout.addWidget(self.platform_input, 2)
        layout.addWidget(self.rating_selector)
        layout.addWidget(self.add_button)
        for entry in (self.name_input, self.chapter_input, self.platform_input):
            entry.returnPressed.connect(self.submitted.emit)

    def values(self) -> tuple[str, str, str, str]:
        return (self.name_input.text(), self.chapter_input.text(), self.platform_input.text(),
                self.rating_selector.currentData())

    def clear(self):
        for entry in (self.name_input, self.chapter_input, self.platform_input):
            entry.clear()
        self.rating_selector.setCurrentIndex(self.rating_selector.findData(""))

    def _uppercase_platform(self, text: str):
        cursor = self.platform_input.cursorPosition()
        upper = text.upper()
        if upper != text:
            self.platform_input.setText(upper)
            self.platform_input.setCursorPosition(len(text[:cursor].upper()))


class LibraryToolbar(QWidget):
    search_requested = Signal()
    search_cleared = Signal()
    view_requested = Signal()
    letter_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre o plataforma…")
        self.search_input.setAccessibleName("Buscar lecturas")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.returnPressed.connect(self.search_requested.emit)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.search_requested.emit)
        self.letter_selector = QComboBox()
        self.letter_selector.setAccessibleName("Filtrar por letra inicial")
        self.letter_selector.addItem("Todas las letras", None)
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ#":
            self.letter_selector.addItem(letter, letter)
        self.letter_selector.currentIndexChanged.connect(self._on_letter_changed)
        self.view_button = QPushButton("Ver lista completa")
        self.view_button.setObjectName("secondary")
        self.view_button.clicked.connect(self.view_requested.emit)
        layout.addWidget(self.search_input, 1)
        layout.addWidget(self.search_button)
        layout.addWidget(self.letter_selector)
        layout.addWidget(self.view_button)

    def _on_search_text_changed(self, text: str):
        if not text:
            self.search_cleared.emit()

    def _on_letter_changed(self, index: int):
        self.letter_changed.emit(self.letter_selector.itemData(index))


class ReadingTable(QTableView):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setAccessibleName("Lecturas y progreso")
        self.setModel(model)
        self.setItemDelegateForColumn(COLUMNS.index("estado"), StatusDelegate(self))
        self.setItemDelegateForColumn(COLUMNS.index("valoracion"), RatingDelegate(self))
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(50)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header = self.horizontalHeader()
        header.setMinimumSectionSize(75)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for field, width in (("capitulo", 95), ("pagina", 170), ("estado", 140),
                             ("valoracion", 135), ("fecha", 195)):
            self.setColumnWidth(COLUMNS.index(field), width)
        header.setSortIndicatorShown(True)

    def set_theme(self, theme):
        self.model().set_theme(theme)
        self.itemDelegateForColumn(COLUMNS.index("estado")).theme = theme
        self.viewport().update()


class PaginationBar(QWidget):
    previous_requested = Signal()
    next_requested = Signal()
    size_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.page_label = QLabel()
        self.page_label.setObjectName("pageInfo")
        self.size_selector = QComboBox()
        self.size_selector.setAccessibleName("Lecturas por página")
        for size in PAGE_SIZES:
            self.size_selector.addItem(f"{size} por página", size)
        self.size_selector.setCurrentIndex(self.size_selector.findData(DEFAULT_PAGE_SIZE))
        self.size_selector.currentIndexChanged.connect(self._on_size_changed)
        self.previous_button = QPushButton("Anterior")
        self.next_button = QPushButton("Siguiente")
        self.previous_button.setObjectName("secondary")
        self.next_button.setObjectName("secondary")
        self.previous_button.clicked.connect(self.previous_requested.emit)
        self.next_button.clicked.connect(self.next_requested.emit)
        layout.addWidget(self.page_label)
        layout.addStretch()
        layout.addWidget(self.size_selector)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.next_button)

    def _on_size_changed(self, index: int):
        self.size_changed.emit(self.size_selector.itemData(index))


class ReadingActions(QWidget):
    deletion_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        actions = QHBoxLayout()
        self.delete_button = QPushButton("Eliminar seleccionado")
        self.delete_button.setObjectName("delete")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.deletion_requested.emit)
        self.result_label = QLabel()
        actions.addWidget(self.delete_button)
        actions.addStretch()
        actions.addWidget(self.result_label)
        layout.addLayout(actions)
        hint = QLabel("Doble clic o F2 para editar. Clic en Estado o Valoración para cambiarlos.")
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        layout.addWidget(hint)
