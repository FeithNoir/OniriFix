# Instalación y distribución

OniriFix se distribuye como una aplicación de consola autocontenida. No necesita
Python instalado en el equipo de destino: el intérprete, las dependencias y las
reglas viajan dentro del ejecutable.

## Artefactos

| Archivo | Tipo | Cuándo usarlo |
| :--- | :--- | :--- |
| `dist\OniriFix-Setup-0.1.0.exe` | Instalador Inno Setup | Uso normal en Windows: asistente, accesos directos, PATH opcional y desinstalador. |
| `dist\OniriFix.exe` | Ejecutable portable PyInstaller | Pruebas rápidas, equipos sin instalación o ejecución desde una carpeta temporal. |

Ambos contienen el mismo programa. El instalador añade configuración, ejemplos,
documentación, licencia, un lanzador de consola y las tareas de integración con
Windows.

## Requisitos

- Windows 10 u 11 de 64 bits.
- Unos 60 MB libres para la instalación.
- No requiere permisos de administrador: por defecto se instala en el perfil del
  usuario.
- No requiere conexión a internet. El núcleo es offline y determinista.

## Instalación guiada

1. Ejecuta `OniriFix-Setup-0.1.0.exe`.
2. Acepta la licencia MIT.
3. Revisa la carpeta de destino. Con privilegios de usuario queda en
   `%LOCALAPPDATA%\Programs\OniriFix`.
4. Elige las tareas opcionales:
   - **Añadir OniriFix al PATH del usuario**: permite escribir `onirifix` en
     cualquier consola nueva.
   - **Crear un acceso directo en el escritorio**.
5. Finaliza y abre **OniriFix** desde el menú Inicio.

El acceso **OniriFix** no abre el ejecutable a secas: lanza
`onirifix-shell.cmd`, que prepara una consola con:

- `ONIRIFIX_HOME=%USERPROFILE%\OniriFix`;
- la configuración de reglas copiada a esa carpeta la primera vez;
- los ejemplos copiados a `%USERPROFILE%\OniriFix\examples`;
- el directorio de instalación al frente del `PATH` de esa consola.

### Primer uso

Dentro de la consola instalada:

```bat
onirifix init
onirifix registro importar examples\obra.ejemplo.yaml
onirifix --obra oniriums analizar examples\manuscrito_ejemplo.md
onirifix --obra oniriums corregir examples\manuscrito_ejemplo.md --aplicar
onirifix doctor
```

`init` crea `data\onirifix.db` y la obra `general`. La importación añade la obra
de ejemplo `oniriums` con personajes, lugares, términos, variantes y verbos. El
análisis no toca el manuscrito; `--aplicar` escribe solo L1 y deja una copia en
`.onirifix\backups\`.

### Dónde quedan los datos

| Ruta | Contenido |
| :--- | :--- |
| `%USERPROFILE%\OniriFix\data\onirifix.db` | Registro SQLite, auditoría e historial. |
| `%USERPROFILE%\OniriFix\config\reglas.yaml` | Configuración editable. |
| `%USERPROFILE%\OniriFix\.onirifix\backups\` | Copias previas a cada escritura. |
| `%USERPROFILE%\OniriFix\informes\` | Informes Markdown, CSV, JSON y diff. |
| `%LOCALAPPDATA%\Programs\OniriFix\` | Programa, ejemplos, documentación y desinstalador. |

Puedes mover la carpeta de datos y apuntar a ella con `ONIRIFIX_HOME`, o cambiar
solo la base con `ONIRIFIX_DB`.

## Desinstalación

Usa **Configuración → Aplicaciones → OniriFix → Desinstalar**, el acceso
**Desinstalar OniriFix** del menú Inicio o:

```bat
"%LOCALAPPDATA%\Programs\OniriFix\unins000.exe"
```

El desinstalador:

- elimina el programa y los accesos directos;
- quita la carpeta de OniriFix del `PATH` del usuario si la añadió el instalador;
- **conserva** `%USERPROFILE%\OniriFix` para no borrar manuscritos, copias ni
  registro.

Si quieres una limpieza total, borra esa carpeta a mano después de desinstalar.

## Instalación silenciosa

Útil para pruebas automatizadas o despliegues internos:

```powershell
.\dist\OniriFix-Setup-0.1.0.exe `
  /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- `
  /DIR="C:\ruta\de\prueba" `
  /MERGETASKS="!addtopath,!desktopicon" `
  /LOG="C:\ruta\de\prueba\install.log"
```

`!addtopath` y `!desktopicon` desactivan esas tareas. Para desinstalar en
silencio:

```powershell
& "C:\ruta\de\prueba\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Cierra antes cualquier consola abierta desde esa instalación.

## Compilación

### Dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev,build]"
```

El extra `build` aporta `pyinstaller` y `pillow` (icono y capturas). El
instalador necesita **Inno Setup 6**:

```powershell
winget install --id JRSoftware.InnoSetup -e
```

`build_release.ps1` busca `ISCC.exe` en el `PATH` y en las rutas habituales de
Inno Setup.

### Build completo

```powershell
.\scripts\build_release.ps1
```

El script:

1. instala `.[build]`;
2. regenera `src\onirifix\assets\icon.ico` y `icon.png`;
3. compila `dist\OniriFix.exe` con `OniriFix.spec`;
4. ejecuta `pytest`;
5. compila `dist\OniriFix-Setup-0.1.0.exe` con Inno Setup.

Opciones:

```powershell
.\scripts\build_release.ps1 -SkipTests       # no ejecuta pytest
.\scripts\build_release.ps1 -SkipInstaller   # solo el ejecutable portable
```

El `.spec` declara explícitamente los módulos de `onirifix.reglas` porque el
motor los descubre con `pkgutil` en tiempo de ejecución y PyInstaller no puede
verlos. Si añades una regla nueva, actualiza la lista `REGLAS` de
`OniriFix.spec`.

### Capturas de la documentación

El script abre el ejecutable en consolas reales, espera a que termine cada
comando y fotografía el área de texto:

```powershell
.\.venv\Scripts\python.exe scripts\capture_screenshots.py
.\.venv\Scripts\python.exe scripts\capture_screenshots.py --exe "C:\ruta\OniriFix.exe"
```

Genera las ocho imágenes de `docs\screenshots\` dentro de una carpeta de trabajo
`.onirifix-demo\` (ignorada por git). Requiere una sesión de escritorio activa:
no funciona en un servidor sin interfaz gráfica.

## Verificación después de un cambio

```powershell
pytest
ruff check src tests scripts
mypy src/onirifix
.\scripts\build_release.ps1
```

Prueba manual mínima del artefacto:

```powershell
dist\OniriFix.exe --version
dist\OniriFix.exe --help
$env:ONIRIFIX_HOME = "$env:TEMP\onirifix-prueba"
dist\OniriFix.exe init
dist\OniriFix.exe registro importar examples\obra.ejemplo.yaml
dist\OniriFix.exe --obra oniriums analizar examples\manuscrito_ejemplo.md
```

Comprueba que aparecen 26 reglas activas en el análisis (28 registradas, 2
desactivadas por configuración) y que `doctor` marca como `ok` las dependencias
obligatorias.

## Problemas frecuentes

| Síntoma | Causa y solución |
| :--- | :--- |
| SmartScreen bloquea el instalador | El ejecutable no está firmado. Usa **Más información → Ejecutar de todas formas** solo con un archivo de confianza. |
| `onirifix` no se reconoce en una consola antigua | El `PATH` se actualiza en procesos nuevos. Cierra y vuelve a abrir la consola o usa el acceso del menú Inicio. |
| El instalador no encuentra `ISCC.exe` | Instala Inno Setup 6 con `winget` o compila indicando la ruta completa. |
| Acentos raros al redirigir a un archivo | Desde 0.1.0 la CLI fuerza UTF-8 cuando `stdout` no es una consola. Revisa que el visor use UTF-8. |
| `spacy`, `spylls` o `python-docx` aparecen como opcionales | Es lo esperado en el ejecutable. Solo se instalan en la versión desde código fuente con los extras `nlp`, `ortografia` o `docx`. |
| El antivirus marca el `.exe` | Falso positivo habitual de PyInstaller en archivos sin firma. Verifica el hash y el origen. |

## Estructura instalada

```text
OniriFix\
  OniriFix.exe           Programa autocontenido
  onirifix-shell.cmd     Lanzador con entorno preparado
  config\reglas.yaml     Configuración de referencia
  examples\              Obra y manuscrito de ejemplo
  docs\                  Esta guía, arquitectura, reglas y capturas
  README.md              Guía rápida
  CHANGELOG.md
  CONTRIBUTING.md
  LICENSE
  unins000.exe           Desinstalador
```
