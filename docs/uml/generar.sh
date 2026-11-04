#!/bin/sh
# Regenera las imágenes de los diagramas. Requiere Java, Graphviz y plantuml.jar.
# Uso: sh docs/uml/generar.sh /ruta/a/plantuml.jar
cd "$(dirname "$0")" && java -jar "${1:-plantuml.jar}" -tpng -o img *.puml
