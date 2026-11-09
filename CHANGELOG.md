# Changelog

Todas las novedades relevantes de OniriFix se documentan aquí. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido

- **Interfaz de escritorio** (PySide6, extra `[gui]`) con el estilo oscuro de
  TagFlow: cabecera de estado, laterales plegables, capa de espera que bloquea
  acciones simultáneas, trabajadores en segundo plano, panel de estadísticas e
  inspector con el antes y el después. Flujo abrir → elegir reglas y niveles →
  analizar → filtrar por nivel, regla, capítulo o estado → aceptar o rechazar
  L1/L2 uno a uno o en bloque → aplicar con copia de seguridad → exportar el
  informe. Los L3 son avisos de solo lectura.
- Comando `onirifix gui [ARCHIVO]`, lanzador `onirifix-gui` y ejecutable
  `OniriFix-GUI.exe` en el `.spec` y en el instalador.
- Reglas nuevas a partir del informe editorial:
  - `TIL-003` pretéritos sin tilde (inequívocos en L1, ambiguos con contexto en
    L2; `tildes.forma_rio` elige `rió` o `rio`).
  - `TIL-004` sustantivo escrito como pretérito tras determinante.
  - `TIL-005` diacríticas (`Sé`, `Sí`, `él`) e interrogativas indirectas.
  - `TIL-006` futuro en lugar de subjuntivo tras `como si`, `antes de que`…
  - `DIA-006` verbo de habla suelto; `DIA-007` inciso sin cerrar.
  - `TIP-011` elipsis corruptas, `TIP-012` signo de cierre invertido,
    `TIP-013` falta de `¿`/`¡` (L3), `TIP-014` comillas inglesas,
    `TIP-015` espacios dentro de `¿ ¡ « »`.
  - `ORT-004` minúscula tras punto.
  - `REP-005` párrafo u oración duplicados consecutivos; `REP-006` restos de
    asistente, notas de borrador y términos vetados (L3).
- `docs/files/cobertura-informe.md`: cada punto del informe con su regla, nivel
  y si es automático, asistido, señalado o manual.
- `docs/README.md` como índice de la documentación.
- `scripts/capture_gui_screenshots.py` y capturas 09–15 de la ventana.

### Cambiado

- `TIL-001` también corrige `hacía` → `hacia` cuando indica dirección.
- `TIP-007` convierte el guion simple al inicio de un diálogo en raya.
- `ORT-003` baja la confianza de las repeticiones enfáticas (`muy muy`).
- `ORT-001` incluye `aún así` → `aun así` en el mapa por defecto.
- `servicio.aplicar_seleccion` es la única vía de escritura (copia de
  seguridad + auditoría) para `corregir`, `revisar` y la GUI.
- El diff del informe parte siempre del texto que se corrigió.
- `.gitignore` excluye manuscritos, PDF y documentos privados, preferencias de
  la GUI y restos de PyInstaller y del sistema.

### Corregido

- El paquete `onirifix.informes` estaba excluido por un `informes/` del
  `.gitignore` y el repositorio no se podía importar.

## [0.1.0] — 2026-10-26

### Añadido

- Núcleo de reglas L1/L2/L3 con dry-run por defecto, copias de seguridad,
  idempotencia y trazabilidad de cada hallazgo.
- Registro SQLite multiobra: obras, personajes, lugares, términos, variantes,
  verbos de habla e historial de correcciones.
- CLI en español: `init`, `analizar`, `corregir`, `revisar`, `frecuencia`,
  `duplicados`, `reglas`, `doctor` y el árbol `registro`.
- Reglas de tipografía, diálogos, tildes contextuales, ortografía, consistencia
  onomástica, repetición, duplicados y residuo de IA.
- Informes en Markdown, CSV, JSON, diff unificado y resumen en terminal.
- Importación/exportación YAML del registro para migrar bibliotecas existentes.
- Configuración YAML con toggles por regla, umbrales y opciones de tipografía.
- Soporte opcional de spaCy, spylls y python-docx mediante extras.
- Documentación de arquitectura, catálogo de reglas, registro SQLite y diseño de
  la CLI, con un índice en `docs/README.md`.
- Suite de pruebas con golden tests, idempotencia, no-daño y CLI.
- Ejecutable portable `dist\OniriFix.exe` e instalador
  `dist\OniriFix-Setup-0.1.0.exe` con Inno Setup: accesos directos, PATH
  opcional, lanzador de consola y desinstalador.
- Icono propio, información de versión de Windows y build reproducible con
  `scripts\build_release.ps1`.
- Capturas reales de la CLI empaquetada en `docs/screenshots/`, generadas con
  `scripts/capture_screenshots.py`.
- Guía de instalación, compilación y desinstalación en
  `docs/files/instalacion.md`.

### Corregido

- La salida redirigida a un archivo o tubería en Windows ya no falla con
  `UnicodeEncodeError` al encontrar símbolos como `→`; se fuerza UTF-8 cuando
  `stdout` no es una consola.
