# Cómo recuperar una construcción de Echosounder

## Estado real

No está disponible el fuente original. La carpeta conserva el EXE, sus DLL, nueve objetos `.o`, tres fuentes `moc_*.cpp`, un fuente `qrc_reources.cpp` y `moc_predefs.h`. **Conservar los `.o` es esencial**: se excluyeron de la subida inicial a GitHub como archivos intermedios y siguen estando únicamente en esta copia local.

Los nueve objetos coinciden con el código del ejecutable, excluyendo reubicaciones. Se puede estudiar un **reenlazado** a partir de ellos, aunque no es una recompilación de las fuentes. Para recuperar un proyecto modificable es necesario reconstruir los fuentes faltantes.

No se ha ejecutado ninguna de las construcciones descritas a continuación. Las herramientas originales no están en PATH y no se ha descargado ni instalado un SDK de varios GB como parte de este estudio.

## Entorno compatible

| Componente | Versión o configuración requerida para reproducir la construcción original |
| --- | --- |
| Sistema anfitrión | Windows x64 |
| Qt | 5.14.2, paquete para MinGW 7.3 de 64 bits |
| Compilador | GCC 7.3.0 x86_64, POSIX threads, excepciones SEH |
| Lenguaje | C++11 |
| Configuración | Release; el objeto original fue optimizado |
| Módulos Qt del enlace principal | Core, Gui, Widgets, SerialPort y PrintSupport |
| Qt adicional de ejecución | Svg y sus plugins para iconos SVG |
| Herramientas | `qmake`, `mingw32-make`, `g++`, `moc`, `uic`, `rcc`, `windeployqt` |
| Arranque Windows | Biblioteca de importación/arranque `qtmain` y runtime de MinGW del kit |

La combinación coincide con las [herramientas publicadas para Qt 5.14](https://wiki.qt.io/Qt_5.14_Tools_and_Versions). El [archivo oficial de Qt 5.14.2](https://download.qt.io/archive/qt/5.14/5.14.2/) conserva un instalador Windows de aproximadamente 2,3 GB. Que su nombre contenga `x86` no sustituye la comprobación del componente MinGW **64-bit** que se seleccione dentro del instalador.

Qt Creator facilita seleccionar el kit, pero no es necesario para invocar las herramientas desde la consola. No se deben mezclar estos `.o` de MinGW con bibliotecas Qt para MSVC, con un kit de 32 bits o con Qt 6. Cambiar de compilador o de Qt al reconstruir fuentes es otro trabajo y requiere una compilación limpia.

## Ruta A: volver a enlazar los objetos existentes

Esta ruta conserva la lógica compilada y no requiere recuperar cabeceras o `.ui` para volver a compilar clases. Sí necesita el compilador/enlazador y las bibliotecas de importación del SDK compatible. Las DLL distribuidas no contienen por sí solas el proyecto de enlace original.

Se ha preparado [build-reference/relink.pro](build-reference/relink.pro). Sus entradas son:

```text
fft.o
main.o
mainwindow.o
settings.o
qcustomplot.o
moc_mainwindow.o
moc_settings.o
moc_qcustomplot.o
qrc_reources.o
```

`main.o` define `qMain(int, char**)`; el arranque de aplicación GUI debe aportar el adaptador correspondiente del kit Qt/MinGW. La plantilla deja que qmake configure ese enlace de Windows. Se utilizan los objetos conservados como entradas de enlace, sin inventar fuentes vacíos que dupliquen clases o símbolos.

Ejemplo en **PowerShell**, suponiendo las rutas de instalación habituales. Hay que ajustar las rutas si el kit se instala en otro lugar:

```powershell
$qtBin = 'C:\Qt\5.14.2\mingw73_64\bin'
$mingwBin = 'C:\Qt\Tools\mingw730_64\bin'
$env:Path = "$qtBin;$mingwBin;$env:Path"

& "$qtBin\qmake.exe" -query QT_VERSION
& "$mingwBin\g++.exe" -dumpmachine
& "$mingwBin\g++.exe" -dumpfullversion
# Esperado: 5.14.2; x86_64-w64-mingw32; 7.3.0.

New-Item -ItemType Directory -Force D:\Repos\Echosounder\build-relink | Out-Null
Set-Location D:\Repos\Echosounder\build-relink
& "$qtBin\qmake.exe" '..\analysis\build-reference\relink.pro' 'CONFIG+=release'
if ($LASTEXITCODE -ne 0) { throw 'qmake ha fallado' }
& "$mingwBin\mingw32-make.exe" -j4
if ($LASTEXITCODE -ne 0) { throw 'El reenlazado ha fallado' }
```

El objetivo se llama `SonarFrontEnd-relinked.exe` para conservar el ejecutable analizado. La ubicación exacta de salida depende del Makefile generado; normalmente estará en `release` o en el directorio de construcción.

La prueba decisiva de esta ruta es enlazar con el kit correcto y comprobar las referencias pendientes. La plantilla no ha pasado aún esa prueba. Si aparecen símbolos Qt sin resolver, hay que comprobar versión, arquitectura, orden de enlace y bibliotecas del kit. No debe resolverse sustituyendo arbitrariamente los objetos o añadiendo bibliotecas de otro compilador.

Un reenlazado satisfactorio tampoco implica identidad byte a byte del EXE: pueden variar marcas temporales, orden y metadatos. El comportamiento debe contrastarse contra el binario original y el instrumento.

## Ruta B: reconstruir un proyecto fuente mantenible

Los nombres de las unidades originales se conocen por los símbolos y archivos generados. El proyecto fuente mínimo esperado es:

```text
SonarFrontEnd/
  SonarFrontEnd.pro
  main.cpp
  mainwindow.h
  mainwindow.cpp
  mainwindow.ui          # o construcción equivalente de widgets por código
  settings.h
  settings.cpp
  settings.ui            # o construcción equivalente por código
  fft.h
  fft.cpp
  qcustomplot.h
  qcustomplot.cpp
  reources.qrc
  art/*.svg
```

La existencia de un archivo `fft.h` con ese nombre es una propuesta de organización; los objetos confirman `fft.cpp` y las firmas de funciones, pero no permiten recuperar todos los nombres de cabeceras que se incluyeron. Del mismo modo, los nombres `.ui` deben confirmarse o elegirse al reconstruirlos.

| Parte | Qué se puede recuperar | Trabajo pendiente |
| --- | --- | --- |
| Entrada y ventana | Funciones, slots, cadenas, acciones, buena parte del flujo | Reescribir C++ y declarar correctamente clases y miembros |
| Ajustes | Valores, códigos de ganancia, rangos y aplicación de parámetros | Reconstruir `ApplicationSettings` y el formulario |
| Serie | Órdenes, tamaños y lectura little-endian del cliente | Validar con el dispositivo, especialmente relleno, errores y acumulación |
| FFT/envolvente | Algoritmos y llamadas observables en el desensamblado | Implementación fuente y comparación numérica |
| QCustomPlot | Biblioteca enlazada y API utilizada | Recuperar una distribución fuente compatible; versión exacta original no confirmada |
| Recursos | Diez SVG originales y rutas Qt | Ya extraídos y validados en `recovered-resources` |
| Proyecto | Módulos, compilador y estructura deducida | Recuperar las opciones exactas faltantes o definir un proyecto nuevo |
| Firmware | Solo contrato que espera el cliente | No está disponible; no se puede reconstruir de forma completa a partir de esta aplicación |

La [descarga oficial de QCustomPlot](https://www.qcustomplot.com/index.php/download) proporciona las distribuciones fuente. La API encontrada incluye la infraestructura de la familia 2; 2.0.1 es una candidata temporalmente compatible con el ejecutable de 2020, pero **no se ha identificado como versión exacta**. Elegir una versión concreta requiere comparar las interfaces y validar el resultado.

La plantilla [SonarFrontEnd.pro.example](build-reference/SonarFrontEnd.pro.example) enumera los módulos y los archivos esperados. No compila hoy porque esos fuentes y formularios faltan. Una vez reconstruidos, se copiaría como `SonarFrontEnd.pro` junto a ellos y se construiría en un directorio separado con el mismo procedimiento qmake/mingw32-make.

Los iconos están en [recovered-resources/art](recovered-resources/art) y el índice reconstruido conserva el nombre original, incluida su grafía `reources.qrc`. Conserva también `diconnect_usb.svg` para que las rutas `:/art/...` observadas sigan resolviendo.

No se deben usar los `moc_*.cpp` antiguos como sustitutos de las cabeceras faltantes. Incluyen rutas relativas a `../../SonarFrontEnd/*.h` y exigen la revisión de metadatos de Qt 5.14.2. Para construir desde fuentes, qmake debe regenerar `moc`, `uic` y `rcc` con el SDK elegido. `moc_predefs.h` es salida del compilador, no una cabecera de negocio que haya que mantener manualmente.

## Distribución del resultado

Una vez producido y probado un EXE nuevo, la herramienta de Qt que reúne las dependencias de Windows es `windeployqt`, según su [documentación de Qt 5](https://doc.qt.io/qt-5/windows-deployment.html). Ejemplo en PowerShell, ajustando la ruta real de salida:

```powershell
$qtBin = 'C:\Qt\5.14.2\mingw73_64\bin'
$mingwBin = 'C:\Qt\Tools\mingw730_64\bin'
$env:Path = "$qtBin;$mingwBin;$env:Path"
$newExe = 'D:\Repos\Echosounder\build-relink\release\SonarFrontEnd-relinked.exe'
$distDir = 'D:\Repos\Echosounder\dist-relinked'

if (-not (Test-Path -LiteralPath $newExe)) { throw 'No se encuentra el EXE construido' }
New-Item -ItemType Directory -Force $distDir | Out-Null
Copy-Item -LiteralPath $newExe -Destination $distDir
& "$qtBin\windeployqt.exe" --release --compiler-runtime --svg `
    (Join-Path $distDir 'SonarFrontEnd-relinked.exe')
if ($LASTEXITCODE -ne 0) { throw 'windeployqt ha fallado' }
```

No se necesita copiar `.o`, `moc_*.cpp`, SDK, fuentes o herramientas de construcción a la carpeta de ejecución. Para conservar la posibilidad de reenlazar en el futuro, hay que archivar esos artefactos por separado.

## Validación necesaria al disponer del kit y del instrumento

Una construcción deberá comprobarse por etapas:

1. **Enlace:** sin símbolos pendientes y con importaciones Qt/MinGW de 64 bits coherentes.
2. **Arranque en carpeta distribuida:** iconos y tres vistas disponibles, sin depender del PATH del SDK.
3. **Protocolo con un simulador:** saludo, versión, confirmaciones, tramas partidas, ausencia de respuesta y traza de 6.800 bytes.
4. **Comparación numérica:** tonos de frecuencia conocida, señal constante, impulso y ceros para verificar conversión, FFT, envolvente y escalas. Incluir repeticiones 1, 2, 3 y 256.
5. **Hardware:** retardo y ganancia reales, frecuencia de muestreo, estabilidad de adquisiciones, Stop y reconexión.

Para reproducir el comportamiento histórico se conservan primero sus convenciones numéricas. Las correcciones identificadas en el estudio deben introducirse después con pruebas que permitan distinguir una mejora deliberada de una incompatibilidad accidental.
