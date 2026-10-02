# Arquitectura y mantenimiento

## Archivos

| Archivo | Responsabilidad |
| --- | --- |
| `MangaSaves/app.py`, `__main__.py` | Puntos de entrada para el IDE y ejecución como paquete. |
| `MangaSaves/bootstrap.py` | Argumentos, preparación de Qt y apertura de la ventana. |
| `MangaSaves/config.py` | Configuración compartida sin dependencias gráficas. |
| `MangaSaves/paths.py` | Ubicaciones de bases y recursos, desde el código y el ejecutable. |
| `MangaSaves/domain/models.py` | Lectura, escala de valoración, estado de navegación y página de resultados. |
| `MangaSaves/domain/validation.py` | Validaciones de capítulos y valoraciones, independientes de Qt y SQLite. |
| `MangaSaves/persistence/repository.py` | Conexión, esquema, respaldo y operaciones SQLite. |
| `MangaSaves/persistence/queries.py` | Expresiones de orden y filtros parametrizados. |
| `MangaSaves/ui/main_window.py` | Coordinación de eventos, selección y navegación. |
| `MangaSaves/ui/widgets.py` | Formulario, búsqueda, tabla, paginación y acciones. |
| `MangaSaves/ui/table_model.py` | Modelo de tabla, roles de Qt y edición de celdas. |
| `MangaSaves/ui/delegates.py` | Dibujo del estado y editor temporal de valoración. |
| `MangaSaves/ui/styles.qss` | Colores, fuentes y reglas visuales. |
| `MangaSaves/ui/themes.py` | Paletas de temas, aplicación del estilo y preferencias por usuario. |
| `requirements.txt` | Dependencia de ejecución fijada a PySide6 6.11.2. |
| `requirements-dev.txt` | Dependencias para compilar el ejecutable. |
| `tools/build_app.py` | Empaquetado para Windows con PyInstaller. |
| `tools/verify_app.py` | Capturas y mediciones con bases temporales. |
| `tools/verify_executable.py` | Verificación de arranque del ejecutable con una base temporal. |
| `tests/` | Pruebas de SQLite y de interacciones reales con Qt. |

## Dependencias entre módulos

`domain` contiene estructuras de datos y validaciones; no importa Qt ni
SQLite. `persistence` usa esas estructuras para leer y escribir. `ui` usa el
repositorio y los modelos del dominio para mostrar y editar las lecturas.
`bootstrap` inicia la aplicación y `app.py` conserva la ejecución desde el IDE.

Los componentes de `ui/widgets.py` emiten señales como `submitted`,
`search_requested` y `size_changed`. La ventana conecta esas señales con sus
operaciones. Los widgets no ejecutan consultas SQL ni deciden qué datos guardar.

Los estilos se cargan desde `ui/styles.qss`. `paths.resource_path` resuelve la
misma ruta dentro del código y del paquete de PyInstaller, que incluye los
recursos bajo `MangaSaves/`. La carpeta de los datos se resuelve por separado,
por lo que mover módulos a subcarpetas no cambia la base utilizada.

`styles.qss` es una plantilla con variables `$background`, `$text`, etc.
`ui/themes.py` define las cuatro paletas y sustituye las variables con
`string.Template`; también configura `QPalette` para controles y estados que
dependen del estilo de Qt. Los colores del texto de la tabla y del delegado de
estado proceden del mismo tema, incluyendo lecturas terminadas y fechas.
Para añadir un tema, incorpora una entrada en `THEMES` con todas las claves
de color de la paleta clásica: aparecerá automáticamente en el selector.

`ThemeSelector` emite la elección y la ventana aplica la paleta sin recargar
SQLite ni reiniciar el modelo. Solo se notifica el cambio de color de las
celdas y se repinta la tabla. `QSettings` guarda `appearance/theme` en formato
INI por usuario, bajo `%APPDATA%/MangaSaves/MangaSaves.ini` en Windows;
la preferencia es compartida entre los formatos de ejecutable y la ejecución
desde el código. Un valor desconocido vuelve al tema clásico. Si el archivo
no puede guardarse, un mensaje indica que el tema solo se aplicó a la sesión.
El constructor de la ventana admite un `QSettings` alternativo: las pruebas y
el verificador visual usan archivos temporales y no modifican las preferencias
personales.

## Dónde hacer cambios

- Paletas de colores: `ui/themes.py`; tipografía y reglas de estilo: `ui/styles.qss`.
- Distribución y controles: `ui/widgets.py`.
- Acciones de la ventana y navegación: `ui/main_window.py`.
- Presentación y edición de una celda: `ui/table_model.py` y `ui/delegates.py`.
- Reglas de capítulos y estructuras de lectura: `domain`.
- Filtros y orden SQL: `persistence/queries.py`.
- Guardado, respaldo y esquema: `persistence/repository.py`.
- Opciones de inicio y rutas: `bootstrap.py` y `paths.py`.

## Tabla y distribución

`QTableView` contiene cabeceras y filas dentro del mismo componente. Cada
columna tiene una única posición y ancho. Nombre utiliza el modo `Stretch` de
`QHeaderView`; las demás permiten cambiar el ancho. Los textos usan
`ElideRight` y el rol `ToolTipRole` conserva el contenido completo.

`ReadingTableModel`, basado en `QAbstractTableModel`, mantiene únicamente las
lecturas de la página actual. Qt pinta las celdas y crea un editor temporal
cuando se empieza a editar capítulo o plataforma. `StatusDelegate` pinta la
etiqueta de estado sin crear un botón por registro.
`RatingDelegate` crea un `QComboBox` temporal para elegir la valoración; al
seleccionar una opción confirma el editor y lo cierra. Las opciones proceden
de `domain.models.RATING_OPTIONS`, también usada en el formulario y en SQL.
Los selectores presentan la escala en orden descendente (GOAT primero), con
Sin valorar al final como valor inicial. La escala del dominio conserva el
orden ascendente para las consultas SQL.

La barra para agregar y la de búsqueda están en filas separadas con layouts de
Qt, para que sus textos no determinen el ancho de la tabla. Las instrucciones
permiten saltos de línea y los avisos temporales evitan insertar títulos largos
en la barra inferior.

## Guardado y actualización

1. El modelo envía el nuevo valor al repositorio.
2. El repositorio valida y compara con el valor guardado. Si es igual, no hace
   `UPDATE`, `commit` ni cambia la fecha.
3. Si cambió, actualiza el campo y `fecha_mod` dentro de una transacción.
4. El modelo reemplaza esa lectura y emite `dataChanged` para la fila.
5. Si la edición afecta el orden o un filtro, la ventana programa una consulta
   con un temporizador de Qt. Se hace después de confirmar el editor para evitar
   cambiar su índice mientras `setData` sigue ejecutándose.

Cuando una consulta devuelve los mismos identificadores en el mismo orden,
`replace_rows` actualiza únicamente las filas diferentes. Si cambian las filas
o su orden, se reinicia el modelo de datos conservando la selección por ID
cuando esa lectura sigue visible. La tabla y sus controles permanecen creados.

## Consultas y estado de navegación

`ViewState` guarda modo, búsqueda activa, letra, orden, página y tamaño de
página. La búsqueda tiene prioridad sobre el filtro de letra; al borrarla se
restaura ese filtro. Editar no elimina la búsqueda ni vuelve a los últimos cinco.

Las consultas aplican `WHERE`, `ORDER BY`, `LIMIT` y `OFFSET` en SQLite. Se
cargan cinco lecturas recientes o, como máximo, 100 lecturas por página. El
repositorio recalcula el número de páginas y corrige los límites después de
eliminar registros.

Los valores van en parámetros SQL. Las expresiones de orden y los campos
editables proceden de listas permitidas, no del texto del usuario. En la
búsqueda, `%`, `_` y `\` se escapan para tratarlos como texto literal.

## Compatibilidad de la base

Se mantienen la tabla y los seis campos originales: `id`, `nombre`, `capitulo`,
`pagina`, `terminado` y `fecha_mod`. Se reconocen tanto `Sí` como
`✅ Terminado` en datos antiguos. Las plataformas existentes se muestran en
mayúsculas; abrir la app no reescribe sus valores.

Se añade `valoracion TEXT NOT NULL DEFAULT ''` con una restricción `CHECK` que
permite la escala Horrible, Malo, Decente, Bueno, Muy bueno, Increíble y GOAT,
además del texto vacío para Sin valorar. `PRAGMA table_info` detecta si falta
la columna; `ALTER TABLE ... ADD COLUMN` la incorpora sin reconstruir la tabla
ni modificar los seis campos anteriores. La migración y los índices se
confirman en una transacción. Abrir una base ya actualizada no repite la migración.

El repositorio valida la valoración antes de escribir. Al ordenar por esta
columna, `queries.RATING_SORT_SQL` usa el orden de la escala, en vez del orden
alfabético. Sin valorar aparece primero en orden ascendente y último en
descendente. Editar la valoración actualiza `fecha_mod` igual que los demás
campos editables; guardar el mismo valor no escribe.

Las fechas anteriores `DD/MM/YYYY HH:MM` se conservan. Los nuevos cambios se
guardan con segundos (`DD/MM/YYYY HH:MM:SS`). `DATE_SQL` transforma las fechas
para ordenarlas; también admite fechas ISO. La interfaz conserva la fecha
guardada como texto. Se utiliza la hora local del equipo.

Se añaden tres índices, sin reconstruir la tabla:

- `idx_lecturas_nombre_v2`: nombre con `COLLATE NOCASE` e ID.
- `idx_lecturas_capitulo_v2`: capítulo convertido a número e ID.
- `idx_lecturas_fecha_v2`: expresión de fecha e ID descendentes.

Antes de incorporar índices o la columna de valoración a una base existente, se hace un respaldo
con `sqlite3.Connection.backup`. Su nombre contiene fecha, hora y microsegundos;
la conexión de destino se cierra explícitamente. La presencia del índice de
fecha y la presencia de la columna identifican una base ya actualizada y
evitan crear un respaldo en cada apertura. También se respalda la versión Qt
que tiene índices pero todavía no valoración. La base utilizada para las pruebas se abrió solamente
en modo lectura; todas las modificaciones se probaron en copias temporales.

## Rendimiento y límites

La mejora principal elimina la creación y destrucción de widgets por fila y
los guardados sin cambios. El índice de fecha evita ordenar toda la base para
mostrar los últimos cinco. La búsqueda por contenido (`%texto%`) puede recorrer
la tabla, aunque devuelve solo una página.

Las consultas se ejecutan en el hilo de la interfaz. Con la base actual y
10 000 registros de prueba fueron cortas; si el volumen o la latencia del disco
crecen, se puede añadir un trabajador con su propia conexión SQLite y entregar
resultados al hilo principal mediante señales. Los modelos y widgets de Qt se
actualizan desde el hilo principal.

`LIKE` y `COLLATE NOCASE` de SQLite conservan el comportamiento básico de la
versión anterior: ignoran mayúsculas en ASCII, pero no realizan búsqueda
lingüística ni equivalencia general de acentos. Para ampliar esa función se
necesita una política explícita de normalización o un índice de búsqueda.

Las dependencias de Qt y el paquete de Windows ocupan más espacio que una
interfaz sencilla de Tkinter. El ejecutable se genera en una carpeta para
reducir el trabajo de extracción al arrancar. `tools/build_app.py --onefile`
genera alternativamente un único `.exe` con las dependencias incorporadas,
que se extraen a una carpeta temporal al iniciar. Los recursos se leen desde
`sys._MEIPASS` en ambos formatos; la base permanece fuera del paquete, junto
al ejecutable o en la ruta seleccionada. Cada formato usa su propia carpeta
de trabajo en `MangaSaves/build` y una ruta de salida distinta en `dist`.

## Referencias

- [QTableView](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QTableView.html)
- [QAbstractTableModel](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractTableModel.html)
- [QStyledItemDelegate](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QStyledItemDelegate.html)
- [QHeaderView](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QHeaderView.html)
