# Changelog

Todas las novedades relevantes de OniriFix se documentan aquí. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[Versionado Semántico](https://semver.org/lang/es/).

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
