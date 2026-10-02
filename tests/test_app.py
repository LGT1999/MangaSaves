import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QAbstractItemModelTester, QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QMessageBox, QPushButton

from MangaSaves.domain.models import RATING_OPTIONS
from MangaSaves.ui.main_window import AppLectura
from MangaSaves.ui.table_model import COLUMNS
from MangaSaves.ui.themes import DEFAULT_THEME, THEMES


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setStyle("Fusion")
        font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings_path = Path(self.temp.name) / "settings.ini"
        self.settings = QSettings(str(self.settings_path), QSettings.Format.IniFormat)
        self.window = AppLectura(Path(self.temp.name) / "test.db", self.settings)
        self.window.show()
        self.application.processEvents()
        self.model_tester = QAbstractItemModelTester(
            self.window.model, QAbstractItemModelTester.FailureReportingMode.Warning, self.window
        )

    def tearDown(self):
        self.window.close()
        self.application.processEvents()
        self.temp.cleanup()

    def add(self, name="Un título muy largo " * 10, chapter="2.3", platform="mh"):
        self.window.form.name_input.setText(name)
        self.window.form.chapter_input.setText(chapter)
        self.window.form.platform_input.setText(platform)
        QTest.mouseClick(self.window.form.add_button, Qt.MouseButton.LeftButton)
        self.application.processEvents()

    def test_theme_switch_preserves_data_form_search_and_selection(self):
        self.add("Mi lectura")
        self.window.alternar_modo_vista()
        self.window.toolbar.search_input.setText("Mi")
        self.window.ejecutar_busqueda()
        self.window.table.selectRow(0)
        selected = self.window.selected_id()
        self.window.form.name_input.setText("Borrador sin guardar")
        before = self.window.repository.conn.total_changes
        reset = QSignalSpy(self.window.model.modelReset)
        selector = self.window.theme_control.selector
        for key, theme in THEMES.items():
            selector.setCurrentIndex(selector.findData(key))
            self.application.processEvents()
            self.assertEqual(self.window.theme_key, key)
            self.assertIn(theme.colors["background"], self.window.styleSheet())
            delegate = self.window.table.itemDelegateForColumn(COLUMNS.index("estado"))
            self.assertEqual(delegate.theme, theme)
            self.assertEqual(self.window.model.index(0, 0).data(Qt.ItemDataRole.ForegroundRole).name(),
                             theme.colors["text"])
            self.assertEqual(self.window.model.index(0, COLUMNS.index("fecha")).data(
                Qt.ItemDataRole.ForegroundRole).name(), theme.colors["muted"])
            self.assertEqual(self.window.selected_id(), selected)
            self.assertEqual((self.window.state.search, self.window.state.page), ("Mi", 1))
            self.assertEqual(self.window.form.name_input.text(), "Borrador sin guardar")
        self.assertEqual(self.window.repository.conn.total_changes, before)
        self.assertEqual(reset.count(), 0)

    def test_theme_choice_survives_window_restart(self):
        selector = self.window.theme_control.selector
        selector.setFocus()
        QTest.keyClick(selector, Qt.Key.Key_Down)
        self.application.processEvents()
        self.assertEqual(self.window.theme_key, "light")
        self.window.close()
        settings = QSettings(str(self.settings_path), QSettings.Format.IniFormat)
        reopened = AppLectura(Path(self.temp.name) / "test.db", settings)
        try:
            self.assertEqual(reopened.theme_key, "light")
            self.assertEqual(reopened.theme_control.selector.currentData(), "light")
            self.assertIn(THEMES["light"].colors["background"], reopened.styleSheet())
        finally:
            reopened.close()

    def test_unknown_saved_theme_falls_back_to_classic(self):
        self.settings.setValue("appearance/theme", "removed-theme")
        reopened = AppLectura(Path(self.temp.name) / "other.db", self.settings)
        try:
            self.assertEqual(reopened.theme_key, DEFAULT_THEME)
            self.assertEqual(reopened.theme_control.selector.currentData(), DEFAULT_THEME)
        finally:
            reopened.close()

    def test_theme_selector_fits_small_window_in_every_theme(self):
        self.window.resize(850, 530)
        for key in THEMES:
            selector = self.window.theme_control.selector
            selector.setCurrentIndex(selector.findData(key))
            self.application.processEvents()
            self.assertGreaterEqual(selector.width(), selector.minimumSizeHint().width())
            self.assertLessEqual(self.window.theme_control.geometry().right(), self.window.centralWidget().width())
            self.assertTrue(self.window.grab().width() == 850)

    def test_long_titles_keep_columns_aligned_at_different_sizes(self):
        self.add()
        self.add("Corto")
        for width, height in ((1150, 720), (850, 530), (1450, 800)):
            self.window.resize(width, height)
            self.application.processEvents()
            table = self.window.table
            header = table.horizontalHeader()
            for column in range(self.window.model.columnCount()):
                self.assertEqual(table.columnViewportPosition(column), header.sectionViewportPosition(column))
                self.assertEqual(table.visualRect(table.model().index(0, column)).width(), header.sectionSize(column))
            self.assertLessEqual(self.window.toolbar.view_button.geometry().right(), self.window.centralWidget().width())
            self.assertEqual(table.model().index(0, 0).data(Qt.ItemDataRole.ToolTipRole), "Corto")
        # No hay botones ni editores permanentes en las filas.
        self.assertEqual(self.window.table.findChildren(QPushButton), [])
        self.assertEqual(self.window.table.findChildren(QLineEdit), [])

    def test_edit_saves_only_changed_cell_and_no_reset(self):
        self.add("Mi lectura")
        self.window.alternar_modo_vista()
        reset = QSignalSpy(self.window.model.modelReset)
        changed = QSignalSpy(self.window.model.dataChanged)
        index = self.window.model.index(0, 1)
        before = self.window.repository.conn.total_changes
        self.assertTrue(self.window.model.setData(index, "2.3"))
        self.assertEqual(self.window.repository.conn.total_changes, before)
        self.assertEqual(changed.count(), 0)
        self.assertTrue(self.window.model.setData(index, "55"))
        self.application.processEvents()
        self.assertEqual(self.window.model.rows[0].capitulo, "55")
        self.assertEqual(reset.count(), 0)
        self.assertEqual(changed.count(), 1)
        with patch.object(QMessageBox, "warning") as warning:
            self.assertFalse(self.window.model.setData(index, "abc"))
            warning.assert_called_once()
        self.assertEqual(self.window.model.rows[0].capitulo, "55")

    def test_real_editor_return_and_focus_out(self):
        self.add("Mi lectura")
        self.window.alternar_modo_vista()
        index = self.window.model.index(0, 1)
        self.window.table.setCurrentIndex(index)
        QTest.keyClick(self.window.table, Qt.Key.Key_F2)
        self.application.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        self.assertIsNotNone(editor)
        editor.selectAll()
        QTest.keyClicks(editor, "42.5")
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.application.processEvents()
        self.assertEqual(self.window.model.rows[0].capitulo, "42.5")
        index = self.window.model.index(0, 2)
        self.window.table.setCurrentIndex(index)
        QTest.keyClick(self.window.table, Qt.Key.Key_F2)
        self.application.processEvents()
        editor = self.window.table.findChild(QLineEdit)
        editor.selectAll()
        QTest.keyClicks(editor, "scan")
        self.window.toolbar.search_input.setFocus()
        self.application.processEvents()
        self.assertEqual(self.window.model.rows[0].pagina, "SCAN")

    def test_copy_status_and_delete_confirmation(self):
        self.add("Nombre completo")
        table = self.window.table
        index = self.window.model.index(0, 0)
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualRect(index).center())
        self.assertEqual(QApplication.clipboard().text(), "Nombre completo")
        self.assertTrue(self.window.actions.delete_button.isEnabled())
        index = self.window.model.index(0, 3)
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=table.visualRect(index).center())
        self.application.processEvents()
        self.assertTrue(self.window.model.rows[0].completed)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window.eliminar_registro()
        self.assertEqual(self.window.model.rowCount(), 1)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window.eliminar_registro()
        self.assertEqual(self.window.model.rowCount(), 0)
        self.assertFalse(self.window.actions.delete_button.isEnabled())

    def test_search_pagination_preserved_on_edit_and_clear_restores_letters(self):
        for i in range(31):
            self.window.repository.add(f"Lectura {i:02}", "1", "MH")
        self.window.alternar_modo_vista()
        self.window.toolbar.letter_selector.setCurrentIndex(self.window.toolbar.letter_selector.findData("Z"))
        self.assertEqual(self.window.model.rowCount(), 0)
        self.window.toolbar.search_input.setText("MH")
        QTest.keyClick(self.window.toolbar.search_input, Qt.Key.Key_Return)
        self.assertEqual(self.window.model.rowCount(), 25)
        self.assertTrue(self.window.toolbar.letter_selector.isHidden())
        self.window.mostrar_pagina(2)
        self.assertEqual(self.window.model.rowCount(), 6)
        self.window.model.setData(self.window.model.index(0, 2), "OTRA")
        self.application.processEvents()
        self.assertEqual((self.window.state.search, self.window.state.page), ("MH", 2))
        self.assertEqual(self.window.model.rowCount(), 5)
        self.window.toolbar.search_input.clear()
        self.assertEqual(self.window.model.rowCount(), 0)
        self.assertFalse(self.window.toolbar.letter_selector.isHidden())

    def test_sort_changes_actual_page_order_and_recent_edit_reorders(self):
        self.add("A", "10")
        self.add("B", "2")
        self.window.alternar_modo_vista()
        self.window.procesar_orden_columna(1)
        self.assertEqual([r.capitulo for r in self.window.model.rows], ["2", "10"])
        self.window.table.selectRow(1)
        selected = self.window.selected_id()
        self.window.model.setData(self.window.model.index(1, 1), "0.5")
        self.application.processEvents()
        self.assertEqual([r.capitulo for r in self.window.model.rows], ["0.5", "2"])
        self.assertEqual(self.window.selected_id(), selected)
        self.window.alternar_modo_vista()
        self.assertEqual(self.window.model.rowCount(), 2)

    def test_component_signals_connect_navigation_search_and_deletion(self):
        for i in range(31):
            self.window.repository.add(f"Alpha {i:02}", "1", "MH")
        QTest.mouseClick(self.window.toolbar.view_button, Qt.MouseButton.LeftButton)
        self.assertEqual((self.window.state.mode, self.window.model.rowCount()), ("todos", 25))
        QTest.mouseClick(self.window.pagination.next_button, Qt.MouseButton.LeftButton)
        self.assertEqual((self.window.state.page, self.window.model.rowCount()), (2, 6))
        QTest.mouseClick(self.window.pagination.previous_button, Qt.MouseButton.LeftButton)
        self.window.pagination.size_selector.setCurrentIndex(0)
        self.assertEqual((self.window.state.page_size, self.window.model.rowCount()), (10, 10))
        self.window.toolbar.search_input.setText("No existe")
        QTest.mouseClick(self.window.toolbar.search_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.model.rowCount(), 0)
        self.window.toolbar.search_input.clear()
        self.assertEqual(self.window.model.rowCount(), 10)
        self.window.table.selectRow(0)
        selected = self.window.selected_id()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            QTest.mouseClick(self.window.actions.delete_button, Qt.MouseButton.LeftButton)
        self.assertNotIn(selected, [r.id for r in self.window.model.rows])

    def test_form_normalizes_typed_platform_and_submits_with_enter(self):
        self.window.form.name_input.setText("Nueva lectura")
        self.window.form.chapter_input.setText("0.5")
        QTest.keyClicks(self.window.form.platform_input, "scan")
        self.assertEqual(self.window.form.platform_input.text(), "SCAN")
        QTest.keyClick(self.window.form.platform_input, Qt.Key.Key_Return)
        self.assertEqual(self.window.model.rows[0].pagina, "SCAN")
        self.assertEqual(self.window.form.values(), ("", "", "", ""))

    def test_rating_form_and_real_table_selector_persist_changes(self):
        self.window.form.rating_selector.setCurrentIndex(self.window.form.rating_selector.findData("Bueno"))
        self.add("Lectura valorada")
        self.assertEqual(self.window.model.rows[0].valoracion, "Bueno")
        self.assertEqual(self.window.form.rating_selector.currentData(), "")
        self.window.alternar_modo_vista()
        reset = QSignalSpy(self.window.model.modelReset)
        column = COLUMNS.index("valoracion")
        index = self.window.model.index(0, column)
        QTest.mouseClick(self.window.table.viewport(), Qt.MouseButton.LeftButton,
                         pos=self.window.table.visualRect(index).center())
        self.application.processEvents()
        editor = self.window.table.findChild(QComboBox)
        self.assertIsNotNone(editor)
        expected = [*reversed(RATING_OPTIONS), ""]
        self.assertEqual([editor.itemData(i) for i in range(editor.count())], expected)
        self.assertEqual([self.window.form.rating_selector.itemData(i)
                          for i in range(self.window.form.rating_selector.count())], expected)
        # Elige GOAT con el teclado en la lista desplegada.
        QTest.keyClick(editor, Qt.Key.Key_Home)
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.application.processEvents()
        self.assertEqual(self.window.model.rows[0].valoracion, "GOAT")
        self.assertEqual(self.window.repository.get(self.window.model.rows[0].id).valoracion, "GOAT")
        self.assertEqual(reset.count(), 0)

    def test_rating_editor_escape_cancels_and_quality_sort_preserves_selection(self):
        self.window.repository.add("A", "1", "MH", "GOAT")
        self.window.repository.add("B", "1", "MH", "Horrible")
        self.window.alternar_modo_vista()
        column = COLUMNS.index("valoracion")
        index = self.window.model.index(0, column)
        self.window.table.setCurrentIndex(index)
        QTest.keyClick(self.window.table, Qt.Key.Key_F2)
        self.application.processEvents()
        editor = self.window.table.findChild(QComboBox)
        editor.setCurrentIndex(editor.findData("Malo"))
        QTest.keyClick(editor, Qt.Key.Key_Escape)
        self.application.processEvents()
        self.assertEqual(self.window.model.rows[0].valoracion, "GOAT")
        self.window.procesar_orden_columna(column)
        self.assertEqual([r.valoracion for r in self.window.model.rows], ["Horrible", "GOAT"])
        self.window.table.selectRow(1)
        selected = self.window.selected_id()
        self.window.model.setData(self.window.model.index(1, column), "")
        self.application.processEvents()
        self.assertEqual([r.valoracion for r in self.window.model.rows], ["", "Horrible"])
        self.assertEqual(self.window.selected_id(), selected)


if __name__ == "__main__":
    unittest.main()
