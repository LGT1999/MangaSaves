# MangaSaves

Aplicación de escritorio para guardar el progreso de tus lecturas, hecha con
Python, PySide6 (Qt) y SQLite. La interfaz usa una tabla real: las cabeceras y
filas comparten columnas y los títulos largos se muestran con `…`, sin mover
los otros campos.

## Organización del código

```text
MangaSaves/
├── app.py                # Entrada para el IDE y ejecución directa
├── __main__.py           # Entrada con python -m MangaSaves
├── bootstrap.py          # Argumentos, arranque de Qt y apertura de la app
├── config.py             # Nombre, tamaños y valores predeterminados
├── paths.py              # Rutas de la base y recursos del ejecutable
├── domain/
│   ├── models.py         # Lecturas y estado de navegación
│   └── validation.py     # Validación de capítulos y valoraciones
├── persistence/
│   ├── repository.py     # SQLite, respaldos y operaciones de datos
│   └── queries.py        # Filtros y orden SQL
├── ui/
│   ├── main_window.py    # Coordinación de la ventana y sus eventos
│   ├── widgets.py        # Formulario, búsqueda, tabla, paginación y acciones
│   ├── table_model.py    # Datos y edición de celdas en Qt
│   ├── delegates.py      # Dibujo de las etiquetas de estado
│   ├── themes.py         # Paletas y preferencias de apariencia
│   └── styles.qss        # Colores, fuentes y apariencia
└── Img/                  # Iconos
```

Para cambiar el diseño, edita `ui/styles.qss` o `ui/widgets.py`; los colores de
cada tema están en `ui/themes.py`. Para modificar
la búsqueda o el almacenamiento, usa `persistence`. Las reglas y estructuras
de datos están en `domain`. La ventana conecta estas partes sin concentrar
la construcción de controles ni las consultas SQL en un solo archivo.

## Abrir en Windows

El ejecutable actualizado se genera en:

```text
MangaSaves/dist/MangaSaves/MangaSaves.exe
```

Abre ese archivo con doble clic. Si lo llevas a otro equipo, copia **toda la
carpeta `MangaSaves` del ejecutable**, incluyendo `_internal`. La compilación es
en una carpeta para evitar la extracción temporal de una distribución
`--onefile` en cada arranque.

También puedes generar un único archivo `MangaSaves/dist/MangaSaves.exe`
con la opción `--onefile` descrita más abajo. Ese ejecutable no necesita una
carpeta `_internal` a su lado. Para conservar tus lecturas al trasladarlo,
copia también `progreso_lectura.db` junto al `.exe`.

## Ejecutar desde el código

Requiere Python 3.10 o posterior. Se verificó con Python 3.13.3 y PySide6 6.11.2.
Los comandos siguientes se ejecutan en PowerShell desde la raíz del proyecto.

Si ya existe el entorno `.venv`, puedes abrir la nueva interfaz directamente:

```powershell
.\.venv\Scripts\python.exe -m MangaSaves
```

Para instalarla desde cero:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m MangaSaves
```

Si `py` no encuentra Python, usa la ruta de tu instalación para crear el entorno:

```powershell
& 'C:\ruta\a\python.exe' -m venv .venv
```

También puedes ejecutar `MangaSaves/app.py` directamente desde tu IDE;
selecciona `.venv/Scripts/python.exe` como intérprete.
El comando anterior `python -m MangaSaves.app` también sigue funcionando.

## Tus datos existentes

La tabla `lecturas` y sus campos mantienen el formato de la versión anterior.
No tienes que exportar ni convertir los registros. La base encontrada durante
esta actualización está en `MangaSaves/dist/progreso_lectura.db`.

La aplicación busca `progreso_lectura.db` junto al código o ejecutable, en el
directorio desde el que la abres, en la subcarpeta `dist` y en la carpeta padre.
Si hay una sola base, la utiliza. Si encuentra varias bases distintas, pide
seleccionar explícitamente una ruta al ejecutar; no elige una al azar.
Si no hay ninguna, crea una junto al código o ejecutable.

Para indicar una base:

```powershell
.\.venv\Scripts\python.exe -m MangaSaves --db 'B:\ruta\progreso_lectura.db'
```

Con el ejecutable:

```powershell
& '.\MangaSaves\dist\MangaSaves\MangaSaves.exe' --db 'B:\ruta\progreso_lectura.db'
```

Puedes ver la ruta completa pasando el mouse sobre el nombre de la base en la
esquina inferior derecha. La primera vez que abre una base de la versión
anterior, guarda una copia en `backups`, junto a esa base, antes de añadir
índices o el campo de valoración. Usa la API de respaldo de SQLite y conserva
los campos existentes. La actualización se hace automáticamente al abrir la app.

Para restaurar una copia, cierra la aplicación y abre el archivo respaldado
mediante `--db`, o cópialo como `progreso_lectura.db` en la ubicación que utilizas.

## Uso

- **Temas:** el selector Tema, arriba a la derecha, ofrece Oscuro clásico,
  Claro, Bosque y Violeta. El cambio se aplica al instante y se recuerda al
  volver a abrir la app, tanto desde Python como desde el ejecutable.
  La elección es por usuario y se guarda en
  `%APPDATA%/MangaSaves/MangaSaves.ini`, separada de las lecturas. Si la opción
  guardada ya no existe, se utiliza Oscuro clásico. Cambiar de tema conserva
  la búsqueda, selección, página y texto pendiente del formulario.
- **Agregar:** completa nombre, capítulo y plataforma; pulsa Agregar o Enter.
  Los capítulos aceptan números como `2`, `2.3` y `0.5`. Puedes elegir una
  valoración en el formulario o dejarla sin asignar.
- **Editar:** doble clic o F2 en capítulo o plataforma. Enter o salir de la celda
  guarda; Escape cancela. Solo se escribe si el valor cambió. La plataforma se
  normaliza a mayúsculas al guardar.
- **Estado:** clic en la etiqueta Leyendo/Terminado para alternarlo.
- **Valoración:** clic en la celda o F2 para abrir el selector. Las opciones son
  GOAT, Increíble, Muy bueno, Bueno, Decente, Malo y Horrible, en ese orden. Seleccionar una
  opción guarda el cambio; Escape cancela. Sin valorar aparece al final y permite quitar la nota.
  Las lecturas existentes empiezan sin valoración.
- **Copiar un título:** clic en su nombre copia el texto completo.
- **Títulos largos:** pasa el mouse para leer el nombre completo. La columna
  Nombre aprovecha el espacio disponible; las otras se ajustan arrastrando los
  bordes de las cabeceras.
- **Últimos cinco:** vista inicial, ordenada por modificación más reciente.
- **Lista completa:** permite filtrar por letra inicial, incluyendo Todas y `#`.
  La opción `#` agrupa iniciales fuera de A–Z, como números, signos, Ñ y vocales
  acentuadas, conservando el criterio de la versión anterior.
- **Buscar:** escribe parte del nombre o plataforma y pulsa Buscar o Enter.
  La búsqueda cubre toda la base; borrar el texto restaura la vista anterior.
- **Ordenar:** clic en una cabecera en la lista completa o búsqueda; otro clic
  invierte el orden. Los capítulos se ordenan como números y las fechas de forma
  cronológica. Valoración se ordena por calidad, de Horrible a GOAT, y no
  alfabéticamente. El orden se aplica antes de paginar.
- **Páginas:** puedes mostrar 10, 25, 50 o 100 lecturas por página. También se
  paginan las búsquedas. Si eliminas la última lectura de una página, se ajusta
  la página automáticamente.
- **Eliminar:** selecciona una fila y pulsa Eliminar seleccionado; la app pide
  confirmación.

## Generar el ejecutable

Desde Windows, instala las dependencias de desarrollo y compila:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tools\build_app.py
```

Para generar **solo un `.exe`**, como en la versión anterior:

```powershell
.\.venv\Scripts\python.exe tools\build_app.py --onefile
```

El resultado es `MangaSaves/dist/MangaSaves.exe`. Incluye Python, Qt, iconos y
estilos; puedes copiar ese archivo sin `_internal`. Al abrirse, extrae las
dependencias a una carpeta temporal, por lo que el arranque puede tardar más
que con el paquete en carpeta. La interfaz y sus funciones son las mismas.
Ambos formatos se generan en rutas distintas y pueden coexistir.

El constructor incluye los iconos de `MangaSaves/Img` y el archivo de estilos
`MangaSaves/ui/styles.qss`. La base de datos no se incluye en el paquete; se mantiene
como archivo independiente. Los archivos de compilación se recrean en
`MangaSaves/build`; puedes eliminar esa carpeta después de compilar.

## Pruebas y mantenimiento

Para comprobar el arranque del ejecutable sin abrir una ventana ni utilizar
tus datos, después de compilar:

```powershell
.\.venv\Scripts\python.exe tools\verify_executable.py
```

Para verificar el ejecutable único:

```powershell
.\.venv\Scripts\python.exe tools\verify_executable.py --exe '.\MangaSaves\dist\MangaSaves.exe'
```

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas usan bases temporales e interfaz fuera de pantalla. Comprueban
compatibilidad, guardado, orden, búsqueda, paginación, selección y alineación.
También comprueban el cambio de temas y la recuperación de la preferencia al reiniciar.

Para repetir la verificación con tus datos, sin escribir en la base original:

```powershell
.\.venv\Scripts\python.exe tools\verify_app.py --db '.\MangaSaves\dist\progreso_lectura.db'
```

Genera capturas y `report.json` en `verification/`, utilizando una copia temporal
de la base, y mide consultas contra 10 000 lecturas de prueba.

Las carpetas `build`, `verification` y `__pycache__` son temporales y se pueden
eliminar. `.venv` contiene las dependencias instaladas. `MangaSaves/dist`
contiene el ejecutable actualizado y tu base de datos: conserva esos archivos.
Los datos, el entorno y los archivos generados están excluidos de Git.

Consulta [la arquitectura y las decisiones de mantenimiento](docs/ARQUITECTURA.md)
y [los resultados de verificación](docs/VERIFICACION.md).
