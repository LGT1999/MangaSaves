"""Expresiones de orden y filtros SQL parametrizados."""

from MangaSaves.domain.models import RATING_OPTIONS, ViewState


LEGACY_FIELDS = "id, nombre, capitulo, pagina, terminado, fecha_mod"
FIELDS = f"{LEGACY_FIELDS}, valoracion"
RATING_VALUES_SQL = ", ".join("'" + value.replace("'", "''") + "'" for value in ("", *RATING_OPTIONS))
RATING_SORT_SQL = "CASE valoracion " + " ".join(
    f"WHEN '{value.replace(chr(39), chr(39) * 2)}' THEN {rank}"
    for rank, value in enumerate(RATING_OPTIONS, start=1)
) + " ELSE 0 END"
# Conserva las fechas antiguas DD/MM/YYYY y admite también fechas ISO.
DATE_SQL = """COALESCE(CASE WHEN substr(fecha_mod, 3, 1) = '/'
    THEN substr(fecha_mod, 7, 4) || '-' || substr(fecha_mod, 4, 2) || '-'
         || substr(fecha_mod, 1, 2) || substr(fecha_mod, 11)
    ELSE fecha_mod END, '')"""
SORT_SQL = {
    "nombre": "nombre COLLATE NOCASE",
    "capitulo": "CAST(capitulo AS REAL)",
    "pagina": "pagina COLLATE NOCASE",
    "estado": "CASE WHEN terminado IN ('Sí', '✅ Terminado') THEN 1 ELSE 0 END",
    "valoracion": RATING_SORT_SQL,
    "fecha": DATE_SQL,
}


def filter_clause(state: ViewState) -> tuple[str, tuple]:
    if state.search:
        # Los comodines escritos por el usuario son texto literal.
        text = state.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return (
            "WHERE (nombre LIKE ? ESCAPE '\\' OR pagina LIKE ? ESCAPE '\\')",
            (f"%{text}%", f"%{text}%"),
        )
    if state.letter == "#":
        return "WHERE nombre NOT GLOB '[A-Za-z]*'", ()
    if state.letter:
        return "WHERE nombre LIKE ?", (f"{state.letter}%",)
    return "", ()
