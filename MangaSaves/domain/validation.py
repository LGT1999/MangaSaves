"""Validaciones de los datos introducidos por el usuario."""

import re

from MangaSaves.domain.models import RATING_OPTIONS


def validate_chapter(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("El capítulo debe ser un número, por ejemplo: 2, 2.3 o 0.5.")
    return value


def validate_rating(value: str) -> str:
    value = value.strip()
    if value and value not in RATING_OPTIONS:
        raise ValueError("Elige una valoración de la lista.")
    return value
