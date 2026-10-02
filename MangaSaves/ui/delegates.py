"""Dibujo de celdas especiales sin controles permanentes por fila."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QComboBox, QStyledItemDelegate, QStyle, QStyleOptionViewItem

from MangaSaves.domain.models import RATING_OPTIONS
from MangaSaves.ui.themes import DEFAULT_THEME, THEMES


def populate_ratings(combo: QComboBox):
    """Comparte las mismas opciones entre el formulario y el editor de celda."""
    for rating in reversed(RATING_OPTIONS):
        combo.addItem(rating, rating)
    combo.addItem("Sin valorar", "")
    combo.setCurrentIndex(combo.findData(""))


class RatingDelegate(QStyledItemDelegate):
    """Crea un selector únicamente mientras se está editando la valoración."""

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.setAccessibleName("Valoración de la lectura")
        populate_ratings(editor)
        editor.activated.connect(lambda: self._commit(editor))
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.ItemDataRole.EditRole)
        editor.setCurrentIndex(max(0, editor.findData(value)))
        # Espera a que Qt muestre el editor antes de desplegar sus opciones.
        QTimer.singleShot(0, editor, editor.showPopup)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect.adjusted(2, 5, -2, -5))

    def _commit(self, editor):
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)


class StatusDelegate(QStyledItemDelegate):
    """Dibuja una etiqueta de estado; no crea un QPushButton por fila."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = THEMES[DEFAULT_THEME]

    def paint(self, painter: QPainter, option, index):
        background = QStyleOptionViewItem(option)
        self.initStyleOption(background, index)
        text = background.text
        background.text = ""
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, background, painter, option.widget)
        rect = option.rect.adjusted(10, 10, -10, -10)
        completed = index.model().rows[index.row()].completed
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        colors = self.theme.colors
        painter.setBrush(QColor(colors["completed" if completed else "reading"]))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor(colors["completed_text" if completed else "reading_text"]))
        label = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, max(0, rect.width() - 12))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()
