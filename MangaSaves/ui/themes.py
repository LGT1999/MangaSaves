"""Paletas de la interfaz y preferencias de apariencia del usuario."""

from dataclasses import dataclass
from string import Template

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette

from MangaSaves.config import APP_NAME
from MangaSaves.paths import resource_path


@dataclass(frozen=True)
class Theme:
    name: str
    colors: dict[str, str]


DEFAULT_THEME = "dark"
_DARK = {
    "background": "#161c26", "text": "#e7edf6", "muted": "#99a9bf",
    "panel": "#1f2836", "border": "#303e52", "input": "#141c28",
    "input_border": "#3b4a60", "primary": "#285e98", "primary_border": "#3476b8",
    "primary_hover": "#3274b4", "primary_pressed": "#204c7c", "button_text": "#ffffff",
    "focus": "#66a9ed", "disabled": "#253043", "disabled_text": "#77869d",
    "secondary": "#263449", "secondary_border": "#40536f", "secondary_hover": "#334865",
    "danger": "#762f3d", "danger_border": "#9c4052", "danger_hover": "#943b4d",
    "table": "#18212e", "alternate": "#1c2736", "selection": "#2c405c",
    "selection_text": "#ffffff", "header": "#222f41", "header_text": "#bdcde1",
    "header_border": "#34445c", "scrollbar": "#455871", "tooltip_border": "#536a89",
    "reading": "#214e7e", "reading_text": "#dcecff",
    "completed": "#196c50", "completed_text": "#dcf8eb",
}

THEMES = {
    "dark": Theme("Oscuro clásico", _DARK),
    "light": Theme("Claro", {
        **_DARK,
        "background": "#f3f5f8", "text": "#182334", "muted": "#536276",
        "panel": "#ffffff", "border": "#c6cfdc", "input": "#ffffff",
        "input_border": "#a6b3c5", "primary": "#245b95", "primary_border": "#245b95",
        "primary_hover": "#1d4d80", "primary_pressed": "#173d67", "focus": "#245b95",
        "disabled": "#e0e5ed", "disabled_text": "#626f82",
        "secondary": "#e5ebf3", "secondary_border": "#b6c3d4", "secondary_hover": "#d3deed",
        "danger": "#a12e43", "danger_border": "#a12e43", "danger_hover": "#842336",
        "table": "#ffffff", "alternate": "#eef2f7", "selection": "#d5e5f9",
        "selection_text": "#132c4b", "header": "#e1e8f1", "header_text": "#253a55",
        "header_border": "#bdc9d9", "scrollbar": "#9baac0", "tooltip_border": "#a6b3c5",
        "reading": "#dceafa", "reading_text": "#17416e",
        "completed": "#d6eee3", "completed_text": "#17513b",
    }),
    "forest": Theme("Bosque", {
        **_DARK,
        "background": "#15221d", "text": "#e6f1eb", "muted": "#a5baae",
        "panel": "#1d3027", "border": "#354f42", "input": "#12231b",
        "input_border": "#486453", "primary": "#28694d", "primary_border": "#3d8965",
        "primary_hover": "#337e5c", "primary_pressed": "#20563e", "focus": "#79cba1",
        "disabled": "#283d31", "disabled_text": "#8aa291",
        "secondary": "#2a4033", "secondary_border": "#4a6655", "secondary_hover": "#365440",
        "table": "#182a21", "alternate": "#1e3228", "selection": "#355743",
        "header": "#263e31", "header_text": "#c8e2d2", "header_border": "#45644f",
        "scrollbar": "#557760", "tooltip_border": "#678d73",
        "reading": "#365843", "reading_text": "#eef8ef",
        "completed": "#28694d", "completed_text": "#e2f8ec",
    }),
    "purple": Theme("Violeta", {
        **_DARK,
        "background": "#211a2b", "text": "#efe8f8", "muted": "#b5a7c9",
        "panel": "#30253d", "border": "#4a3b5e", "input": "#1d1728",
        "input_border": "#625078", "primary": "#654394", "primary_border": "#8660b9",
        "primary_hover": "#7a53ae", "primary_pressed": "#503476", "focus": "#c39af4",
        "disabled": "#3b2e4c", "disabled_text": "#a393b7",
        "secondary": "#40314f", "secondary_border": "#6c5284", "secondary_hover": "#533f67",
        "table": "#271e33", "alternate": "#30243e", "selection": "#513d68",
        "header": "#3b2c4d", "header_text": "#dfcfef", "header_border": "#614976",
        "scrollbar": "#79608f", "tooltip_border": "#9574b3",
        "reading": "#604184", "reading_text": "#f1e7ff",
        "completed": "#315f52", "completed_text": "#e2f8ec",
    }),
}


def user_settings() -> QSettings:
    """Preferencias por usuario, compartidas entre fuente y ambos ejecutables."""
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, APP_NAME, APP_NAME)


def saved_theme(settings: QSettings) -> str:
    key = settings.value("appearance/theme", DEFAULT_THEME)
    return key if isinstance(key, str) and key in THEMES else DEFAULT_THEME


def apply_theme(widget, key: str):
    colors = THEMES[key].colors
    palette = QPalette()
    roles = {
        "Window": "background", "WindowText": "text", "Base": "input",
        "AlternateBase": "alternate", "Text": "text", "Button": "primary",
        "ButtonText": "button_text", "Highlight": "selection", "HighlightedText": "selection_text",
        "ToolTipBase": "secondary", "ToolTipText": "text", "PlaceholderText": "muted",
        "Light": "input_border", "Midlight": "panel", "Mid": "border", "Dark": "background",
    }
    for role, color in roles.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(colors[color]))
    for role in ("WindowText", "Text", "ButtonText"):
        palette.setColor(QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole, role),
                         QColor(colors["disabled_text"]))
    widget.setPalette(palette)
    stylesheet = resource_path("ui/styles.qss").read_text(encoding="utf-8")
    widget.setStyleSheet(Template(stylesheet).substitute(colors))
