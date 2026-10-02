"""Lecturas, estado de navegación y páginas de resultados."""

from dataclasses import dataclass

from MangaSaves.config import DEFAULT_PAGE_SIZE


RATING_OPTIONS = ("Horrible", "Malo", "Decente", "Bueno", "Muy bueno", "Increíble", "GOAT")


@dataclass(frozen=True)
class Reading:
    id: int
    nombre: str
    capitulo: str
    pagina: str
    terminado: str | None
    fecha_mod: str | None
    valoracion: str = ""

    @property
    def completed(self) -> bool:
        return self.terminado in ("Sí", "✅ Terminado")


@dataclass
class ViewState:
    mode: str = "ultimos"
    search: str = ""
    letter: str | None = None
    sort_column: str = "nombre"
    descending: bool = False
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class ReadingPage:
    rows: list[Reading]
    total: int
    page: int
    pages: int
