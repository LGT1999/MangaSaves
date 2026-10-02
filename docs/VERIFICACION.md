# Verificación de la migración

Fecha: 2 de octubre de 2026. Entorno: Windows, Python 3.13.3 y PySide6 6.11.2.

## Pruebas automatizadas

Las 24 pruebas de `unittest` pasan, incluidas valoraciones y temas. Cubren:

- Inicialización de bases antiguas y respaldo previo sin cambiar registros.
- Detección de la base existente y rechazo de rutas ambiguas.
- Validación de capítulos y plataformas; guardar sin cambios no escribe.
- Orden numérico de capítulos y cronológico de fechas antiguas e ISO.
- Uso del índice de fecha para consultar los últimos cinco.
- Búsqueda literal, filtros, paginación y ajuste al borrar la última fila.
- Alineación entre cabeceras y filas con textos largos en tres tamaños de ventana.
- Edición real con F2, Enter y pérdida de foco.
- Actualización de la fila sin reiniciar el modelo cuando no cambia su orden.
- Copia de nombres, cambio de estado y confirmación al eliminar.
- Conservación de búsqueda y selección después de editar u ordenar.
- Señales entre formulario, búsqueda, paginación, acciones y ventana principal.
- Normalización de la plataforma escrita y envío del formulario con Enter.
- Valoración al agregar, edición real con selector y cancelación con Escape.
- Orden descendente de opciones en ambos selectores, con Sin valorar al final como valor inicial.
- Persistencia de las siete opciones, borrado de la nota y rechazo de opciones inválidas.
- Orden por calidad antes de paginar y conservación de la selección al cambiar la nota.
- Migración con respaldo de bases Tkinter y Qt, incluso si ya tienen índices.
- Cambio de los cuatro temas sin escribir lecturas ni perder búsqueda, selección o formulario.
- Recuperación del tema al abrir otra ventana y alternativa clásica ante un valor desconocido.
- Colores del texto y etiquetas de estado acordes al tema y selector visible a 850 × 530.

Las pruebas de interfaz se ejecutan con `QT_QPA_PLATFORM=offscreen` y
`QAbstractItemModelTester` comprueba el contrato del modelo durante las
interacciones. Se generaron y revisaron capturas a 1150 × 720 y 850 × 530.
Se comprobaron las tres entradas con `--help`: `python -m MangaSaves`,
`python -m MangaSaves.app` y `python MangaSaves/app.py`. La resolución de rutas
sigue encontrando la base existente aunque los módulos estén en subcarpetas.

Se generaron capturas de cada tema a 1150 × 720 y 850 × 530 usando datos
sintéticos y preferencias temporales. Se revisaron los colores, los textos,
las etiquetas de estado y la ubicación del selector, incluyendo el tema claro.

## Compatibilidad con los datos existentes

Se abrió `MangaSaves/dist/progreso_lectura.db` en modo de solo lectura y se
trabajó sobre una copia temporal. Se verificaron sus **235 lecturas**: todos los
campos originales coinciden antes y después de inicializar la nueva aplicación;
la columna de valoración queda disponible en la copia. El hash
SHA-256 del archivo original coincide antes y después de la verificación.

## Mediciones

El paquete de Windows se generó con PyInstaller 6.22.3. Su arranque se verificó
fuera de pantalla con `tools/verify_executable.py`: creó una base temporal y
sus índices y la columna de valoración, y permaneció abierto durante la comprobación. No se
utilizó la base personal para esta prueba.

También se generó el formato de archivo único con `tools/build_app.py --onefile`
y se verificó `MangaSaves/dist/MangaSaves.exe` con el mismo comprobador. Ambos
formatos inicializan la base temporal correctamente. En Windows, el comprobador
cierra también el proceso hijo del paquete `--onefile` y retira sus archivos
extraídos de la carpeta temporal de prueba.

Mediana de 100 consultas por escenario, con caché local, usando
`tools/verify_app.py`. Incluyen la consulta y la conversión de resultados a
objetos Python; no representan el tiempo de arranque ni el de dibujar la ventana.

| Escenario | Lecturas en la base | Filas cargadas | Mediana |
| --- | ---: | ---: | ---: |
| Últimos cinco, datos existentes | 235 | 5 | 0,117 ms |
| Lista completa, primera página | 235 | 25 | 0,349 ms |
| Últimos cinco, datos sintéticos | 10 000 | 5 | 0,110 ms |
| Lista completa, datos sintéticos | 10 000 | 25 | 0,348 ms |
| Búsqueda con 10 000 coincidencias | 10 000 | 25 | 1,871 ms |

Estos valores corresponden al equipo de verificación. No se midió una
comparación de tiempos con la interfaz anterior; no se atribuye un porcentaje
de aceleración a la migración.

Al repetir la verificación se generan capturas y datos de la medición en
`verification/`. Los archivos generados se eliminaron al limpiar el proyecto;
los resultados de esta ejecución se conservan en este documento. Esa carpeta
se excluye de Git porque puede contener títulos personales. Los comandos para
repetir la verificación están en el README.
