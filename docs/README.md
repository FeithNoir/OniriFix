# Documentación de OniriFix

## Estructura

```text
docs/
  README.md        Este índice
  files/           Guías y referencias
  screenshots/     Capturas de la consola (01–08) y de la ventana (09–15)
```

## Guías

| Documento | Para qué |
| :--- | :--- |
| [`files/instalacion.md`](files/instalacion.md) | Instalador, ejecutables portables (`OniriFix.exe`, `OniriFix-GUI.exe`) y compilación. |
| [`files/arquitectura.md`](files/arquitectura.md) | Capas, módulos (incluida la GUI) y flujo de datos. |
| [`files/reglas.md`](files/reglas.md) | Catálogo de las 42 reglas, niveles y configuración. |
| [`files/cobertura-informe.md`](files/cobertura-informe.md) | Qué pide el informe editorial, qué regla lo cubre y qué queda manual. |
| [`files/registro.md`](files/registro.md) | Registro SQLite de obras, nombres y términos. |
| [`files/diseno_cli.md`](files/diseno_cli.md) | Principios y estilo de la CLI. |
| [`files/design_guidelines.md`](files/design_guidelines.md) · [`files/architecture_guidelines.md`](files/architecture_guidelines.md) | Pautas de diseño y arquitectura. |
| [`files/project.md`](files/project.md) | Especificación original. |

## Recorridos sugeridos

- **Quiero corregir mi manuscrito con ventana:** README → «Interfaz de
  escritorio», después `cobertura-informe.md` para saber qué revisar a mano.
- **Quiero usar la consola o automatizar:** README → «Inicio rápido» y
  `diseno_cli.md`.
- **Quiero añadir una regla:** `reglas.md` → «Añadir una regla» y
  `arquitectura.md`.
