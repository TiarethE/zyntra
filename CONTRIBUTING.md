# Cómo contribuir a Zyntra

Este documento define cómo se controlan los cambios del proyecto: ramas, commits, revisiones y versiones.

## Flujo de trabajo

Zyntra usa **GitHub Flow** con revisión obligatoria:

1. **Issue.** Todo cambio empieza con un issue que explica el contexto, qué se hará y sus criterios de aceptación.
2. **Rama.** Se crea una rama desde `main` con el número del issue.
3. **Commits.** Se trabaja en la rama con commits pequeños que dejan las pruebas pasando.
4. **Pull request.** Se abre un PR hacia `main` con la plantilla, que enlaza el issue (`Closes #N`) y muestra la evidencia de pruebas.
5. **Revisión.** GitHub Actions corre las pruebas. Otra persona revisa el código y aprueba.
6. **Merge.** Se une a `main` con *merge commit* y se borra la rama. El issue se cierra solo.
7. **Versión.** Al cerrar un conjunto de cambios se actualiza `CHANGELOG.md` y se crea una etiqueta.

`main` siempre está estable: nunca se hace commit directo sobre ella.

## Nombres de ramas

`<tipo>/<número-de-issue>-<descripción-corta>`

| Tipo | Uso | Ejemplo |
| --- | --- | --- |
| `feature/` | Funcionalidad nueva | `feature/2-reintentos-notificaciones` |
| `fix/` | Corrección de un error | `fix/12-redondeo-seguro` |
| `docs/` | Documentación, diagramas o procesos | `docs/1-estrategia-ramas-ci` |
| `release/` | Preparación de una versión | `release/2.0` |

Las ramas `feature/` del Primer Parcial (sin número de issue) son anteriores a esta convención y se conservan como historial.

## Mensajes de commit

- Primera línea en imperativo y en español, de 72 caracteres o menos: «Agrega reintentos con espera exponencial».
- Cuerpo opcional con el porqué del cambio.
- Referencia al issue al final: `Refs #2`.

## Pull requests

Un PR está listo para merge cuando:

- [ ] Enlaza su issue y cumple sus criterios de aceptación.
- [ ] Las pruebas de GitHub Actions pasan.
- [ ] Agrega o actualiza pruebas para lo que cambia.
- [ ] Si cambia una clase dibujada, actualiza `docs/uml` (lo verifica `tests/test_diagramas.py`).
- [ ] Agrega una línea en la sección «Sin publicar» de `CHANGELOG.md`.
- [ ] Tiene al menos una aprobación.

## Versiones

Se usa [versionado semántico](https://semver.org/lang/es/): `MAYOR.MENOR.PARCHE`.

- **MAYOR**: cambios que rompen la forma de usar el sistema.
- **MENOR**: funcionalidad nueva compatible.
- **PARCHE**: correcciones.

Cada versión tiene una etiqueta anotada (`git tag -a vX.Y -m "..."`) y su sección en `CHANGELOG.md`.

| Etiqueta | Entrega |
| --- | --- |
| `v0.1` | Código de partida |
| `v1.0` | Primer Parcial: patrones de diseño |
| `v2.0` | Segundo Parcial: módulo de respuesta en tiempo real |

## Cómo correr las pruebas

```bash
python -m unittest -v
```
